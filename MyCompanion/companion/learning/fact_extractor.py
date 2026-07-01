"""
Fact Extractor - Personal Fact Mining

Scans conversation streams asynchronously using regex pattern matching
to capture personal facts about the user:
  - Preferences (likes, dislikes, favorites)
  - Identity details (name, age, occupation)
  - Habits and routines
  - Technical interests
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from companion.learning.memory_store import MemoryStore

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFact:
    category: str
    key: str
    value: str
    confidence: float


# Regex patterns for Vietnamese + English fact extraction
_PATTERNS: list[tuple[str, str, str, re.Pattern]] = [
    # Name patterns
    ("identity", "name", "user_name", re.compile(
        r"(?:tên\s+(?:tôi|mình|em|anh|chị)\s+là|tôi\s+là|i(?:'m| am)\s+|my name is\s+)(\w[\w\s]{1,20})",
        re.IGNORECASE,
    )),
    # Age
    ("identity", "age", "user_age", re.compile(
        r"(?:tôi|mình|em|anh|chị)\s+(\d{1,3})\s+tuổi|i(?:'m| am)\s+(\d{1,3})\s+years?\s+old",
        re.IGNORECASE,
    )),
    # Occupation
    ("identity", "occupation", "user_job", re.compile(
        r"(?:tôi|mình)\s+(?:là|làm)\s+([\w\s]{2,30}?)(?:\.|,|$)|i\s+(?:work as|am)\s+(?:a\s+)?([\w\s]{2,30}?)(?:\.|,|$)",
        re.IGNORECASE,
    )),
    # Likes
    ("preferences", "likes", "user_likes", re.compile(
        r"(?:tôi|mình|em)\s+(?:thích|yêu|mê)\s+([\w\s]{2,40}?)(?:\.|,|$)|i\s+(?:like|love|enjoy)\s+([\w\s]{2,40}?)(?:\.|,|$)",
        re.IGNORECASE,
    )),
    # Dislikes
    ("preferences", "dislikes", "user_dislikes", re.compile(
        r"(?:tôi|mình|em)\s+(?:ghét|không thích|chán)\s+([\w\s]{2,40}?)(?:\.|,|$)|i\s+(?:hate|dislike|don't like)\s+([\w\s]{2,40}?)(?:\.|,|$)",
        re.IGNORECASE,
    )),
    # Favorite things
    ("preferences", "favorite", "user_favorite", re.compile(
        r"(?:(?:cái|thứ|điều)\s+)?(?:tôi|mình)\s+thích\s+nhất\s+(?:là\s+)?([\w\s]{2,40}?)(?:\.|,|$)|my\s+favorite\s+(?:\w+\s+)?is\s+([\w\s]{2,40}?)(?:\.|,|$)",
        re.IGNORECASE,
    )),
    # Location
    ("identity", "location", "user_location", re.compile(
        r"(?:tôi|mình)\s+(?:ở|sống ở|đến từ)\s+([\w\s]{2,30}?)(?:\.|,|$)|i(?:'m| am)\s+(?:from|in|living in)\s+([\w\s]{2,30}?)(?:\.|,|$)",
        re.IGNORECASE,
    )),
    # Programming language / tech
    ("technical", "language", "programming_lang", re.compile(
        r"(?:tôi|mình)\s+(?:code|lập trình|viết)\s+(?:bằng\s+)?(python|java|rust|c\+\+|javascript|typescript|go|ruby|php|c#|swift|kotlin)",
        re.IGNORECASE,
    )),
    # OS preference
    ("technical", "os", "operating_system", re.compile(
        r"(?:tôi|mình)\s+(?:dùng|xài|sử dụng)\s+(arch|ubuntu|fedora|debian|windows|macos|linux)",
        re.IGNORECASE,
    )),
]


class FactExtractor:
    """
    Extracts personal facts from user messages using regex pipelines.
    Persists extracted facts to MemoryStore.
    """

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory
        self._total_extracted = 0

    async def extract_from_message(self, message: str) -> list[ExtractedFact]:
        """Extract all matching facts from a user message."""
        facts: list[ExtractedFact] = []

        for category, key_prefix, fact_key, pattern in _PATTERNS:
            match = pattern.search(message)
            if match:
                # Get the first non-None group
                value = next((g for g in match.groups() if g is not None), None)
                if value:
                    value = value.strip()
                    if len(value) < 2:
                        continue
                    fact = ExtractedFact(
                        category=category,
                        key=fact_key,
                        value=value,
                        confidence=0.7,
                    )
                    facts.append(fact)
                    await self._memory.upsert_fact(
                        category=fact.category,
                        key=fact.key,
                        value=fact.value,
                        confidence=fact.confidence,
                        source="regex",
                    )
                    self._total_extracted += 1
                    logger.info("Extracted fact: [%s] %s = %s", category, fact_key, value)

        return facts

    async def extract_batch(self, messages: list[str]) -> list[ExtractedFact]:
        """Extract facts from multiple messages."""
        all_facts: list[ExtractedFact] = []
        for msg in messages:
            facts = await self.extract_from_message(msg)
            all_facts.extend(facts)
        return all_facts

    @property
    def stats(self) -> dict:
        return {
            "total_extracted": self._total_extracted,
            "pattern_count": len(_PATTERNS),
        }
