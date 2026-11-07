"""Provider-neutral LLM and embedding client.

Design rules:
  * No provider SDK is imported; the protocol is OpenAI-compatible JSON over HTTP, so any gateway
    (self-hosted, Azure-compatible, vLLM, commercial) can be configured by base URL.
  * Timeouts, bounded retries with jittered backoff, and a per-process rate limiter.
  * Every call is measured and recorded by the caller (see `AiUsageLog`); this module never writes
    prompt or document text to logs.
  * Failures raise `AiUnavailable` so callers can fall back explicitly rather than silently.
"""
from __future__ import annotations

import json
import random
import time
from collections import deque
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("ai")


class AiUnavailable(RuntimeError):
    """Raised when the configured provider cannot serve the request."""

    def __init__(self, message: str, error_class: str = "upstream_error") -> None:
        super().__init__(message)
        self.error_class = error_class


@dataclass
class ChatResult:
    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    latency_ms: int


class _RateGate:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = max(per_minute, 1)
        self._stamps: deque[float] = deque()

    def wait(self) -> None:
        now = time.monotonic()
        while self._stamps and now - self._stamps[0] > 60:
            self._stamps.popleft()
        if len(self._stamps) >= self.per_minute:
            sleep_for = 60 - (now - self._stamps[0]) + 0.05
            if sleep_for > 0:
                time.sleep(min(sleep_for, 5.0))
        self._stamps.append(time.monotonic())


_gate = _RateGate(settings.ai_requests_per_minute)


class AiClient:
    def __init__(self) -> None:
        self.base_url = settings.ai_base_url.rstrip("/")
        self.api_key = settings.ai_api_key
        self.chat_model = settings.ai_chat_model
        self.embedding_model = settings.ai_embedding_model
        self.enabled = settings.ai_configured

    # ------------------------------------------------------------------ internals
    def _post(self, path: str, payload: dict) -> tuple[dict, int]:
        if not self.enabled:
            raise AiUnavailable("AI provider is not configured", "not_configured")

        _gate.wait()
        last_error: Exception | None = None
        started = time.perf_counter()

        for attempt in range(settings.ai_max_retries + 1):
            try:
                with httpx.Client(timeout=settings.ai_timeout_seconds) as client:
                    resp = client.post(
                        f"{self.base_url}{path}",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if resp.status_code in (401, 403):
                    raise AiUnavailable("AI provider rejected credentials", "auth_failed")
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_error = AiUnavailable(
                        f"AI provider returned {resp.status_code}", f"http_{resp.status_code}"
                    )
                    if attempt < settings.ai_max_retries:
                        time.sleep(min(2 ** attempt * 0.4 + random.random() * 0.3, 3.0))
                        continue
                    raise last_error
                if resp.status_code >= 400:
                    raise AiUnavailable(
                        f"AI provider returned {resp.status_code}", f"http_{resp.status_code}"
                    )
                return resp.json(), int((time.perf_counter() - started) * 1000)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = AiUnavailable("AI provider unreachable", "network")
                if attempt < settings.ai_max_retries:
                    time.sleep(min(2 ** attempt * 0.4 + random.random() * 0.3, 3.0))
                    continue
                raise last_error from exc

        raise last_error or AiUnavailable("AI provider failed", "unknown")

    # ------------------------------------------------------------------ public API
    def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], model=self.embedding_model, latency_ms=0)
        data, latency = self._post(
            "/embeddings", {"model": self.embedding_model, "input": texts}
        )
        rows = sorted(data.get("data", []), key=lambda r: r.get("index", 0))
        vectors = [row["embedding"] for row in rows]
        if len(vectors) != len(texts):
            raise AiUnavailable("Embedding response size mismatch", "bad_response")
        for vec in vectors:
            if len(vec) != settings.ai_embedding_dim:
                raise AiUnavailable(
                    f"Embedding dimension {len(vec)} does not match configured "
                    f"{settings.ai_embedding_dim}",
                    "dimension_mismatch",
                )
        return EmbeddingResult(vectors=vectors, model=self.embedding_model, latency_ms=latency)

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 900,
        json_mode: bool = False,
    ) -> ChatResult:
        payload: dict = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data, latency = self._post("/chat/completions", payload)
        try:
            choice = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise AiUnavailable("AI provider returned an unexpected payload", "bad_response") from exc
        usage = data.get("usage") or {}
        return ChatResult(
            text=(choice or "").strip(),
            model=data.get("model", self.chat_model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency,
        )

    def chat_json(self, system: str, user: str, *, max_tokens: int = 2000) -> tuple[dict, ChatResult]:
        """Chat with strict JSON parsing. Models sometimes wrap JSON in prose or code fences."""
        result = self.chat(system, user, temperature=0.1, max_tokens=max_tokens, json_mode=True)
        text = result.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise AiUnavailable("Model did not return JSON", "bad_response")
        try:
            return json.loads(text[start : end + 1]), result
        except json.JSONDecodeError as exc:
            raise AiUnavailable("Model returned malformed JSON", "bad_response") from exc

    def health(self) -> tuple[bool, str]:
        if not self.enabled:
            return False, "AI provider not configured"
        try:
            self.chat("You are a health probe.", "Reply with: ok", max_tokens=8)
            return True, "reachable"
        except AiUnavailable as exc:
            return False, str(exc)


ai = AiClient()
