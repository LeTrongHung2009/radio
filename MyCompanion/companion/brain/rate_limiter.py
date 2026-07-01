"""
Token-Bucket Rate Limiter
Deterministic rate limiting for cloud API calls.
Prevents 429 errors on Groq Free Tier and other providers.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Token-bucket rate limiter.

    Allows `capacity` requests per `refill_period` seconds.
    Tokens refill at a constant rate.
    """

    capacity: float
    refill_rate: float  # tokens per second
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens. Blocks until enough tokens are available.
        Returns the wait time in seconds (0.0 if no wait).
        """
        waited = 0.0
        async with self._lock:
            self._refill()
            while self._tokens < tokens:
                deficit = tokens - self._tokens
                sleep_time = deficit / self.refill_rate
                waited += sleep_time
                logger.debug("Rate limiter: waiting %.2fs for %.1f tokens", sleep_time, tokens)
                await asyncio.sleep(sleep_time)
                self._refill()
            self._tokens -= tokens
        return waited

    @property
    def available(self) -> float:
        self._refill()
        return self._tokens


def create_groq_limiter() -> TokenBucket:
    """Groq free tier: ~30 requests/min => 0.5 req/s."""
    return TokenBucket(capacity=30.0, refill_rate=0.5)


def create_openai_limiter() -> TokenBucket:
    """OpenAI rate limit (conservative)."""
    return TokenBucket(capacity=60.0, refill_rate=1.0)


def create_anthropic_limiter() -> TokenBucket:
    """Anthropic rate limit (conservative)."""
    return TokenBucket(capacity=60.0, refill_rate=1.0)
