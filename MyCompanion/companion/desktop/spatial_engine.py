"""
Spatial Awareness & Auto-Movement Engine

Implements:
  - "Don't Block Content" Protocol: detects when the widget overlaps
    the user's active window and auto-repositions.
  - Idle/Boredom behavior: sinusoidal levitation and wandering when
    the user is inactive for >120s.
"""

import asyncio
import logging
import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QPoint, QRect

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


@dataclass
class WindowRect:
    x: int
    y: int
    w: int
    h: int

    def as_qrect(self) -> QRect:
        return QRect(self.x, self.y, self.w, self.h)

    def intersects(self, other: "WindowRect") -> bool:
        return self.as_qrect().intersects(other.as_qrect())


class SpatialEngine:
    """
    Manages widget positioning to avoid blocking user content.

    Uses xdotool to detect active window geometry.
    Computes clear quadrants on the desktop for repositioning.
    Triggers idle animations when user is inactive.
    """

    IDLE_THRESHOLD = 120.0  # seconds
    CHECK_INTERVAL = 3.0  # seconds
    LEVITATION_AMPLITUDE = 8  # pixels
    LEVITATION_PERIOD = 4.0  # seconds
    WANDER_SPEED = 0.5  # pixels per tick

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self._sw = screen_width
        self._sh = screen_height
        self._has_xdotool = shutil.which("xdotool") is not None
        self._running = False
        self._last_input_time = time.monotonic()
        self._widget_rect: Optional[WindowRect] = None
        self._on_reposition: Optional[callable] = None
        self._on_idle_move: Optional[callable] = None
        self._idle_active = False

    def set_widget_rect(self, x: int, y: int, w: int, h: int) -> None:
        self._widget_rect = WindowRect(x, y, w, h)

    def on_reposition(self, cb: callable) -> None:
        self._on_reposition = cb

    def on_idle_move(self, cb: callable) -> None:
        self._on_idle_move = cb

    def record_user_input(self) -> None:
        self._last_input_time = time.monotonic()
        self._idle_active = False

    async def run(self) -> None:
        self._running = True
        logger.info("Spatial engine started (screen=%dx%d)", self._sw, self._sh)

        try:
            while self._running:
                try:
                    await self._check_collision()
                    await self._check_idle()
                except Exception:
                    logger.exception("Spatial check error")
                await asyncio.sleep(self.CHECK_INTERVAL)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        self._running = False

    async def _check_collision(self) -> None:
        if self._widget_rect is None or not self._has_xdotool:
            return

        active = await asyncio.get_event_loop().run_in_executor(
            None, self._get_active_window_rect
        )
        if active is None:
            return

        if self._widget_rect.intersects(active):
            new_pos = self._find_clear_position(active)
            if new_pos and self._on_reposition:
                logger.debug(
                    "Widget collision detected; repositioning to (%d, %d)",
                    new_pos.x(),
                    new_pos.y(),
                )
                try:
                    self._on_reposition(new_pos)
                    self._widget_rect.x = new_pos.x()
                    self._widget_rect.y = new_pos.y()
                except Exception:
                    logger.exception("Reposition callback error")

    async def _check_idle(self) -> None:
        idle_time = time.monotonic() - self._last_input_time
        if idle_time < self.IDLE_THRESHOLD:
            return

        if not self._idle_active:
            self._idle_active = True
            logger.debug("User idle for %.0fs; starting idle animation", idle_time)

        if self._on_idle_move and self._widget_rect:
            t = time.monotonic()
            dy = math.sin(t * 2 * math.pi / self.LEVITATION_PERIOD) * self.LEVITATION_AMPLITUDE
            new_y = self._widget_rect.y + int(dy)
            new_y = max(0, min(self._sh - self._widget_rect.h, new_y))
            try:
                self._on_idle_move(QPoint(self._widget_rect.x, new_y))
            except Exception:
                logger.exception("Idle move callback error")

    def _find_clear_position(self, active_rect: WindowRect) -> Optional[QPoint]:
        """Find the best unobstructed quadrant for the widget."""
        if self._widget_rect is None:
            return None

        w = self._widget_rect.w
        h = self._widget_rect.h
        margin = 20

        candidates = [
            QPoint(self._sw - w - margin, self._sh - h - margin),  # bottom-right
            QPoint(margin, self._sh - h - margin),                  # bottom-left
            QPoint(self._sw - w - margin, margin),                  # top-right
            QPoint(margin, margin),                                  # top-left
            QPoint((self._sw - w) // 2, self._sh - h - margin),   # bottom-center
        ]

        ar = active_rect.as_qrect()
        for pt in candidates:
            candidate_rect = QRect(pt.x(), pt.y(), w, h)
            if not candidate_rect.intersects(ar):
                return pt

        return candidates[0]

    def _get_active_window_rect(self) -> Optional[WindowRect]:
        try:
            wid = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode().strip()

            geo = subprocess.check_output(
                ["xdotool", "getwindowgeometry", "--shell", wid],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode()

            vals: dict[str, int] = {}
            for line in geo.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    try:
                        vals[k.strip()] = int(v.strip())
                    except ValueError:
                        pass

            size = subprocess.check_output(
                ["xdotool", "getwindowfocus", "getwindowgeometry", "--shell", wid],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode()

            for line in size.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    try:
                        vals[k.strip()] = int(v.strip())
                    except ValueError:
                        pass

            x = vals.get("X", 0)
            y = vals.get("Y", 0)
            w = vals.get("WIDTH", 0)
            h = vals.get("HEIGHT", 0)

            if w > 0 and h > 0:
                return WindowRect(x, y, w, h)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            pass
        return None

    @property
    def stats(self) -> dict:
        return {
            "idle_seconds": time.monotonic() - self._last_input_time,
            "idle_active": self._idle_active,
            "has_xdotool": self._has_xdotool,
            "widget_rect": (
                f"{self._widget_rect.x},{self._widget_rect.y},{self._widget_rect.w},{self._widget_rect.h}"
                if self._widget_rect
                else "none"
            ),
        }
