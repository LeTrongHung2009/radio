"""
Context Reader - Active Window Tracking

Extracts active process metadata (Window Title, Application Name)
using psutil and xdotool. Flags context-switch events when the
active window changes.
"""

import asyncio
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Coroutine, Optional, Any

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

OnContextSwitchCallback = Callable[[str, str, str], Coroutine[Any, Any, None]]
# callback(window_title, app_name, window_class)


@dataclass
class WindowInfo:
    title: str = ""
    app_name: str = ""
    window_class: str = ""
    pid: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WindowInfo):
            return False
        return self.title == other.title and self.app_name == other.app_name

    def describe(self) -> str:
        parts = []
        if self.app_name:
            parts.append(self.app_name)
        if self.title:
            parts.append(f'"{self.title}"')
        return " - ".join(parts) if parts else "Unknown"


class ContextReader:
    """
    Periodically polls the active window and detects context switches.
    Uses xdotool for X11, falls back to basic psutil heuristics.
    """

    POLL_INTERVAL = 2.0  # seconds

    def __init__(self) -> None:
        self._running = False
        self._current: Optional[WindowInfo] = None
        self._previous: Optional[WindowInfo] = None
        self._on_switch_cbs: list[OnContextSwitchCallback] = []
        self._has_xdotool = shutil.which("xdotool") is not None
        self._total_switches = 0

        if not self._has_xdotool:
            logger.warning("xdotool not found; context tracking limited")

    def on_context_switch(self, cb: OnContextSwitchCallback) -> None:
        self._on_switch_cbs.append(cb)

    @property
    def current_window(self) -> Optional[WindowInfo]:
        return self._current

    async def run(self) -> None:
        self._running = True
        logger.info("Context reader started (xdotool=%s)", self._has_xdotool)

        try:
            while self._running:
                try:
                    await self._poll()
                except Exception:
                    logger.exception("Context poll error")
                await asyncio.sleep(self.POLL_INTERVAL)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Context reader stopped (switches=%d)", self._total_switches)

    async def stop(self) -> None:
        self._running = False

    async def _poll(self) -> None:
        info = await asyncio.get_event_loop().run_in_executor(None, self._get_active_window)
        if info is None:
            return

        if self._current is not None and info != self._current:
            self._previous = self._current
            self._total_switches += 1
            logger.debug(
                "Context switch: %s -> %s",
                self._current.describe(),
                info.describe(),
            )
            for cb in self._on_switch_cbs:
                try:
                    await cb(info.title, info.app_name, info.window_class)
                except Exception:
                    logger.exception("Context switch callback error")

        self._current = info

    def _get_active_window(self) -> Optional[WindowInfo]:
        if self._has_xdotool:
            return self._xdotool_query()
        return self._psutil_fallback()

    def _xdotool_query(self) -> Optional[WindowInfo]:
        try:
            wid_raw = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode().strip()

            wid = int(wid_raw)

            title = subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowname"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode().strip()

            pid_raw = subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowpid"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode().strip()
            pid = int(pid_raw) if pid_raw else 0

            app_name = ""
            if pid and psutil is not None:
                try:
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            wm_class = ""
            try:
                class_raw = subprocess.check_output(
                    ["xdotool", "getactivewindow", "getwindowclassname"],
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                ).decode().strip()
                wm_class = class_raw
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

            return WindowInfo(
                title=title,
                app_name=app_name or wm_class,
                window_class=wm_class,
                pid=pid,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            return None

    @staticmethod
    def _psutil_fallback() -> Optional[WindowInfo]:
        if psutil is None:
            return None
        try:
            for proc in psutil.process_iter(["pid", "name", "status"]):
                if proc.info["status"] == psutil.STATUS_RUNNING:
                    return WindowInfo(
                        title="",
                        app_name=proc.info["name"],
                        pid=proc.info["pid"],
                    )
        except Exception:
            pass
        return None

    @property
    def stats(self) -> dict:
        return {
            "current": self._current.describe() if self._current else "none",
            "total_switches": self._total_switches,
            "has_xdotool": self._has_xdotool,
        }
