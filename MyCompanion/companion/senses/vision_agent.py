"""
Vision Agent - Screen Capture via mss

Captures the primary display at a configurable rate (default every 3-5s).
Converts raw bitmaps to 60% quality JPEG.
Computes sequential MD5 frame hashes; drops unchanged frames.
Forwards altered frames to the cortex / cloud VLM.
"""

import asyncio
import base64
import hashlib
import io
import logging
import time
from typing import Callable, Coroutine, Optional, Any

logger = logging.getLogger(__name__)

try:
    import mss
    import mss.tools
except ImportError:
    mss = None  # type: ignore[assignment]

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]


OnFrameCallback = Callable[[str, bytes], Coroutine[Any, Any, None]]


class VisionAgent:
    """
    Async screen capture agent.

    Runs in a background loop, capturing and hashing frames.
    Invokes registered callbacks only when the frame has changed.
    """

    JPEG_QUALITY = 60
    CAPTURE_INTERVAL_MIN = 3.0
    CAPTURE_INTERVAL_MAX = 5.0
    MAX_WIDTH = 512  # resize for bandwidth savings

    def __init__(self) -> None:
        self._running = False
        self._last_hash = ""
        self._last_capture_time = 0.0
        self._on_change_cbs: list[OnFrameCallback] = []
        self._total_captures = 0
        self._total_changes = 0
        self._interval = self.CAPTURE_INTERVAL_MIN

    def on_frame_change(self, cb: OnFrameCallback) -> None:
        self._on_change_cbs.append(cb)

    async def run(self) -> None:
        if mss is None:
            logger.error("mss not installed; vision agent disabled")
            return

        self._running = True
        logger.info("Vision agent started (interval=%.1fs)", self._interval)

        try:
            while self._running:
                try:
                    await self._capture_cycle()
                except Exception:
                    logger.exception("Vision capture error")
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info(
                "Vision agent stopped (captures=%d, changes=%d)",
                self._total_captures,
                self._total_changes,
            )

    async def stop(self) -> None:
        self._running = False

    async def _capture_cycle(self) -> None:
        raw = await asyncio.get_event_loop().run_in_executor(None, self._grab_screen)
        if raw is None:
            return

        self._total_captures += 1
        frame_hash = hashlib.md5(raw).hexdigest()

        if frame_hash == self._last_hash:
            return

        self._last_hash = frame_hash
        self._total_changes += 1
        self._last_capture_time = time.monotonic()

        jpeg_bytes = await asyncio.get_event_loop().run_in_executor(
            None, self._to_jpeg, raw
        )
        if jpeg_bytes is None:
            return

        b64 = base64.b64encode(jpeg_bytes).decode("ascii")
        for cb in self._on_change_cbs:
            try:
                await cb(b64, jpeg_bytes)
            except Exception:
                logger.exception("Frame change callback error")

    @staticmethod
    def _grab_screen() -> Optional[bytes]:
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # primary display
                shot = sct.grab(monitor)
                return bytes(shot.rgb)
        except Exception:
            logger.exception("Screen grab failed")
            return None

    def _to_jpeg(self, rgb_bytes: bytes) -> Optional[bytes]:
        if cv2 is None or np is None:
            return None
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                w, h = monitor["width"], monitor["height"]

            arr = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape((h, w, 3))
            # mss gives BGRA on some systems; ensure BGR for opencv
            if arr.shape[2] == 4:
                arr = arr[:, :, :3]

            # resize to save bandwidth
            if w > self.MAX_WIDTH:
                scale = self.MAX_WIDTH / w
                new_h = int(h * scale)
                arr = cv2.resize(arr, (self.MAX_WIDTH, new_h), interpolation=cv2.INTER_AREA)

            ok, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY])
            return buf.tobytes() if ok else None
        except Exception:
            logger.exception("JPEG encode failed")
            return None

    async def capture_once(self) -> Optional[bytes]:
        raw = await asyncio.get_event_loop().run_in_executor(None, self._grab_screen)
        if raw is None:
            return None
        return await asyncio.get_event_loop().run_in_executor(None, self._to_jpeg, raw)

    @property
    def stats(self) -> dict:
        return {
            "total_captures": self._total_captures,
            "total_changes": self._total_changes,
            "change_rate": (
                self._total_changes / max(1, self._total_captures) * 100
            ),
            "interval": self._interval,
        }
