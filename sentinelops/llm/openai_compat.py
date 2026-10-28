"""OpenAI-compatible chat client over httpx (``POST {base}/chat/completions`` with tools, non-streaming).

Hosted, free tier only (decision 2026-10-28, docs/PROGRESS.md): requests go only to the registered
provider's own host over HTTPS, with no redirects. The API key is read from the provider's environment
variable and is never returned by ``describe()``, written to a trace or kept in an error message.
Every failure becomes an ``LLMError`` value. 429 and 5xx responses are retried with backoff
(``retry-after`` when the server sends it); a wait above ``max_wait_s`` is not slept through but
returned as an error, since it usually means a daily limit. A client-side pace keeps requests under
the provider's per-minute request and token limits. Retries and every second slept are returned on
the result, so the agent trace records them. The request shape follows the provider's documented
OpenAI compatibility; it is checked against a real server only in the hosted smoke run.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from sentinelops.llm.client import ChatMessage, LLMError, LLMResponse, ToolCallRequest, ToolSpec, Usage

ORG_ID = re.compile(r"\borg_[A-Za-z0-9]{6,}")


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    key_env: str


# Only providers whose free tier needs no card (research 2026-10-28). Add one only with a logged decision.
PROVIDERS: dict[str, Provider] = {
    "groq": Provider("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
}


@dataclass(frozen=True)
class RateLimits:
    requests_per_minute: int
    tokens_per_minute: int


class DisallowedEndpoint(ValueError):
    """Raised for an unregistered provider or a base URL that is not HTTPS."""


class MissingKey(ValueError):
    """Raised when the provider's key variable is unset. The message names the variable, never a value."""


class OpenAICompatibleClient:
    def __init__(self, provider: str, model: str, *, limits: RateLimits, timeout_s: float = 180.0,
                 max_tokens: int = 2048, extra: Mapping[str, Any] | None = None, max_retries: int = 4,
                 max_wait_s: float = 120.0, environ: Mapping[str, str] = os.environ,
                 transport: httpx.BaseTransport | None = None, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, today: str | None = None) -> None:
        if provider not in PROVIDERS:
            raise DisallowedEndpoint(f"unregistered provider {provider!r}; known: {', '.join(PROVIDERS)}")
        self.provider = PROVIDERS[provider]
        url = urlparse(self.provider.base_url)
        if url.scheme != "https" or not url.hostname:
            raise DisallowedEndpoint(f"provider {provider!r} must use an https base URL")
        key = environ.get(self.provider.key_env, "")
        if not key.strip():
            raise MissingKey(f"{self.provider.key_env} is not set")
        self._key = key.strip()
        self.host = url.hostname
        self.model, self.limits, self.timeout_s, self.max_tokens = model, limits, timeout_s, max_tokens
        self.extra = dict(extra or {})
        self.max_retries, self.max_wait_s = max_retries, max_wait_s
        self.clock, self.sleep = clock, sleep
        self.date_utc = today or datetime.now(timezone.utc).date().isoformat()
        self._window: deque[tuple[float, int]] = deque()  # (finish time, tokens) of successful requests
        self._last_start: float | None = None
        self._last_tokens = 0
        self._http = httpx.Client(base_url=self.provider.base_url, timeout=httpx.Timeout(timeout_s),
                                  transport=transport, follow_redirects=False,
                                  headers={"Authorization": f"Bearer {self._key}"})

    def __repr__(self) -> str:
        return f"OpenAICompatibleClient(provider={self.provider.name!r}, model={self.model!r})"

    def describe(self) -> dict[str, Any]:
        return {"backend": self.provider.name, "api": "openai-compatible", "host": self.host, "model": self.model,
                "date_utc": self.date_utc, "timeout_s": self.timeout_s, "temperature": 0,
                "max_completion_tokens": self.max_tokens, "extra": self.extra,
                "rate_limits": {"requests_per_minute": self.limits.requests_per_minute,
                                "tokens_per_minute": self.limits.tokens_per_minute},
                "max_retries": self.max_retries, "max_wait_s": self.max_wait_s, "key_env": self.provider.key_env}

    def request_body(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [_message(m) for m in messages],
            "tools": [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                        "parameters": t.parameters}} for t in tools],
            "temperature": 0,
            "max_completion_tokens": self.max_tokens,
            **self.extra,
        }

    def unload(self) -> LLMError | None:
        """Nothing to unload on a hosted backend."""
        return None

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError:
        body = self.request_body(messages, tools)
        waited = self._pace()
        retries, latency = 0, 0.0
        while True:
            started = self.clock()
            self._last_start = started
            try:
                response = self._http.post("/chat/completions", json=body)
            except httpx.TimeoutException as exc:
                return LLMError("timeout", type(exc).__name__, self.clock() - started, retries, waited)
            except httpx.TransportError as exc:
                return LLMError("connection", type(exc).__name__, self.clock() - started, retries, waited)
            latency = self.clock() - started
            status = response.status_code
            if status == 429 or 500 <= status < 600:
                delay = _retry_after(response)
                if delay is None:
                    delay = min(2.0 * 2 ** retries, self.max_wait_s)
                if delay > self.max_wait_s:
                    return LLMError("http_status", f"HTTP {status}: provider asks to wait {delay:.0f} s, above the "
                                    f"{self.max_wait_s:.0f} s cap (likely a daily limit): {self._clean(response)}",
                                    latency, retries, waited)
                if retries >= self.max_retries:
                    return LLMError("http_status", f"HTTP {status} after {retries} retries: {self._clean(response)}",
                                    latency, retries, waited)
                self.sleep(delay)
                waited += delay
                retries += 1
                continue
            if status != 200:
                return LLMError("http_status", f"HTTP {status}: {self._clean(response)}", latency, retries, waited)
            try:
                result = _parse(response.json(), latency, retries, waited)
            except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
                return LLMError("bad_response", f"unparseable response ({type(exc).__name__})", latency, retries,
                                waited)
            used = (result.usage.prompt_tokens or 0) + (result.usage.completion_tokens or 0)
            self._window.append((self.clock(), used))
            self._last_tokens = used
            return result

    def _pace(self) -> float:
        """Sleep so the next request stays under the per-minute limits; returns the seconds slept."""
        waited = 0.0
        if self._last_start is not None:
            gap = 60.0 / self.limits.requests_per_minute - (self.clock() - self._last_start)
            if gap > 0:
                self.sleep(gap)
                waited += gap
        while self._window:
            now = self.clock()
            while self._window and now - self._window[0][0] >= 60.0:
                self._window.popleft()
            used = sum(tokens for _, tokens in self._window)
            if not self._window or used + self._last_tokens <= self.limits.tokens_per_minute:
                break
            delay = self._window[0][0] + 60.0 - now
            self.sleep(delay)
            waited += delay
        return waited

    def _clean(self, response: httpx.Response) -> str:
        """A short error body with the key and organization IDs removed (Groq's 429 names the organization)."""
        return ORG_ID.sub("org_[redacted]", response.text.replace(self._key, "[redacted]"))[:300]


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    try:
        return max(0.0, float(value)) if value is not None else None
    except ValueError:
        return None


def _message(m: ChatMessage) -> dict[str, Any]:
    if m.role == "tool":
        return {"role": "tool", "tool_call_id": m.tool_call_id or "", "content": m.content}
    out: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        out["tool_calls"] = [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.raw_arguments}}
                             for c in m.tool_calls]
        if not m.content:
            out["content"] = None
    return out


def _parse(data: dict[str, Any], latency: float, retries: int, waited: float) -> LLMResponse:
    choice = data["choices"][0]
    message = choice["message"]
    calls = []
    for i, tc in enumerate(message.get("tool_calls") or []):
        fn = tc["function"]
        arguments = fn.get("arguments", "")
        raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
        calls.append(ToolCallRequest(tc.get("id") or f"call-{i}", str(fn["name"]), raw))
    usage = data.get("usage") or {}
    return LLMResponse(text=message.get("content") or "", tool_calls=tuple(calls),
                       usage=Usage(usage.get("prompt_tokens"), usage.get("completion_tokens")), latency_s=latency,
                       thinking_chars=len(message.get("reasoning") or ""), total_s=latency,
                       truncated=choice.get("finish_reason") == "length", retries=retries, wait_s=waited)
