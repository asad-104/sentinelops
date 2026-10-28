"""OpenAI-compatible hosted client: request shape, parsing, backoff, pacing, key handling, and a full agent run,
all offline with httpx.MockTransport (the network guard in conftest blocks real sockets)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from sentinelops.agent.machine import StateMachineInvestigator
from sentinelops.evaluation import agent_run
from sentinelops.evaluation.harness import CountingToolSet
from sentinelops.llm.client import ChatMessage, LLMError, LLMResponse, ToolCallRequest, ToolSpec
from sentinelops.llm.openai_compat import (
    DisallowedEndpoint,
    MissingKey,
    OpenAICompatibleClient,
    RateLimits,
)
from sentinelops.llm.trace import TraceWriter
from sentinelops.report import InvestigationFailed
from sentinelops.tools import ToolSet

KEY = "gsk_test_secret_value_123"
ENV = {"GROQ_API_KEY": KEY}
SPEC = ToolSpec("search_logs", "Search logs.", {"type": "object", "properties": {"limit": {"type": "integer"}}})


class FakeTime:
    def __init__(self) -> None:
        self.now, self.slept = 1000.0, []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _ok(calls=(), content="", prompt=100, completion=10, finish="tool_calls", reasoning=None) -> httpx.Response:
    message = {"role": "assistant", "content": content,
               "tool_calls": [{"id": f"call_{i}", "type": "function", "function": {"name": n, "arguments": a}}
                              for i, (n, a) in enumerate(calls)] or None}
    if reasoning is not None:
        message["reasoning"] = reasoning
    return httpx.Response(200, json={"model": "qwen/qwen3.8-27b", "choices": [
        {"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion}})


def _client(handler, time_: FakeTime | None = None, limits=RateLimits(1000, 10_000_000), **kwargs):
    t = time_ or FakeTime()
    return OpenAICompatibleClient("groq", "qwen/qwen3.8-27b", limits=limits, environ=ENV,
                                  transport=httpx.MockTransport(handler), clock=t.clock, sleep=t.sleep,
                                  today="2026-10-28", extra={"reasoning_effort": "none"}, **kwargs), t


def test_request_shape_host_auth_and_message_conversion() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _ok([("search_logs", '{"limit": 2}')])

    client, _ = _client(handler)
    messages = [ChatMessage("system", "sys"), ChatMessage("user", "hi"),
                ChatMessage("assistant", "", tool_calls=(ToolCallRequest("call_9", "search_logs", '{"limit": 1}'),)),
                ChatMessage("tool", '{"ok": true}', tool_name="search_logs", tool_call_id="call_9")]
    result = client.chat(messages, [SPEC])
    assert isinstance(result, LLMResponse)
    request = seen[0]
    assert request.url == httpx.URL("https://api.groq.com/openai/v1/chat/completions")
    assert request.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(request.content)
    assert body["model"] == "qwen/qwen3.8-27b" and body["temperature"] == 0
    assert body["max_completion_tokens"] == 2048 and body["reasoning_effort"] == "none"
    assert body["tools"] == [{"type": "function", "function": {"name": "search_logs", "description": "Search logs.",
                                                               "parameters": SPEC.parameters}}]
    assert body["messages"][2] == {"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_9", "type": "function", "function": {"name": "search_logs", "arguments": '{"limit": 1}'}}]}
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "call_9", "content": '{"ok": true}'}
    assert all("name" not in m for m in body["messages"])  # messages[].name is a 400 on Groq


def test_parses_calls_usage_truncation_and_reasoning_length() -> None:
    client, _ = _client(lambda r: _ok([("search_logs", '{"limit": 3}')], prompt=4200, completion=33,
                                      finish="length", reasoning="abc"))
    result = client.chat([ChatMessage("user", "x")], [SPEC])
    assert isinstance(result, LLMResponse)
    assert result.tool_calls == (ToolCallRequest("call_0", "search_logs", '{"limit": 3}'),)
    assert (result.usage.prompt_tokens, result.usage.completion_tokens) == (4200, 33)
    assert result.truncated and result.thinking_chars == 3 and result.retries == 0 and result.wait_s == 0.0


def test_429_honours_retry_after_and_counts_the_retry() -> None:
    replies = [httpx.Response(429, headers={"retry-after": "7"}, text="rate limit"), _ok()]
    client, t = _client(lambda r: replies.pop(0))
    result = client.chat([ChatMessage("user", "x")], [SPEC])
    assert isinstance(result, LLMResponse) and result.retries == 1 and result.wait_s == 7.0
    assert t.slept == [7.0]


def test_5xx_backs_off_exponentially_then_gives_up_with_the_count() -> None:
    client, t = _client(lambda r: httpx.Response(503, text="busy"), max_retries=3)
    result = client.chat([ChatMessage("user", "x")], [SPEC])
    assert isinstance(result, LLMError) and result.code == "http_status"
    assert result.retries == 3 and "after 3 retries" in result.message
    assert t.slept == [2.0, 4.0, 8.0] and result.wait_s == 14.0


def test_a_wait_above_the_cap_is_not_slept_through() -> None:
    client, t = _client(lambda r: httpx.Response(429, headers={"retry-after": "3600"}, text="tokens per day"))
    result = client.chat([ChatMessage("user", "x")], [SPEC])
    assert isinstance(result, LLMError) and "above the 120 s cap" in result.message and t.slept == []


def test_timeouts_connection_errors_and_bad_bodies_are_values() -> None:
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request):
        raise httpx.ConnectError("refused", request=request)

    assert _client(timeout)[0].chat([ChatMessage("user", "x")], [SPEC]).code == "timeout"
    assert _client(refused)[0].chat([ChatMessage("user", "x")], [SPEC]).code == "connection"
    assert _client(lambda r: httpx.Response(200, json={"choices": []}))[0].chat(
        [ChatMessage("user", "x")], [SPEC]).code == "bad_response"
    assert _client(lambda r: httpx.Response(302, headers={"location": "https://elsewhere.example"}))[0].chat(
        [ChatMessage("user", "x")], [SPEC]).code == "http_status"  # redirects are not followed


def test_pacing_keeps_under_the_token_and_request_limits() -> None:
    client, t = _client(lambda r: _ok(prompt=5000, completion=100), limits=RateLimits(30, 8000))
    assert client.chat([ChatMessage("user", "x")], [SPEC]).wait_s == 0.0
    second = client.chat([ChatMessage("user", "x")], [SPEC])
    assert second.wait_s == pytest.approx(60.0)  # 5,100 + 5,100 > 8,000: wait for the window to clear
    t.now += 1.0
    client._window.clear()  # token window empty: only the 2 s request interval applies
    third = client.chat([ChatMessage("user", "x")], [SPEC])
    assert third.wait_s == pytest.approx(1.0)


def test_key_is_required_and_never_described_or_echoed() -> None:
    with pytest.raises(MissingKey) as missing:
        OpenAICompatibleClient("groq", "m", limits=RateLimits(30, 8000), environ={})
    assert str(missing.value) == "GROQ_API_KEY is not set"
    with pytest.raises(DisallowedEndpoint):
        OpenAICompatibleClient("elsewhere", "m", limits=RateLimits(30, 8000), environ=ENV)
    client, _ = _client(lambda r: httpx.Response(401, text=f"invalid key {KEY}"))
    error = client.chat([ChatMessage("user", "x")], [SPEC])
    assert KEY not in error.message and "[redacted]" in error.message
    assert KEY not in json.dumps(client.describe()) and KEY not in repr(client)
    assert client.describe()["model"] == "qwen/qwen3.8-27b" and client.describe()["date_utc"] == "2026-10-28"
    assert client.describe()["host"] == "api.groq.com" and client.unload() is None


def test_organization_ids_are_stripped_from_provider_errors() -> None:
    body = ('{"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization '
            '`org_0fakeorg0id0for0tests` service tier `on_demand` on tokens per day (TPD)"}}')
    client, _ = _client(lambda r: httpx.Response(429, headers={"retry-after": "445"}, text=body))
    error = client.chat([ChatMessage("user", "x")], [SPEC])
    assert isinstance(error, LLMError) and "org_0fakeorg0id0for0tests" not in error.message
    assert "organization `org_[redacted]`" in error.message and "tokens per day" in error.message


def _scripted_handler(toolset: ToolSet):
    alert = toolset.call("get_alert").items[0].source_id
    deps = [d.source_id for d in toolset.call("get_dependencies").items]
    ranking = {"hypotheses": [{"rank": 1, "service": "orders", "fault_type": "memory_leak", "confidence": "low",
                               "supporting_evidence": [alert, deps[0]], "rationale": "r"}]}
    services = ["api-gateway", "auth", "orders", "payments"]
    script = [("search_logs", {"service": services[i % 4], "limit": 3 + i}) for i in range(1, 5)]
    script += [("finish_gathering", {}), ("submit_hypotheses", ranking), ("search_logs", {"service": "auth", "limit": 2}),
               ("finish_verifying", {}), ("submit_report", {"summary": "s", **ranking})]
    first = [True]

    def handler(request: httpx.Request) -> httpx.Response:
        if first[0]:  # one 429 on the first turn, so the trace must record a retry
            first[0] = False
            return httpx.Response(429, headers={"retry-after": "3"}, text="slow down")
        name, arguments = script.pop(0)
        return _ok([(name, json.dumps(arguments))], prompt=4000, completion=30)

    return handler


def test_full_agent_run_records_model_date_retries_and_never_the_key(toolset: ToolSet, tmp_path: Path) -> None:
    client, _ = _client(_scripted_handler(toolset))
    agent = StateMachineInvestigator(client, traces=TraceWriter(tmp_path))
    sid = toolset.call("get_window").items[0].scenario_id
    report = agent.investigate(CountingToolSet(toolset), sid)
    assert report.stop_reason == "sufficient_evidence"
    text = "".join(p.read_text() for p in tmp_path.glob("*.jsonl"))
    assert KEY not in text
    events = [json.loads(line) for line in text.splitlines()]
    start = events[0]
    assert start["client"]["model"] == "qwen/qwen3.8-27b" and start["client"]["date_utc"] == "2026-10-28"
    models = [e for e in events if e["event"] == "model"]
    assert models[0]["retries"] == 1 and models[0]["wait_s"] == 3.0
    assert all(e["retries"] == 0 for e in models[1:])


def test_client_errors_after_retries_end_the_run_with_an_error_row(toolset: ToolSet) -> None:
    client, _ = _client(lambda r: httpx.Response(429, headers={"retry-after": "9999"}, text="daily"))
    sid = toolset.call("get_window").items[0].scenario_id
    with pytest.raises(InvestigationFailed) as failed:
        StateMachineInvestigator(client).investigate(CountingToolSet(toolset), sid)
    assert failed.value.stop_reason == "error"


def test_cli_refuses_without_the_key_and_prints_no_value(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert agent_run.main(["--backend", "groq", "--smoke", "sc-45fa1390ea", "--quiet"]) == 2
    err = capsys.readouterr().err
    assert "refused: GROQ_API_KEY is not set" in err


def test_cli_names_the_groq_smoke_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run_agent(client, backend, model, data_root, out_dir, ids, *args, **kwargs):
        captured.update(backend=backend, model=model, out_dir=out_dir, ids=ids, client=client.describe())
        raise agent_run.OutputExists("stop here")

    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(agent_run, "run_agent", fake_run_agent)
    assert agent_run.main(["--backend", "groq", "--smoke", "sc-45fa1390ea", "--quiet", "--out-root", str(tmp_path)]) == 2
    assert captured["out_dir"] == tmp_path / "generator-v5" / "smoke-groq-qwen-qwen3.8-27b"
    assert captured["model"] == "qwen/qwen3.8-27b" and captured["ids"] == ("sc-45fa1390ea",)
    assert captured["client"]["extra"] == {"reasoning_effort": "none"}
    assert captured["client"]["rate_limits"] == {"requests_per_minute": 30, "tokens_per_minute": 8000}
