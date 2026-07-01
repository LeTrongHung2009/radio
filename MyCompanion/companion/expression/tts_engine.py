"""
TTS Engine - Text-to-Speech via edge-tts

Translates AI persona text output into Vietnamese audio using
vi-VN-HoaiMyNeural voice. Streams through a non-blocking mpv process.
"""

import asyncio
import logging
import os
import shutil
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import edge_tts
except ImportError:
    edge_tts = None  # type: ignore[assignment]


class TTSEngine:
    """
    Non-blocking TTS engine using edge-tts + mpv playback.

    Audio flow:
      text -> edge-tts (vi-VN-HoaiMyNeural) -> temp .mp3 -> mpv playback
    """

    VOICE = "vi-VN-HoaiMyNeural"
    RATE = "+10%"
    VOLUME = "+5%"
    TEMP_DIR = "/tmp/mycompanion_tts"

    def __init__(self) -> None:
        self._async_proc: Optional[asyncio.subprocess.Process] = None
        self._is_speaking = False
        self._has_mpv = shutil.which("mpv") is not None
        self._has_paplay = shutil.which("paplay") is not None
        self._total_utterances = 0

        os.makedirs(self.TEMP_DIR, exist_ok=True)

        if not self._has_mpv and not self._has_paplay:
            logger.warning("Neither mpv nor paplay found; TTS playback disabled")

    @property
    def is_speaking(self) -> bool:
        if self._async_proc is not None:
            if self._async_proc.returncode is not None:
                self._async_proc = None
                self._is_speaking = False
        return self._is_speaking

    async def speak(self, text: str) -> None:
        """Synthesize and play speech. Blocks until playback completes."""
        if edge_tts is None:
            logger.error("edge-tts not installed; TTS disabled")
            return

        if not text.strip():
            return

        await self.stop()

        try:
            audio_path = os.path.join(
                self.TEMP_DIR, f"tts_{int(time.time() * 1000)}.mp3"
            )

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.VOICE,
                rate=self.RATE,
                volume=self.VOLUME,
            )
            await communicate.save(audio_path)

            if not os.path.exists(audio_path):
                logger.error("TTS audio file not created")
                return

            self._is_speaking = True
            self._total_utterances += 1
            await self._play_audio(audio_path)

        except Exception:
            logger.exception("TTS speak error")
        finally:
            self._is_speaking = False
            self._cleanup_old_files()

    async def _play_audio(self, path: str) -> None:
        """Play audio file via mpv (preferred) or paplay."""
        if self._has_mpv:
            cmd = [
                "mpv",
                "--no-video",
                "--really-quiet",
                "--no-terminal",
                path,
            ]
        elif self._has_paplay:
            cmd = ["paplay", path]
        else:
            logger.warning("No audio player available")
            return

        try:
            self._async_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await self._async_proc.wait()
        except Exception:
            logger.exception("Audio playback error")
        finally:
            self._async_proc = None

    async def stop(self) -> None:
        """Stop current playback if any."""
        if self._async_proc is not None:
            try:
                self._async_proc.terminate()
                await asyncio.wait_for(self._async_proc.wait(), timeout=2)
            except Exception:
                try:
                    self._async_proc.kill()
                except Exception:
                    pass
            self._async_proc = None
        self._is_speaking = False

    def _cleanup_old_files(self) -> None:
        """Remove TTS temp files older than 60 seconds."""
        try:
            now = time.time()
            for f in os.listdir(self.TEMP_DIR):
                fp = os.path.join(self.TEMP_DIR, f)
                if os.path.isfile(fp) and now - os.path.getmtime(fp) > 60:
                    os.unlink(fp)
        except Exception:
            pass

    @property
    def stats(self) -> dict:
        return {
            "is_speaking": self.is_speaking,
            "total_utterances": self._total_utterances,
            "voice": self.VOICE,
            "has_mpv": self._has_mpv,
            "has_paplay": self._has_paplay,
        }
