"""
Memory Store - SQLite + JSON Hybrid Datastore

Stores:
  - Conversation history (short-term ring buffer)
  - Extracted personal facts (long-term)
  - Interaction quality metrics
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

DB_PATH = Path("data/memory.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    emotion TEXT DEFAULT 'neutral',
    context TEXT DEFAULT '',
    importance REAL DEFAULT 0.5
);

CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    source TEXT DEFAULT 'extracted',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    access_count INTEGER DEFAULT 0,
    UNIQUE(category, key)
);

CREATE TABLE IF NOT EXISTS interaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_message TEXT,
    ai_response TEXT,
    reaction TEXT DEFAULT 'neutral',
    quality_score REAL DEFAULT 0.5
);

CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
"""


class MemoryStore:
    """
    Async SQLite memory store with JSON hybrid support.

    Designed for minimal memory usage: uses WAL mode and explicit
    cache eviction to stay under the 250MB framework budget.
    """

    MAX_SHORT_TERM = 100
    MAX_FACTS = 500

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional["aiosqlite.Connection"] = None

    async def initialize(self) -> None:
        if aiosqlite is None:
            logger.error("aiosqlite not installed; memory store disabled")
            return

        self._db = await aiosqlite.connect(str(self._db_path))
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA cache_size=500")  # ~2MB cache
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        logger.info("Memory store initialized: %s", self._db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    # --- Conversations ---

    async def add_conversation(
        self,
        user_message: str,
        ai_response: str,
        emotion: str = "neutral",
        context: str = "",
        importance: float = 0.5,
    ) -> None:
        if not self._db:
            return
        await self._db.execute(
            "INSERT INTO conversations (timestamp, user_message, ai_response, emotion, context, importance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), user_message, ai_response, emotion, context, importance),
        )
        await self._db.commit()
        await self._evict_old_conversations()

    async def get_recent_conversations(self, limit: int = 10) -> list[dict]:
        if not self._db:
            return []
        cursor = await self._db.execute(
            "SELECT user_message, ai_response, emotion, context FROM conversations "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {"user_message": r[0], "ai_response": r[1], "emotion": r[2], "context": r[3]}
            for r in reversed(rows)
        ]

    async def _evict_old_conversations(self) -> None:
        if not self._db:
            return
        cursor = await self._db.execute("SELECT COUNT(*) FROM conversations")
        (count,) = await cursor.fetchone()
        if count > self.MAX_SHORT_TERM:
            excess = count - self.MAX_SHORT_TERM
            await self._db.execute(
                "DELETE FROM conversations WHERE id IN "
                "(SELECT id FROM conversations ORDER BY id ASC LIMIT ?)",
                (excess,),
            )
            await self._db.commit()

    # --- Facts ---

    async def upsert_fact(
        self,
        category: str,
        key: str,
        value: str,
        confidence: float = 0.5,
        source: str = "extracted",
    ) -> None:
        if not self._db:
            return
        now = datetime.now().isoformat()
        await self._db.execute(
            "INSERT INTO facts (category, key, value, confidence, source, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(category, key) DO UPDATE SET "
            "value=excluded.value, confidence=excluded.confidence, updated_at=excluded.updated_at, "
            "access_count=access_count+1",
            (category, key, value, confidence, source, now, now),
        )
        await self._db.commit()

    async def get_facts(self, category: Optional[str] = None, limit: int = 50) -> list[dict]:
        if not self._db:
            return []
        if category:
            cursor = await self._db.execute(
                "SELECT category, key, value, confidence FROM facts "
                "WHERE category = ? ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                (category, limit),
            )
        else:
            cursor = await self._db.execute(
                "SELECT category, key, value, confidence FROM facts "
                "ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [
            {"category": r[0], "key": r[1], "value": r[2], "confidence": r[3]}
            for r in rows
        ]

    async def get_all_facts_as_strings(self) -> list[str]:
        """Return facts as human-readable strings for prompt injection."""
        facts = await self.get_facts(limit=30)
        return [f"[{f['category']}] {f['key']}: {f['value']}" for f in facts]

    # --- Interaction Quality ---

    async def log_interaction(
        self,
        user_message: str,
        ai_response: str,
        reaction: str = "neutral",
        quality_score: float = 0.5,
    ) -> None:
        if not self._db:
            return
        await self._db.execute(
            "INSERT INTO interaction_log (timestamp, user_message, ai_response, reaction, quality_score) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), user_message, ai_response, reaction, quality_score),
        )
        await self._db.commit()

    async def get_stats(self) -> dict:
        if not self._db:
            return {"status": "disabled"}

        conv_cursor = await self._db.execute("SELECT COUNT(*) FROM conversations")
        (conv_count,) = await conv_cursor.fetchone()

        fact_cursor = await self._db.execute("SELECT COUNT(*) FROM facts")
        (fact_count,) = await fact_cursor.fetchone()

        return {
            "conversations": conv_count,
            "facts": fact_count,
            "db_path": str(self._db_path),
        }
