"""
Speech-to-Text Pipeline

Async, non-blocking microphone listener via sounddevice.
Captures audio into an elastic ring buffer.
On voice activity detection (VAD), flushes to a temporary WAV
and transmits to Groq Whisper large-v3.
"""

import asyncio
import io
import logging
import os
import struct
import tempfile
import time
import wave
from collections import deque
from typing import Callable, Coroutine, Optional, Any

import httpx

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

OnTranscriptCallback = Callable[[str], Coroutine[Any, Any, None]]

_GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class STTPipeline:
    """
    Continuous microphone listener with VAD and cloud STT.

    Audio flow:
      mic -> ring buffer -> VAD gate -> WAV -> Groq Whisper -> transcript
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    BLOCK_SIZE = 1024
    DTYPE = "int16"
    RING_BUFFER_SECONDS = 30
    VAD_ENERGY_THRESHOLD = 500
    VAD_SILENCE_TIMEOUT = 1.5  # seconds of silence to end utterance
    MIN_UTTERANCE_DURATION = 0.5  # ignore very short bursts

    def __init__(self) -> None:
        self._running = False
        self._ring: deque[bytes] = deque(
            maxlen=int(self.SAMPLE_RATE / self.BLOCK_SIZE * self.RING_BUFFER_SECONDS)
        )
        self._on_transcript_cbs: list[OnTranscriptCallback] = []
        self._is_speaking = False
        self._speech_start = 0.0
        self._silence_start = 0.0
        self._utterance_blocks: list[bytes] = []
        self._http = httpx.AsyncClient(timeout=30.0)
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._total_utterances = 0

    def on_transcript(self, cb: OnTranscriptCallback) -> None:
        self._on_transcript_cbs.append(cb)

    async def run(self) -> None:
        if sd is None or np is None:
            logger.error("sounddevice/numpy not installed; STT disabled")
            return

        self._running = True
        logger.info("STT pipeline started (sample_rate=%d)", self.SAMPLE_RATE)

        loop = asyncio.get_event_loop()
        audio_queue: asyncio.Queue[bytes] = asyncio.Queue()

        def audio_callback(indata: "np.ndarray", frames: int, time_info: Any, status: Any) -> None:
            if status:
                logger.debug("Audio status: %s", status)
            loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

        try:
            stream = sd.RawInputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                blocksize=self.BLOCK_SIZE,
                callback=audio_callback,
            )
            stream.start()
        except Exception:
            logger.exception("Failed to open microphone stream")
            return

        try:
            while self._running:
                try:
                    block = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                    await self._process_block(block)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    logger.exception("STT block processing error")
        except asyncio.CancelledError:
            pass
        finally:
            stream.stop()
            stream.close()
            logger.info("STT pipeline stopped (utterances=%d)", self._total_utterances)

    async def stop(self) -> None:
        self._running = False
        await self._http.aclose()

    async def _process_block(self, block: bytes) -> None:
        energy = self._compute_energy(block)
        self._ring.append(block)

        if energy > self.VAD_ENERGY_THRESHOLD:
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start = time.monotonic()
                self._utterance_blocks.clear()
                logger.debug("VAD: speech started (energy=%d)", energy)
            self._silence_start = 0.0
            self._utterance_blocks.append(block)
        elif self._is_speaking:
            self._utterance_blocks.append(block)
            if self._silence_start == 0.0:
                self._silence_start = time.monotonic()
            elif time.monotonic() - self._silence_start > self.VAD_SILENCE_TIMEOUT:
                duration = time.monotonic() - self._speech_start
                if duration >= self.MIN_UTTERANCE_DURATION:
                    await self._handle_utterance(self._utterance_blocks.copy())
                self._is_speaking = False
                self._utterance_blocks.clear()
                self._silence_start = 0.0

    @staticmethod
    def _compute_energy(block: bytes) -> float:
        if len(block) < 2:
            return 0.0
        n_samples = len(block) // 2
        samples = struct.unpack(f"<{n_samples}h", block[:n_samples * 2])
        return sum(abs(s) for s in samples) / max(1, n_samples)

    async def _handle_utterance(self, blocks: list[bytes]) -> None:
        wav_data = self._blocks_to_wav(blocks)
        if wav_data is None:
            return

        transcript = await self._transcribe(wav_data)
        if not transcript:
            return

        self._total_utterances += 1
        logger.info("Transcript: %s", transcript[:80])

        for cb in self._on_transcript_cbs:
            try:
                await cb(transcript)
            except Exception:
                logger.exception("Transcript callback error")

    def _blocks_to_wav(self, blocks: list[bytes]) -> Optional[bytes]:
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)  # int16 = 2 bytes
                wf.setframerate(self.SAMPLE_RATE)
                for b in blocks:
                    wf.writeframes(b)
            return buf.getvalue()
        except Exception:
            logger.exception("WAV encoding failed")
            return None

    async def _transcribe(self, wav_data: bytes) -> str:
        if not self._api_key:
            logger.warning("No GROQ_API_KEY; STT transcription skipped")
            return ""

        try:
            files = {"file": ("utterance.wav", wav_data, "audio/wav")}
            data = {"model": "whisper-large-v3", "language": "vi"}
            headers = {"Authorization": f"Bearer {self._api_key}"}

            r = await self._http.post(
                _GROQ_WHISPER_URL,
                headers=headers,
                files=files,
                data=data,
            )
            r.raise_for_status()
            return r.json().get("text", "").strip()
        except Exception:
            logger.exception("Whisper transcription failed")
            return ""

    @property
    def stats(self) -> dict:
        return {
            "running": self._running,
            "is_speaking": self._is_speaking,
            "total_utterances": self._total_utterances,
            "ring_buffer_blocks": len(self._ring),
        }
