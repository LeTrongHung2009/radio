"""
Priority Queue for incoming events.

Weight scheme (lower = higher priority):
  0 - User TextInput
  1 - Voice Interrupt
  2 - Dynamic Screen Events
  3 - Boredom / Idle Prompting
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    USER_TEXT = 0
    VOICE_INTERRUPT = 1
    SCREEN_EVENT = 2
    BOREDOM = 3


@dataclass(order=True)
class PrioritizedEvent:
    """
    Wrapper for events entering the priority queue.
    Ordering: priority first, then arrival time (FIFO within same priority).
    """

    priority: int
    timestamp: float = field(compare=True)
    payload: Any = field(compare=False)
    event_type: str = field(default="unknown", compare=False)

    @classmethod
    def text_input(cls, text: str) -> "PrioritizedEvent":
        return cls(
            priority=EventPriority.USER_TEXT,
            timestamp=time.monotonic(),
            payload={"text": text},
            event_type="text_input",
        )

    @classmethod
    def voice_input(cls, audio_path: str, transcript: str = "") -> "PrioritizedEvent":
        return cls(
            priority=EventPriority.VOICE_INTERRUPT,
            timestamp=time.monotonic(),
            payload={"audio_path": audio_path, "transcript": transcript},
            event_type="voice_input",
        )

    @classmethod
    def screen_event(cls, description: str, frame_b64: str = "") -> "PrioritizedEvent":
        return cls(
            priority=EventPriority.SCREEN_EVENT,
            timestamp=time.monotonic(),
            payload={"description": description, "frame": frame_b64},
            event_type="screen_event",
        )

    @classmethod
    def boredom(cls, idle_seconds: float) -> "PrioritizedEvent":
        return cls(
            priority=EventPriority.BOREDOM,
            timestamp=time.monotonic(),
            payload={"idle_seconds": idle_seconds},
            event_type="boredom",
        )


class EventQueue:
    """Async priority queue for the AI Cortex event loop."""

    def __init__(self, maxsize: int = 128) -> None:
        self._queue: asyncio.PriorityQueue[PrioritizedEvent] = asyncio.PriorityQueue(maxsize=maxsize)
        self._total_enqueued = 0
        self._total_processed = 0

    async def put(self, event: PrioritizedEvent) -> None:
        await self._queue.put(event)
        self._total_enqueued += 1
        logger.debug(
            "Event enqueued: type=%s prio=%d queue_size=%d",
            event.event_type,
            event.priority,
            self._queue.qsize(),
        )

    def put_nowait(self, event: PrioritizedEvent) -> None:
        self._queue.put_nowait(event)
        self._total_enqueued += 1

    async def get(self) -> PrioritizedEvent:
        event = await self._queue.get()
        self._total_processed += 1
        return event

    def task_done(self) -> None:
        self._queue.task_done()

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()

    @property
    def stats(self) -> dict:
        return {
            "enqueued": self._total_enqueued,
            "processed": self._total_processed,
            "pending": self._queue.qsize(),
        }
