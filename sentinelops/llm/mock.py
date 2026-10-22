"""Offline clients: no model, no network.

``ScriptedClient`` replays a fixed list of responses or errors and records every
request, for tests. ``DemoPolicyClient`` is a scenario-agnostic script used by
``pilot --backend mock`` to exercise the loop, traces and viewer end to end. It
always blames the alerting service, so its numbers mean nothing about any model.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from sentinelops.llm.client import ChatMessage, LLMError, LLMResponse, ToolCallRequest, ToolSpec, Usage


class ScriptedClient:
    def __init__(self, script: Sequence[LLMResponse | LLMError]) -> None:
        self.script = list(script)
        self.requests: list[tuple[list[ChatMessage], list[ToolSpec]]] = []

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError:
        self.requests.append((list(messages), list(tools)))
        if not self.script:
            return LLMError("bad_response", "script exhausted")
        return self.script.pop(0)

    def describe(self) -> dict[str, Any]:
        return {"backend": "scripted"}


def call(name: str, arguments: Any = None, call_id: str = "c1", raw: str | None = None) -> LLMResponse:
    """A response with one tool call; ``raw`` overrides the JSON text (to script malformed calls)."""
    text = raw if raw is not None else json.dumps(arguments or {})
    return LLMResponse(text="", tool_calls=(ToolCallRequest(call_id, name, text),), usage=Usage(10, 5))


def text(content: str) -> LLMResponse:
    return LLMResponse(text=content, usage=Usage(10, 5))


_ALERT = re.compile(r'"service":\s*"([a-z-]+)".*?"source_id":\s*"(ALR-\d{3})"', re.S)
_LOG = re.compile(r"LOG-\d{5}")


class DemoPolicyClient:
    """Fixed sequence: window, error logs, an invalid metrics call (shows error handling), deployments,
    then a report blaming the alert's service as a bad deployment, citing the alert and one log."""

    def describe(self) -> dict[str, Any]:
        return {"backend": "mock", "policy": "demo-v1", "note": "scripted; not a model"}

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError:
        step = sum(1 for m in messages if m.role == "assistant")
        first_user = next(m.content for m in messages if m.role == "user")
        match = _ALERT.search(first_user)
        service, alert_id = (match.group(1), match.group(2)) if match else ("api-gateway", "ALR-001")
        if step == 0:
            return call("get_window", {}, "d0")
        if step == 1:
            return call("search_logs", {"service": service, "min_level": "ERROR", "limit": 20}, "d1")
        if step == 2:
            return call("get_metrics", {"service": service}, "d2")  # missing "metric": invalid on purpose
        if step == 3:
            return call("list_deployments", {"service": service}, "d3")
        logs = [m for m in messages if m.role == "tool" and m.tool_name == "search_logs"]
        found = _LOG.findall(logs[-1].content) if logs else []
        evidence = [alert_id, *found[:1]]
        report = {"summary": f"Mock policy: blames {service} (the alerting service).",
                  "affected_services": [service],
                  "hypotheses": [{"rank": 1, "service": service, "fault_type": "bad_deployment",
                                  "confidence": "low", "supporting_evidence": evidence,
                                  "rationale": "Scripted mock; not an inference."}],
                  "missing_evidence": [], "uncertainty": "high: scripted mock", "next_checks": [],
                  "recommended_remediation": []}
        return call("submit_report", report, "d4")
