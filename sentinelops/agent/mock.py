"""Scripted, scenario-agnostic policy for ``agent_run --backend mock``. Not a model: it walks the states in a
fixed way so the loop, traces, summary and viewer can be exercised end to end. Its numbers mean nothing.
It reads only what the harness sends (the STAGE block, triage data and ledger), as a model would.
"""

from __future__ import annotations

import json
import re
from typing import Any

from sentinelops.llm.client import ChatMessage, LLMError, LLMResponse, ToolCallRequest, ToolSpec, Usage

_STAGE = re.compile(r"STAGE \(from the harness\): (\w+)")
_SERVICES = ("api-gateway", "auth", "orders", "payments")


def _call(name: str, arguments: dict[str, Any], call_id: str) -> LLMResponse:
    return LLMResponse(text="", tool_calls=(ToolCallRequest(call_id, name, json.dumps(arguments)),), usage=Usage(None, 5))


class DemoAgentPolicy:
    def __init__(self) -> None:
        self.steps: dict[str, int] = {}

    def describe(self) -> dict[str, Any]:
        return {"backend": "mock", "policy": "agent-demo-v1", "note": "scripted; not a model"}

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError:
        stage = _STAGE.search(messages[-1].content)
        state = stage.group(1) if stage else "GATHER"
        triage = {}
        for line in messages[1].content.splitlines()[1:]:
            entry = json.loads(line)
            triage[entry["tool"]] = entry["result"]["items"]
        scenario = (triage.get("get_window") or [{}])[0].get("scenario_id", "?")
        key = f"{scenario}:{state}"
        if not any(m.role == "tool" for m in messages) and state == "GATHER":  # first turn of a run (twins reuse IDs)
            self.steps = {k: v for k, v in self.steps.items() if not k.startswith(f"{scenario}:")}
        step = self.steps.get(key, 0)
        self.steps[key] = step + 1
        alert_service = (triage.get("get_alert") or [{}])[0].get("service", "api-gateway")
        other = next(s for s in _SERVICES if s != alert_service)
        ledger = next((m.content for m in messages if m.content.startswith("DATA evidence ledger")), "")
        ids = []
        for line in ledger.splitlines()[1:]:  # entry, group and series lines of the bounded ledger view
            row = json.loads(line)
            ids += [row["id"]] if "id" in row else [*row.get("ids", []), *(row[k] for k in ("first", "last") if k in row)]
        ids = list(dict.fromkeys(ids))
        cid = f"{state.lower()}-{step}"
        if state == "GATHER":
            plan = [("search_logs", {"service": alert_service, "min_level": "ERROR", "limit": 10}),
                    ("get_metrics", {"service": alert_service, "metric": "error_rate", "limit": 20}),
                    ("list_deployments", {}), ("list_config_changes", {}),
                    ("search_logs", {"min_level": "WARN", "limit": 10})]
            return _call(*plan[step], cid) if step < len(plan) else _call("finish_gathering", {}, cid)
        if state == "HYPOTHESIZE":
            if step == 0:  # shows the wrong_state handling in traces and the viewer
                return _call("search_logs", {"limit": 1}, cid)
            return _call("submit_hypotheses", {"hypotheses": self._ranking(alert_service, other, ids)}, cid)
        if state == "VERIFY":
            if step == 0:
                return _call("search_logs", {"service": other, "limit": 5}, cid)
            return _call("finish_verifying", {}, cid)
        return _call("submit_report", {"summary": f"Mock policy: blames {alert_service} (the alerting service).",
                                       "affected_services": [alert_service],
                                       "hypotheses": self._ranking(alert_service, other, ids),
                                       "uncertainty": "high: scripted mock"}, cid)

    @staticmethod
    def _ranking(first: str, second: str, ids: list[str]) -> list[dict[str, Any]]:
        logs = [i for i in ids if i.startswith("LOG-")]
        alert = [i for i in ids if i.startswith("ALR-")]
        return [{"rank": 1, "service": first, "fault_type": "bad_deployment", "confidence": "low",
                 "supporting_evidence": (alert + logs)[:2], "rationale": "Scripted mock; not an inference."},
                {"rank": 2, "service": second, "fault_type": "config_error", "confidence": "low",
                 "supporting_evidence": logs[1:2], "rationale": "Scripted mock; not an inference."}]
