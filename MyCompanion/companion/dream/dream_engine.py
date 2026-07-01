"""
Dream Engine - Cognitive Sleep & Memory Consolidation

When the user is completely idle for >600 seconds, the AI enters "Sleep state".
Triggers a background consolidation routine:
  1. Parse the day's conversation log
  2. Condense repetitive entries into summaries
  3. Calculate importance scores
  4. Merge new facts into long-term memory
  5. Craft an optimized context seed for the next session
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DREAM_IDLE_THRESHOLD = 600.0  # seconds (10 minutes)
CONSOLIDATION_INTERVAL = 600.0  # run every 10 minutes while asleep


class DreamEngine:
    """
    Cognitive sleep loop.

    Monitors idle time. When threshold is reached, enters sleep state
    and begins memory consolidation in the background.
    """

    DATA_DIR = Path("data")
    DREAM_LOG = DATA_DIR / "dream_log.json"
    CONTEXT_SEED = DATA_DIR / "context_seed.txt"

    def __init__(self) -> None:
        self._running = False
        self._is_sleeping = False
        self._last_user_activity = time.monotonic()
        self._consolidation_count = 0
        self._on_sleep_cb: Optional[callable] = None
        self._on_wake_cb: Optional[callable] = None

        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def record_activity(self) -> None:
        was_sleeping = self._is_sleeping
        self._last_user_activity = time.monotonic()
        if was_sleeping:
            self._is_sleeping = False
            logger.info("Dream engine: user returned, waking up")
            if self._on_wake_cb:
                try:
                    self._on_wake_cb()
                except Exception:
                    logger.exception("Wake callback error")

    def on_sleep(self, cb: callable) -> None:
        self._on_sleep_cb = cb

    def on_wake(self, cb: callable) -> None:
        self._on_wake_cb = cb

    @property
    def is_sleeping(self) -> bool:
        return self._is_sleeping

    async def run(self) -> None:
        self._running = True
        logger.info("Dream engine started (threshold=%.0fs)", DREAM_IDLE_THRESHOLD)

        try:
            while self._running:
                idle = time.monotonic() - self._last_user_activity

                if not self._is_sleeping and idle >= DREAM_IDLE_THRESHOLD:
                    self._is_sleeping = True
                    logger.info("Dream engine: entering sleep state (idle=%.0fs)", idle)
                    if self._on_sleep_cb:
                        try:
                            self._on_sleep_cb()
                        except Exception:
                            logger.exception("Sleep callback error")
                    await self._consolidate()

                if self._is_sleeping:
                    await asyncio.sleep(CONSOLIDATION_INTERVAL)
                    if self._is_sleeping:
                        await self._consolidate()
                else:
                    await asyncio.sleep(30.0)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Dream engine stopped (consolidations=%d)", self._consolidation_count)

    async def stop(self) -> None:
        self._running = False

    async def _consolidate(self) -> None:
        """Run one consolidation cycle."""
        self._consolidation_count += 1
        logger.info("Dream consolidation #%d starting", self._consolidation_count)

        try:
            logs = await self._load_today_logs()
            if not logs:
                logger.debug("No conversation logs to consolidate")
                return

            summaries = self._condense_logs(logs)
            scored = self._score_importance(summaries)
            await self._merge_to_longterm(scored)
            await self._build_context_seed(scored)

            logger.info(
                "Consolidation complete: %d logs -> %d summaries",
                len(logs),
                len(summaries),
            )
        except Exception:
            logger.exception("Dream consolidation error")

    async def _load_today_logs(self) -> list[dict]:
        """Load today's conversation entries from the transaction log."""
        log_file = self.DATA_DIR / f"log_{date.today().isoformat()}.jsonl"
        if not log_file.exists():
            return []

        entries = []
        try:
            async with asyncio.Lock():
                text = await asyncio.get_event_loop().run_in_executor(
                    None, log_file.read_text, "utf-8"
                )
            for line in text.strip().split("\n"):
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            logger.exception("Failed to load today's logs")
        return entries

    @staticmethod
    def _condense_logs(logs: list[dict]) -> list[dict]:
        """Merge repetitive log entries into conceptual summaries."""
        seen_topics: dict[str, dict] = {}
        for entry in logs:
            topic = entry.get("topic", entry.get("user_message", "")[:30])
            key = topic.lower().strip()
            if key in seen_topics:
                seen_topics[key]["count"] += 1
                seen_topics[key]["latest"] = entry
            else:
                seen_topics[key] = {
                    "topic": topic,
                    "count": 1,
                    "first": entry,
                    "latest": entry,
                }

        summaries = []
        for key, data in seen_topics.items():
            summaries.append({
                "topic": data["topic"],
                "frequency": data["count"],
                "summary": data["latest"].get("ai_response", ""),
                "emotion": data["latest"].get("emotion", "neutral"),
                "timestamp": data["latest"].get("timestamp", ""),
            })
        return summaries

    @staticmethod
    def _score_importance(summaries: list[dict]) -> list[dict]:
        """Assign importance scores based on frequency and emotional weight."""
        emotion_weights = {
            "happy": 0.6,
            "excited": 0.7,
            "sad": 0.8,
            "angry": 0.9,
            "surprised": 0.7,
            "concerned": 0.6,
            "neutral": 0.3,
            "bored": 0.2,
            "curious": 0.5,
            "playful": 0.4,
            "thoughtful": 0.5,
        }
        for s in summaries:
            freq_score = min(1.0, s["frequency"] / 5.0)
            emo_score = emotion_weights.get(s.get("emotion", "neutral"), 0.3)
            s["importance"] = round(freq_score * 0.4 + emo_score * 0.6, 3)

        summaries.sort(key=lambda x: x["importance"], reverse=True)
        return summaries

    async def _merge_to_longterm(self, scored: list[dict]) -> None:
        """Persist high-importance summaries to long-term dream log."""
        important = [s for s in scored if s["importance"] >= 0.4]
        if not important:
            return

        existing = []
        if self.DREAM_LOG.exists():
            try:
                raw = await asyncio.get_event_loop().run_in_executor(
                    None, self.DREAM_LOG.read_text, "utf-8"
                )
                existing = json.loads(raw)
            except Exception:
                existing = []

        existing.extend(important)
        # Keep only the most recent 200 entries
        if len(existing) > 200:
            existing = existing[-200:]

        await asyncio.get_event_loop().run_in_executor(
            None,
            self.DREAM_LOG.write_text,
            json.dumps(existing, ensure_ascii=False, indent=2),
            "utf-8",
        )

    async def _build_context_seed(self, scored: list[dict]) -> None:
        """Create a compact prompt seed for the next session startup."""
        top = scored[:10]
        lines = [
            f"Ngày {date.today().isoformat()} - Tóm tắt giấc mơ:",
            "",
        ]
        for s in top:
            lines.append(
                f"- [{s['emotion']}] {s['topic']} (importance: {s['importance']})"
            )

        seed_text = "\n".join(lines)
        await asyncio.get_event_loop().run_in_executor(
            None, self.CONTEXT_SEED.write_text, seed_text, "utf-8"
        )
        logger.debug("Context seed updated (%d bytes)", len(seed_text))

    def append_log(self, user_message: str, ai_response: str, emotion: str, topic: str = "") -> None:
        """Append a conversation turn to today's log (called from cortex)."""
        log_file = self.DATA_DIR / f"log_{date.today().isoformat()}.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response,
            "emotion": emotion,
            "topic": topic or user_message[:30],
        }
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to append to conversation log")

    def load_context_seed(self) -> str:
        """Load the context seed from the last dream consolidation."""
        if self.CONTEXT_SEED.exists():
            try:
                return self.CONTEXT_SEED.read_text("utf-8")
            except Exception:
                return ""
        return ""

    @property
    def stats(self) -> dict:
        return {
            "is_sleeping": self._is_sleeping,
            "idle_seconds": time.monotonic() - self._last_user_activity,
            "consolidation_count": self._consolidation_count,
        }
