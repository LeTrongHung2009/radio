"""
API Orchestration Router

Persistent async routing client with deterministic fallback:
  Groq (Llama 3.3 / 3.2 Vision)  ->  OpenAI  ->  Anthropic

Integrates the token-bucket rate limiter per provider.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from companion.brain.rate_limiter import (
    TokenBucket,
    create_anthropic_limiter,
    create_groq_limiter,
    create_openai_limiter,
)

logger = logging.getLogger(__name__)

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_MSG_URL = "https://api.anthropic.com/v1/messages"


@dataclass
class LLMResponse:
    text: str
    emotion: str = "neutral"
    provider: str = "unknown"
    model: str = "unknown"
    tokens_used: int = 0
    latency_ms: float = 0.0
    cached: bool = False


@dataclass
class _ProviderSlot:
    name: str
    url: str
    api_key: str
    model: str
    limiter: TokenBucket
    consecutive_failures: int = 0
    _backoff_until: float = 0.0

    @property
    def available(self) -> bool:
        if not self.api_key:
            return False
        return time.monotonic() >= self._backoff_until

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        backoff = min(60.0, 2 ** self.consecutive_failures)
        self._backoff_until = time.monotonic() + backoff
        logger.warning(
            "%s: failure #%d, backing off %.1fs",
            self.name,
            self.consecutive_failures,
            backoff,
        )

    def record_success(self) -> None:
        self.consecutive_failures = 0


class APIRouter:
    """
    Multi-provider LLM router with automatic fallback.
    All heavy inference goes to the cloud — zero local GPU usage.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0, http2=True)
        self._providers: list[_ProviderSlot] = []
        self._setup_providers()
        self._total_requests = 0
        self._total_tokens = 0

    def _setup_providers(self) -> None:
        groq_key = os.getenv("GROQ_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        self._providers = [
            _ProviderSlot(
                name="groq",
                url=_GROQ_CHAT_URL,
                api_key=groq_key,
                model="llama-3.3-70b-versatile",
                limiter=create_groq_limiter(),
            ),
            _ProviderSlot(
                name="openai",
                url=_OPENAI_CHAT_URL,
                api_key=openai_key,
                model="gpt-4o-mini",
                limiter=create_openai_limiter(),
            ),
            _ProviderSlot(
                name="anthropic",
                url=_ANTHROPIC_MSG_URL,
                api_key=anthropic_key,
                model="claude-3-haiku-20240307",
                limiter=create_anthropic_limiter(),
            ),
        ]

        configured = [p.name for p in self._providers if p.api_key]
        logger.info("API router configured providers: %s", configured or ["NONE"])

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Send chat completion through the provider cascade.
        Returns the first successful response.
        """
        self._total_requests += 1
        last_error: Optional[Exception] = None

        for slot in self._providers:
            if not slot.available:
                continue
            try:
                await slot.limiter.acquire()
                t0 = time.monotonic()

                if slot.name == "anthropic":
                    resp = await self._call_anthropic(slot, messages, temperature, max_tokens)
                else:
                    resp = await self._call_openai_compat(slot, messages, temperature, max_tokens)

                resp.latency_ms = (time.monotonic() - t0) * 1000
                slot.record_success()
                self._total_tokens += resp.tokens_used
                return resp
            except Exception as exc:
                last_error = exc
                slot.record_failure()
                logger.error("Provider %s failed: %s", slot.name, exc)

        logger.error("All providers exhausted. Returning fallback.")
        return LLMResponse(
            text="Xin lỗi, mình đang gặp sự cố kết nối. Thử lại sau nhé!",
            emotion="concerned",
            provider="fallback",
        )

    async def _call_openai_compat(
        self,
        slot: _ProviderSlot,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {slot.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": slot.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        r = await self._client.post(slot.url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        text, emotion = self._parse_json_response(content)
        return LLMResponse(
            text=text,
            emotion=emotion,
            provider=slot.name,
            model=slot.model,
            tokens_used=tokens,
        )

    async def _call_anthropic(
        self,
        slot: _ProviderSlot,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)

        headers = {
            "x-api-key": slot.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": slot.model,
            "max_tokens": max_tokens,
            "system": system_msg,
            "messages": user_msgs,
            "temperature": temperature,
        }
        r = await self._client.post(slot.url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        content = data["content"][0]["text"]
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
        text, emotion = self._parse_json_response(content)
        return LLMResponse(
            text=text,
            emotion=emotion,
            provider=slot.name,
            model=slot.model,
            tokens_used=tokens,
        )

    @staticmethod
    def _parse_json_response(raw: str) -> tuple[str, str]:
        try:
            parsed = json.loads(raw)
            return parsed.get("text", raw), parsed.get("emotion", "neutral")
        except (json.JSONDecodeError, AttributeError):
            return raw.strip(), "neutral"

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "providers": {
                p.name: {
                    "available": p.available,
                    "failures": p.consecutive_failures,
                    "has_key": bool(p.api_key),
                }
                for p in self._providers
            },
        }
