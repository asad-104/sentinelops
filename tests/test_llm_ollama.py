"""Ollama client against httpx.MockTransport: request shape, parsing, errors as values. No network."""

from __future__ import annotations

import json

import httpx
import pytest

from sentinelops.llm.client import ChatMessage, LLMError, LLMResponse, ToolCallRequest
from sentinelops.llm.ollama import NonLocalEndpoint, OllamaClient
from sentinelops.llm.schemas import tool_specs


def _client(handler, **kwargs) -> OllamaClient:
    return OllamaClient("qwen3:4b", transport=httpx.MockTransport(handler), **kwargs)


def _ok(message: dict, **extra) -> httpx.Response:
    return httpx.Response(200, json={"model": "qwen3:4b", "message": message, "done": True, **extra})


def test_request_body_has_tools_no_streaming_and_explicit_context() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return _ok({"role": "assistant", "content": "ok"})

    history = [ChatMessage("system", "s"), ChatMessage("user", "u"),
               ChatMessage("assistant", "", tool_calls=(ToolCallRequest("c1", "get_alert", "{}"),)),
               ChatMessage("tool", '{"ok": true}', tool_name="get_alert", tool_call_id="c1")]
    _client(handler).chat(history, tool_specs())
    body = seen["body"]
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert body["stream"] is False and body["model"] == "qwen3:4b"
    assert body["options"] == {"num_ctx": 8192, "temperature": 0, "seed": 0}
    assert "think" not in body  # left to the server unless configured
    assert {t["function"]["name"] for t in body["tools"]} >= {"search_logs", "submit_report"}
    assert all(t["type"] == "function" for t in body["tools"])
    assert body["messages"][2]["tool_calls"] == [{"function": {"name": "get_alert", "arguments": {}}}]
    assert body["messages"][3] == {"role": "tool", "content": '{"ok": true}', "tool_name": "get_alert"}


def test_think_is_sent_only_when_configured() -> None:
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _ok({"role": "assistant", "content": ""})

    _client(handler, think=False).chat([ChatMessage("user", "u")], [])
    assert bodies[-1]["think"] is False


def test_tool_calls_usage_and_thinking_are_parsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok({"role": "assistant", "content": "", "thinking": "abcde",
                    "tool_calls": [{"function": {"name": "search_logs", "arguments": {"limit": 5}}},
                                   {"id": "x9", "function": {"name": "get_alert", "arguments": "{}"}}]},
                   prompt_eval_count=120, eval_count=30)

    response = _client(handler).chat([ChatMessage("user", "u")], [])
    assert isinstance(response, LLMResponse)
    assert response.tool_calls == (ToolCallRequest("call-0", "search_logs", '{"limit": 5}'),
                                   ToolCallRequest("x9", "get_alert", "{}"))
    assert (response.usage.prompt_tokens, response.usage.completion_tokens) == (120, 30)
    assert response.thinking_chars == 5


@pytest.mark.parametrize("handler, code", [
    (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=r)), "timeout"),
    (lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused", request=r)), "connection"),
    (lambda r: httpx.Response(500, text="model crashed"), "http_status"),
    (lambda r: httpx.Response(200, text="not json"), "bad_response"),
    (lambda r: httpx.Response(200, json={"done": True}), "bad_response"),
    (lambda r: httpx.Response(200, json={"message": {"tool_calls": [{"function": {}}]}}), "bad_response"),
], ids=["timeout", "connection", "http_500", "not_json", "no_message", "tool_call_without_name"])
def test_failures_are_returned_as_values(handler, code: str) -> None:
    result = _client(handler).chat([ChatMessage("user", "u")], [])
    assert isinstance(result, LLMError) and result.code == code


@pytest.mark.parametrize("url", ["https://api.example.com", "http://10.0.0.5:11434", "http://ollama.local:11434"])
def test_non_loopback_endpoints_are_refused(url: str) -> None:
    with pytest.raises(NonLocalEndpoint):
        OllamaClient("qwen3:4b", base_url=url)


def test_describe_is_plain_configuration() -> None:
    described = OllamaClient("qwen3:4b").describe()
    assert described["backend"] == "ollama" and described["model"] == "qwen3:4b"
    assert not any("key" in k.lower() or "token" in k.lower() for k in described)
