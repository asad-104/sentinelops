"""Ollama chat client over httpx (``POST /api/chat`` with tools, non-streaming).

Local only: a base URL whose host is not loopback is refused at construction.
Every failure becomes an ``LLMError`` value. The request shape follows Ollama's
documented chat API. It is checked against a real server only in stage B (the
first smoke run), so mismatches will show up there as ``bad_response`` errors.
"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from sentinelops.llm.client import ChatMessage, LLMError, LLMResponse, ToolCallRequest, ToolSpec, Usage

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_BASE_URL = "http://127.0.0.1:11434"


class NonLocalEndpoint(ValueError):
    """Raised when the Ollama client is pointed at a non-loopback host."""


class OllamaClient:
    def __init__(self, model: str, *, base_url: str = DEFAULT_BASE_URL, timeout_s: float = 180.0,
                 num_ctx: int = 8192, seed: int = 0, think: bool | None = None, keep_alive: str = "5m",
                 transport: httpx.BaseTransport | None = None) -> None:
        host = urlparse(base_url).hostname
        if host not in LOOPBACK_HOSTS:
            raise NonLocalEndpoint(f"Ollama client is local only; refusing host {host!r}")
        self.model, self.base_url, self.timeout_s = model, base_url, timeout_s
        self.num_ctx, self.seed, self.think, self.keep_alive = num_ctx, seed, think, keep_alive
        self._http = httpx.Client(base_url=base_url, timeout=httpx.Timeout(timeout_s), transport=transport)

    def describe(self) -> dict[str, Any]:
        return {"backend": "ollama", "model": self.model, "base_url": self.base_url, "timeout_s": self.timeout_s,
                "num_ctx": self.num_ctx, "seed": self.seed, "temperature": 0, "think": self.think,
                "keep_alive": self.keep_alive}

    def request_body(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [_message(m) for m in messages],
            "tools": [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                        "parameters": t.parameters}} for t in tools],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"num_ctx": self.num_ctx, "temperature": 0, "seed": self.seed},
        }
        if self.think is not None:
            body["think"] = self.think
        return body

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError:
        started = time.monotonic()
        try:
            response = self._http.post("/api/chat", json=self.request_body(messages, tools))
        except httpx.TimeoutException as exc:
            return LLMError("timeout", f"{type(exc).__name__}", time.monotonic() - started)
        except httpx.TransportError as exc:
            return LLMError("connection", f"{type(exc).__name__}", time.monotonic() - started)
        latency = time.monotonic() - started
        if response.status_code != 200:
            return LLMError("http_status", f"HTTP {response.status_code}: {response.text[:300]}", latency)
        try:
            return _parse(response.json(), latency)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return LLMError("bad_response", f"unparseable response ({type(exc).__name__})", latency)


def _message(m: ChatMessage) -> dict[str, Any]:
    out: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        out["tool_calls"] = [{"function": {"name": c.name, "arguments": _arguments_object(c.raw_arguments)}}
                             for c in m.tool_calls]
    if m.tool_name:
        out["tool_name"] = m.tool_name
    return out


def _arguments_object(raw: str) -> Any:
    """Ollama expects arguments as an object when replaying history; keep malformed text as a string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse(data: dict[str, Any], latency: float) -> LLMResponse:
    message = data["message"]
    calls = []
    for i, tc in enumerate(message.get("tool_calls") or []):
        fn = tc["function"]
        arguments = fn.get("arguments", {})
        raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
        calls.append(ToolCallRequest(tc.get("id") or f"call-{i}", str(fn["name"]), raw))
    return LLMResponse(text=message.get("content") or "", tool_calls=tuple(calls),
                       usage=Usage(data.get("prompt_eval_count"), data.get("eval_count")), latency_s=latency,
                       thinking_chars=len(message.get("thinking") or ""))
