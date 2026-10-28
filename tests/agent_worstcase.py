"""Synthetic worst case for M4 context management (no scenario data, no model).

Every read call returns a maximum-size result with all-new IDs: 120 metric points for ``get_metrics``,
200 long log lines (well past the 4,000-character cap) for everything else. A scripted client uses
all 40 read-tool calls: TRIAGE 3, GATHER 16, VERIFY 7, return to GATHER, 14 more, then reports.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sentinelops.llm.client import ChatMessage, LLMResponse, ToolCallRequest, ToolSpec, Usage
from sentinelops.models import Alert, AlertSeverity, Dependency, LogLevel, LogRecord, Metric, MetricPoint, Service
from sentinelops.tools import ScenarioWindow, ToolResult

SCENARIO_ID = "sc-00000000ff"
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
SERIES = [(s, m) for s in (Service.ORDERS, Service.AUTH, Service.PAYMENTS) for m in Metric] + \
         [(Service.GATEWAY, m) for m in Metric if m is not Metric.DB_POOL_UTILIZATION]


class WorstCaseTools:
    def __init__(self) -> None:
        self.log_id = self.metric_id = 0
        self.metric_calls = 0
        self.calls: list[str] = []

    def call(self, name: str, arguments: Any = None) -> ToolResult:
        self.calls.append(name)
        if name == "get_alert":
            alert = Alert(source_id="ALR-001", timestamp=T0 + timedelta(minutes=60), service=Service.GATEWAY,
                          metric=Metric.ERROR_RATE, severity=AlertSeverity.CRITICAL, observed_value=0.2, threshold=0.05,
                          summary="Error rate on api-gateway is 20.00% (5-minute average), above the 5.00% threshold.")
            return ToolResult(tool=name, items=(alert,), total_matches=1)
        if name == "get_window":
            return ToolResult(tool=name, items=(ScenarioWindow(scenario_id=SCENARIO_ID, window_start=T0,
                                                               window_end=T0 + timedelta(minutes=120)),), total_matches=1)
        if name == "get_dependencies":
            edges = [(Service.GATEWAY, Service.AUTH), (Service.GATEWAY, Service.ORDERS), (Service.ORDERS, Service.AUTH),
                     (Service.ORDERS, Service.PAYMENTS)]
            return ToolResult(tool=name, items=tuple(Dependency(source_id=f"DEP-{i:03d}", caller=a, callee=b)
                                                     for i, (a, b) in enumerate(edges, 1)), total_matches=4)
        if name == "get_metrics":
            service, metric = SERIES[self.metric_calls % len(SERIES)]
            self.metric_calls += 1
            points = []
            for minute in range(120):
                self.metric_id += 1
                points.append(MetricPoint(source_id=f"MET-{self.metric_id:05d}", timestamp=T0 + timedelta(minutes=minute),
                                          service=service, metric=metric, value=float(minute % 17)))
            return ToolResult(tool=name, items=tuple(points), total_matches=120)
        logs = []
        for i in range(200):
            self.log_id += 1
            logs.append(LogRecord(source_id=f"LOG-{self.log_id:05d}", timestamp=T0 + timedelta(seconds=self.log_id),
                                  service=list(Service)[self.log_id % 4], level=LogLevel.ERROR,
                                  message=f"request req-{self.log_id:08x} failed: upstream connection reset after "
                                          f"3000 ms while calling dependency (attempt {i % 3}); payload id {i:06d}"))
        return ToolResult(tool=name, items=tuple(logs), total_matches=500, truncated=True)


def _call(name: str, arguments: dict[str, Any], n: int) -> LLMResponse:
    return LLMResponse(text="", tool_calls=(ToolCallRequest(f"w{n}", name, json.dumps(arguments)),), usage=Usage(None, 5))


class WorstCaseClient:
    """Uses the whole budget; reads IDs only from what the harness rendered."""

    def __init__(self) -> None:
        self.n = 0
        self.gather_reads = 0
        self.verify_reads = 0
        self.returned = False
        self.requests: list[list[ChatMessage]] = []
        self.tools: list[list[ToolSpec]] = []  # the tools each request actually carried (context revision 3)

    def describe(self) -> dict[str, Any]:
        return {"backend": "worst-case"}

    def _ids(self, messages: list[ChatMessage]) -> list[str]:
        ledger = next((m.content for m in messages if m.content.startswith("DATA evidence ledger")), "")
        ids = []
        for line in ledger.splitlines()[1:]:
            row = json.loads(line)
            ids += [row["id"]] if "id" in row else [*row.get("ids", []), *(row[k] for k in ("first", "last") if k in row)]
        return list(dict.fromkeys(ids))

    def _ranking(self, ids: list[str]) -> list[dict[str, Any]]:
        logs = [i for i in ids if i.startswith("LOG-")]
        mets = [i for i in ids if i.startswith("MET-")]
        return [{"rank": 1, "service": "orders", "fault_type": "connection_pool_exhaustion", "confidence": "medium",
                 "supporting_evidence": (logs[:3] + mets[:3]), "rationale": "worst case"},
                {"rank": 2, "service": "auth", "fault_type": "config_error", "confidence": "low",
                 "supporting_evidence": logs[3:5], "rationale": "worst case"}]

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse:
        self.requests.append(list(messages))
        self.tools.append(list(tools))
        self.n += 1
        state = messages[-1].content.split("\n", 1)[0].removeprefix("STAGE (from the harness): ")
        read = ("get_metrics", {"service": "orders", "metric": "error_rate", "limit": 120 + self.n % 3}) \
            if self.n % 2 else ("search_logs", {"min_level": "ERROR", "limit": 190 + self.n % 7})
        if state == "GATHER":
            first_pass_done = self.gather_reads >= 16 and not self.returned
            if first_pass_done or (self.returned and self.gather_reads >= 30):
                return _call("finish_gathering", {}, self.n)
            self.gather_reads += 1
            return _call(*read, self.n)
        if state == "HYPOTHESIZE":
            return _call("submit_hypotheses", {"hypotheses": self._ranking(self._ids(messages))}, self.n)
        if state == "VERIFY":
            if not self.returned and self.verify_reads < 7:
                self.verify_reads += 1
                return _call(*read, self.n)
            if not self.returned:
                self.returned = True
                return _call("return_to_gather", {}, self.n)
            return _call("finish_verifying", {}, self.n)
        return _call("submit_report", {"summary": "worst case", "hypotheses": self._ranking(self._ids(messages))}, self.n)
