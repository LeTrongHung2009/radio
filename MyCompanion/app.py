"""
MyCompanion - Global Orchestrator Entrypoint

Autonomous AI Desktop Companion Framework.
Inspired by Neuro-sama, adapted for local desktop use.

Target: Arch Linux, AMD Ryzen 3 3000, 8GB RAM, NO CUDA.
All heavy ML routed via cloud APIs; <=250MB RAM budget.

Usage:
    python app.py
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any module reads env vars
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from companion.brain.api_router import APIRouter
from companion.brain.cortex import Cortex
from companion.brain.priority_queue import EventQueue, PrioritizedEvent
from companion.brain.turn_controller import TurnController
from companion.desktop.chat_widget import ChatWidget
from companion.desktop.spatial_engine import SpatialEngine
from companion.dream.dream_engine import DreamEngine
from companion.expression.tts_engine import TTSEngine
from companion.expression.vts_connector import VTSConnector
from companion.expression.vts_expression_map import ExpressionController
from companion.learning.fact_extractor import FactExtractor
from companion.learning.memory_store import MemoryStore
from companion.model_setup.attribution import check_license
from companion.persona.emotion_matrix import EmotionMatrix
from companion.persona.prompt_engine import PromptEngine
from companion.senses.context_reader import ContextReader
from companion.senses.stt_pipeline import STTPipeline
from companion.senses.vision_agent import VisionAgent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "mycompanion.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("mycompanion")


class Orchestrator:
    """
    Top-level orchestrator wiring all subsystems together.

    Lifecycle:
      1. Initialize all components
      2. Wire callbacks (events -> cortex -> TTS + VTS + UI)
      3. Launch async tasks for each subsystem
      4. Run until shutdown signal
    """

    def __init__(self) -> None:
        # Core
        self._event_queue = EventQueue()
        self._turn_controller = TurnController()
        self._api_router = APIRouter()
        self._emotion_matrix = EmotionMatrix()
        self._prompt_engine = PromptEngine()

        # Memory
        self._memory = MemoryStore()
        self._fact_extractor = FactExtractor(self._memory)
        self._dream = DreamEngine()

        # Senses
        self._vision = VisionAgent()
        self._stt = STTPipeline()
        self._context_reader = ContextReader()

        # Expression
        self._tts = TTSEngine()
        self._vts = VTSConnector()
        self._expression = ExpressionController(self._vts)

        # Brain
        self._cortex = Cortex(
            event_queue=self._event_queue,
            turn_controller=self._turn_controller,
            api_router=self._api_router,
            emotion_matrix=self._emotion_matrix,
            prompt_engine=self._prompt_engine,
        )

        # Desktop (created later in Qt thread)
        self._chat_widget: ChatWidget | None = None
        self._spatial: SpatialEngine | None = None
        self._tasks: list[asyncio.Task] = []

    async def initialize(self) -> None:
        """Initialize all subsystems."""
        logger.info("=" * 60)
        logger.info("MyCompanion Framework - Initializing")
        logger.info("=" * 60)

        check_license()

        await self._memory.initialize()

        # Load facts for prompt context
        facts = await self._memory.get_all_facts_as_strings()
        self._prompt_engine.set_memory_facts(facts)

        # Load dream context seed
        seed = self._dream.load_context_seed()
        if seed:
            logger.info("Loaded dream context seed (%d chars)", len(seed))

        self._wire_callbacks()
        logger.info("All subsystems initialized")

    def _wire_callbacks(self) -> None:
        """Connect subsystem events to the cortex and output layers."""

        # STT transcript -> priority queue
        async def on_transcript(text: str) -> None:
            await self._turn_controller.user_stop_speaking()
            event = PrioritizedEvent.text_input(text)
            event.priority = 1  # voice priority
            await self._event_queue.put(event)
            self._dream.record_activity()
            self._spatial and self._spatial.record_user_input()

        self._stt.on_transcript(on_transcript)

        # Vision frame change -> cortex screen context
        async def on_frame_change(b64: str, raw: bytes) -> None:
            self._cortex.update_screen_context(f"Screen changed ({len(raw)} bytes)")

        self._vision.on_frame_change(on_frame_change)

        # Context reader -> cortex window context
        async def on_context_switch(title: str, app: str, wclass: str) -> None:
            ctx = f"{app}: {title}" if title else app
            self._cortex.update_window_context(ctx)
            self._dream.record_activity()

        self._context_reader.on_context_switch(on_context_switch)

        # Cortex response -> TTS + VTS + UI + memory
        async def on_response(text: str, emotion: str) -> None:
            # Update expression
            snap = self._emotion_matrix.snapshot()
            await self._expression.apply_emotion(snap)

            # Speak
            await self._tts.speak(text)

            # Update chat widget (if running)
            if self._chat_widget:
                self._chat_widget.add_message(text, is_ai=True, emotion=emotion)

            # Store in memory
            await self._memory.add_conversation(
                user_message="",
                ai_response=text,
                emotion=emotion,
            )

            # Log for dream engine
            self._dream.append_log("", text, emotion)

        self._cortex.on_response(on_response)

    async def run(self) -> None:
        """Launch all subsystem tasks and run until shutdown."""
        await self.initialize()

        vts_enabled = os.getenv("VTS_ENABLED", "false").lower() == "true"

        self._tasks = [
            asyncio.create_task(self._cortex.run(), name="cortex"),
            asyncio.create_task(self._vision.run(), name="vision"),
            asyncio.create_task(self._stt.run(), name="stt"),
            asyncio.create_task(self._context_reader.run(), name="context"),
            asyncio.create_task(self._dream.run(), name="dream"),
        ]

        if vts_enabled:
            self._tasks.append(asyncio.create_task(self._vts.run(), name="vts"))

        logger.info(
            "MyCompanion running (%d tasks, VTS=%s)",
            len(self._tasks),
            "ON" if vts_enabled else "OFF",
        )

        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass

    async def shutdown(self) -> None:
        """Graceful shutdown of all subsystems."""
        logger.info("Shutting down MyCompanion...")

        for t in self._tasks:
            t.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)

        await self._cortex.stop()
        await self._vision.stop()
        await self._stt.stop()
        await self._context_reader.stop()
        await self._dream.stop()
        await self._tts.stop()
        await self._vts.stop()
        await self._memory.close()

        logger.info("MyCompanion shutdown complete")

    def setup_qt_widget(self, app_instance: "QApplication") -> ChatWidget:
        """Create and wire up the PyQt6 chat widget."""
        from PyQt6.QtCore import QPoint

        self._chat_widget = ChatWidget()

        screen = app_instance.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self._spatial = SpatialEngine(geo.width(), geo.height())
            self._spatial.set_widget_rect(
                self._chat_widget.x(),
                self._chat_widget.y(),
                self._chat_widget.width(),
                self._chat_widget.height(),
            )

            def on_reposition(pos: QPoint) -> None:
                self._chat_widget.slide_to(pos)

            def on_idle_move(pos: QPoint) -> None:
                self._chat_widget.move(pos)

            self._spatial.on_reposition(on_reposition)
            self._spatial.on_idle_move(on_idle_move)

        # Wire chat input to event queue
        def on_chat_send(text: str) -> None:
            event = PrioritizedEvent.text_input(text)
            try:
                self._event_queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full; dropping text input")
            self._dream.record_activity()
            if self._spatial:
                self._spatial.record_user_input()
            # Add to UI
            self._prompt_engine.add_history("user", text)

        self._chat_widget.message_sent.connect(on_chat_send)
        self._chat_widget.show()
        return self._chat_widget


def _run_with_qt() -> None:
    """Run with PyQt6 GUI (default mode)."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("MyCompanion")

    orchestrator = Orchestrator()
    widget = orchestrator.setup_qt_widget(qt_app)

    loop = asyncio.new_event_loop()

    # Async tick via QTimer
    timer = QTimer()

    async def tick() -> None:
        await asyncio.sleep(0)

    def qt_tick() -> None:
        loop.run_until_complete(tick())

    timer.timeout.connect(qt_tick)
    timer.start(50)  # 20 Hz

    # Start async subsystems in background
    async def async_main() -> None:
        await orchestrator.run()

    import threading

    def run_async_loop() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_main())
        except Exception:
            logger.exception("Async loop error")

    thread = threading.Thread(target=run_async_loop, daemon=True)
    thread.start()

    # Handle shutdown
    def on_quit() -> None:
        loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(orchestrator.shutdown())
        )

    qt_app.aboutToQuit.connect(on_quit)

    sys.exit(qt_app.exec())


def _run_headless() -> None:
    """Run without GUI (headless mode for testing)."""
    orchestrator = Orchestrator()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_signal() -> None:
        loop.create_task(orchestrator.shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    try:
        loop.run_until_complete(orchestrator.run())
    except KeyboardInterrupt:
        loop.run_until_complete(orchestrator.shutdown())
    finally:
        loop.close()


def main() -> None:
    """Entrypoint: detect display and launch appropriate mode."""
    headless = os.getenv("MYCOMPANION_HEADLESS", "").lower() in ("1", "true", "yes")

    if headless or not os.getenv("DISPLAY"):
        logger.info("Starting in headless mode")
        _run_headless()
    else:
        logger.info("Starting with PyQt6 GUI")
        _run_with_qt()


if __name__ == "__main__":
    main()
