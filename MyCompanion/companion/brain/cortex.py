"""
AI Cortex - The Cognitive Core

Central event loop that:
  1. Drains the PriorityQueue
  2. Routes events through the persona / emotion layers
  3. Calls the API router for LLM inference
  4. Dispatches TTS + VTS expression output
  5. Respects turn-taking constraints
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

from companion.brain.api_router import APIRouter, LLMResponse
from companion.brain.priority_queue import EventQueue, PrioritizedEvent
from companion.brain.turn_controller import TurnController
from companion.persona.emotion_matrix import EmotionMatrix
from companion.persona.prompt_engine import PromptEngine

logger = logging.getLogger(__name__)

OnResponseCallback = Callable[[str, str], Coroutine[Any, Any, None]]


class Cortex:
    """
    Main cognitive loop.

    Reads prioritised events, builds context-rich prompts via PromptEngine,
    queries the cloud LLM through APIRouter, and invokes registered callbacks
    for TTS / UI / VTS output.
    """

    BOREDOM_INTERVAL = 120.0  # seconds of silence before boredom event

    def __init__(
        self,
        event_queue: EventQueue,
        turn_controller: TurnController,
        api_router: APIRouter,
        emotion_matrix: EmotionMatrix,
        prompt_engine: PromptEngine,
    ) -> None:
        self._eq = event_queue
        self._tc = turn_controller
        self._api = api_router
        self._emotion = emotion_matrix
        self._prompt = prompt_engine

        self._on_response_cbs: list[OnResponseCallback] = []
        self._running = False
        self._last_interaction = time.monotonic()
        self._screen_context = ""
        self._window_context = ""
        self._total_responses = 0

    def on_response(self, cb: OnResponseCallback) -> None:
        self._on_response_cbs.append(cb)

    def update_screen_context(self, ctx: str) -> None:
        self._screen_context = ctx

    def update_window_context(self, ctx: str) -> None:
        self._window_context = ctx

    async def run(self) -> None:
        self._running = True
        logger.info("Cortex event loop started")
        boredom_task = asyncio.create_task(self._boredom_loop())
        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(self._eq.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                try:
                    await self._handle_event(event)
                except Exception:
                    logger.exception("Error handling event %s", event.event_type)
                finally:
                    self._eq.task_done()
        except asyncio.CancelledError:
            pass
        finally:
            boredom_task.cancel()
            logger.info("Cortex event loop stopped")

    async def stop(self) -> None:
        self._running = False
        await self._api.close()

    async def _handle_event(self, event: PrioritizedEvent) -> None:
        etype = event.event_type
        payload = event.payload

        if etype == "text_input":
            self._last_interaction = time.monotonic()
            await self._respond_to_text(payload["text"])
        elif etype == "voice_input":
            self._last_interaction = time.monotonic()
            transcript = payload.get("transcript", "")
            if transcript:
                await self._respond_to_text(transcript)
        elif etype == "screen_event":
            desc = payload.get("description", "")
            if desc:
                self._screen_context = desc
                await self._respond_to_screen(desc)
        elif etype == "boredom":
            await self._respond_to_boredom(payload.get("idle_seconds", 0))
        else:
            logger.warning("Unknown event type: %s", etype)

    async def _respond_to_text(self, user_text: str) -> None:
        if self._tc.is_user_active():
            return

        await self._tc.ai_start_thinking()
        self._emotion.trigger_reflex("user_input")

        messages = self._prompt.build_chat_prompt(
            user_text=user_text,
            emotion_state=self._emotion.snapshot(),
            screen_context=self._screen_context,
            window_context=self._window_context,
            timestamp=datetime.now().strftime("%H:%M"),
        )

        resp = await self._api.chat(messages, temperature=self._emotion.temperature)
        self._emotion.apply_response_emotion(resp.emotion)
        self._total_responses += 1

        await self._tc.ai_start_speaking()
        try:
            await self._dispatch_response(resp.text, resp.emotion)
        finally:
            await self._tc.ai_stop_speaking()

    async def _respond_to_screen(self, description: str) -> None:
        if self._tc.is_user_active() or self._tc.is_ai_active():
            return

        reflex = self._emotion.trigger_reflex("screen_change")
        if not reflex:
            return

        messages = self._prompt.build_screen_prompt(
            screen_description=description,
            emotion_state=self._emotion.snapshot(),
        )

        resp = await self._api.chat(messages, temperature=0.8, max_tokens=200)
        self._emotion.apply_response_emotion(resp.emotion)
        self._total_responses += 1

        await self._tc.ai_start_speaking()
        try:
            await self._dispatch_response(resp.text, resp.emotion)
        finally:
            await self._tc.ai_stop_speaking()

    async def _respond_to_boredom(self, idle_seconds: float) -> None:
        if self._tc.is_user_active() or self._tc.is_ai_active():
            return

        self._emotion.trigger_reflex("boredom")
        messages = self._prompt.build_boredom_prompt(
            idle_seconds=idle_seconds,
            emotion_state=self._emotion.snapshot(),
            screen_context=self._screen_context,
        )

        resp = await self._api.chat(messages, temperature=0.9, max_tokens=250)
        self._emotion.apply_response_emotion(resp.emotion)
        self._total_responses += 1

        await self._tc.ai_start_speaking()
        try:
            await self._dispatch_response(resp.text, resp.emotion)
        finally:
            await self._tc.ai_stop_speaking()

    async def _dispatch_response(self, text: str, emotion: str) -> None:
        for cb in self._on_response_cbs:
            try:
                await cb(text, emotion)
            except Exception:
                logger.exception("Response callback error")

    async def _boredom_loop(self) -> None:
        while self._running:
            await asyncio.sleep(10.0)
            idle = time.monotonic() - self._last_interaction
            if idle >= self.BOREDOM_INTERVAL and not self._tc.is_ai_active():
                try:
                    self._eq.put_nowait(PrioritizedEvent.boredom(idle))
                except asyncio.QueueFull:
                    pass

    @property
    def stats(self) -> dict:
        return {
            "total_responses": self._total_responses,
            "idle_seconds": time.monotonic() - self._last_interaction,
            "screen_context": self._screen_context[:80],
            "window_context": self._window_context[:80],
            "queue": self._eq.stats,
            "turn": self._tc.stats,
            "api": self._api.stats,
        }
