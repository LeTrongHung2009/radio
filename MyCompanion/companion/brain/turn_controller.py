"""
Turn-Taking Orchestration

Strict global asyncio.Lock mechanism ensuring the AI never triggers TTS
while the user is speaking or typing. Coordinates between input senses
and output expression layers.
"""

import asyncio
import enum
import logging
import time

logger = logging.getLogger(__name__)


class ChannelState(enum.Enum):
    IDLE = "idle"
    USER_SPEAKING = "user_speaking"
    USER_TYPING = "user_typing"
    AI_THINKING = "ai_thinking"
    AI_SPEAKING = "ai_speaking"


class TurnController:
    """
    Global turn-taking arbiter.

    Rules:
      - Only ONE party (user or AI) holds the floor at a time.
      - User input always pre-empts AI boredom/screen events.
      - AI will not start TTS while user is speaking or typing.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state = ChannelState.IDLE
        self._state_since = time.monotonic()
        self._user_active = asyncio.Event()
        self._ai_can_speak = asyncio.Event()
        self._ai_can_speak.set()

    @property
    def state(self) -> ChannelState:
        return self._state

    def _set_state(self, new_state: ChannelState) -> None:
        if new_state != self._state:
            logger.debug("Turn state: %s -> %s", self._state.value, new_state.value)
            self._state = new_state
            self._state_since = time.monotonic()

    async def user_start_speaking(self) -> None:
        async with self._lock:
            self._set_state(ChannelState.USER_SPEAKING)
            self._ai_can_speak.clear()
            self._user_active.set()

    async def user_stop_speaking(self) -> None:
        async with self._lock:
            if self._state == ChannelState.USER_SPEAKING:
                self._set_state(ChannelState.IDLE)
                self._ai_can_speak.set()
                self._user_active.clear()

    async def user_start_typing(self) -> None:
        async with self._lock:
            self._set_state(ChannelState.USER_TYPING)
            self._ai_can_speak.clear()
            self._user_active.set()

    async def user_stop_typing(self) -> None:
        async with self._lock:
            if self._state == ChannelState.USER_TYPING:
                self._set_state(ChannelState.IDLE)
                self._ai_can_speak.set()
                self._user_active.clear()

    async def ai_start_thinking(self) -> None:
        async with self._lock:
            self._set_state(ChannelState.AI_THINKING)

    async def ai_start_speaking(self) -> None:
        """Block until the user is not active, then claim the floor."""
        await self._ai_can_speak.wait()
        async with self._lock:
            self._set_state(ChannelState.AI_SPEAKING)
            self._ai_can_speak.clear()

    async def ai_stop_speaking(self) -> None:
        async with self._lock:
            if self._state == ChannelState.AI_SPEAKING:
                self._set_state(ChannelState.IDLE)
                self._ai_can_speak.set()

    def is_user_active(self) -> bool:
        return self._state in (ChannelState.USER_SPEAKING, ChannelState.USER_TYPING)

    def is_ai_active(self) -> bool:
        return self._state in (ChannelState.AI_THINKING, ChannelState.AI_SPEAKING)

    @property
    def stats(self) -> dict:
        return {
            "state": self._state.value,
            "state_duration": time.monotonic() - self._state_since,
            "user_active": self.is_user_active(),
            "ai_can_speak": self._ai_can_speak.is_set(),
        }
