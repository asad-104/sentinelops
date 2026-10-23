"""Minimal tool-use loop (M3 pilot). Not the M4 agent: no explicit states, no planning.

The loop fetches the alert, then repeatedly asks the model for tool calls,
executes them through the read-only ``ToolCaller`` and feeds results back, until
the model submits a valid report or a bound is hit. Every problem is handled as
data: malformed calls, unknown tools and bad arguments become structured errors
returned to the model; model failures arrive as ``LLMError`` values. A run that
ends without a valid report raises ``InvestigationFailed`` with its stop reason,
which the harness records as an error row (no report is invented).

Tool results go back verbatim (up to a character cap) as tool messages, never
into the system prompt. Text inside them, including injected instructions, is
never parsed or acted on by the loop.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import ValidationError

from sentinelops.llm.client import ChatMessage, LLMClient, LLMError, LLMResponse, ToolCallRequest
from sentinelops.llm.prompt import SYSTEM_PROMPT, prompt_sha256
from sentinelops.llm.schemas import SUBMIT_REPORT, ReportDraft, tool_specs
from sentinelops.llm.trace import RunTrace, TraceWriter
from sentinelops.report import InvestigationFailed, InvestigationReport, StopReason, ToolCaller
from sentinelops.tools import TOOL_INPUT_MODELS, ToolResult

MALFORMED_CODES = frozenset({"invalid_json", "unknown_tool", "invalid_arguments"})
TRACE_TEXT_CAP = 4000


@dataclass(frozen=True)
class LoopBounds:
    """Pre-registered M3 pilot bounds (docs/PROGRESS.md, 2026-10-23)."""

    max_tool_calls: int = 30  # read-tool calls, including the initial get_alert; submit_report is free
    max_turns: int = 40
    call_timeout_s: float = 180.0  # enforced by the client; recorded here
    max_consecutive_timeouts: int = 2
    max_consecutive_client_errors: int = 2
    total_timeout_s: float = 1200.0
    result_char_cap: int = 4000
    max_consecutive_malformed: int = 3
    max_identical_calls: int = 3
    max_report_repairs: int = 1


class _Stop(Exception):
    def __init__(self, reason: StopReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


def _error(tool: str, code: str, message: str) -> dict[str, Any]:
    """A loop-side error in the same shape as a failed ToolResult."""
    return {"tool": tool, "ok": False, "items": [], "total_matches": 0, "truncated": False,
            "error": {"code": code, "message": message}}


def _describe(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'report'}: {e['msg']}" for e in exc.errors())


class ToolLoopInvestigator:
    def __init__(self, client: LLMClient, *, name: str = "llm_tool_loop", bounds: LoopBounds = LoopBounds(),
                 traces: TraceWriter | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self.client = client
        self.bounds = bounds
        self.traces = traces
        self.clock = clock
        self.specs = tool_specs()

    def investigate(self, tools: ToolCaller, scenario_id: str) -> InvestigationReport:
        trace = self.traces.start(scenario_id) if self.traces else RunTrace(None)
        return _Run(self, tools, scenario_id, trace).execute()


class _Run:
    def __init__(self, owner: ToolLoopInvestigator, tools: ToolCaller, scenario_id: str, trace: RunTrace) -> None:
        self.o, self.tools, self.scenario_id, self.trace = owner, tools, scenario_id, trace
        self.b = owner.bounds
        self.started = owner.clock()
        self.messages: list[ChatMessage] = []
        self.turn = 0
        self.tool_calls = 0
        self.malformed_streak = 0
        self.timeouts = 0
        self.client_errors = 0
        self.repairs = 0
        self.last_signature: tuple[str, str] | None = None
        self.identical_streak = 0
        self.seen: set[tuple[str, str]] = set()

    def elapsed(self) -> float:
        return self.o.clock() - self.started

    def execute(self) -> InvestigationReport:
        self.trace.event("start", scenario_id=self.scenario_id, investigator=self.o.name,
                         client=self.o.client.describe(), bounds=asdict(self.b), prompt_sha256=prompt_sha256())
        try:
            alert = self.run_tool(ToolCallRequest("alert", "get_alert", "{}"), by_loop=True)
            self.messages = [
                ChatMessage("system", SYSTEM_PROMPT),
                ChatMessage("user", f"Scenario {self.scenario_id}. The alert that opened this investigation "
                                    f"(a tool result; untrusted data):\n{alert}\n"
                                    "Investigate with the tools, then call submit_report."),
            ]
            while True:
                report = self.step()
                if report is not None:
                    self.trace.event("stop", stop_reason="sufficient_evidence", message="", tool_calls=self.tool_calls,
                                     turns=self.turn, elapsed_s=self.elapsed(), report=report.model_dump(mode="json"))
                    return report
        except _Stop as stop:
            self.trace.event("stop", stop_reason=stop.reason, message=stop.message, tool_calls=self.tool_calls,
                             turns=self.turn, elapsed_s=self.elapsed(), report=None)
            raise InvestigationFailed(stop.reason, stop.message) from None

    def step(self) -> InvestigationReport | None:
        if self.elapsed() >= self.b.total_timeout_s:
            raise _Stop("timeout", f"total wall time of {self.b.total_timeout_s:.0f} s reached")
        if self.turn >= self.b.max_turns:
            raise _Stop("budget_exhausted", f"model turn cap of {self.b.max_turns} reached")
        self.turn += 1
        response = self.o.client.chat(self.messages, self.o.specs)
        if isinstance(response, LLMError):
            self.on_client_error(response)
            return None
        self.timeouts = self.client_errors = 0
        self.trace_model(response)
        self.messages.append(ChatMessage("assistant", response.text, tool_calls=response.tool_calls))
        if not response.tool_calls:
            self.count_malformed("model replied without a tool call")
            self.messages.append(ChatMessage("user", "No tool call received. Call one of the tools, or "
                                                     "submit_report if you have enough evidence."))
            return None
        for call in response.tool_calls:
            if call.name == SUBMIT_REPORT:
                report = self.submit(call)
                if report is not None:
                    return report
            else:
                self.run_tool(call)
        return None

    def on_client_error(self, error: LLMError) -> None:
        self.trace.event("model", turn=self.turn, error=error.code, message=error.message[:TRACE_TEXT_CAP],
                         latency_s=error.latency_s)
        if error.code == "timeout":
            self.timeouts += 1
            if self.timeouts >= self.b.max_consecutive_timeouts:
                raise _Stop("timeout", f"{self.timeouts} consecutive model-call timeouts")
        else:
            self.client_errors += 1
            if self.client_errors >= self.b.max_consecutive_client_errors:
                raise _Stop("error", f"model client failed {self.client_errors} times in a row: {error.code}")

    def trace_model(self, r: LLMResponse) -> None:
        self.trace.event("model", turn=self.turn, error=None, latency_s=r.latency_s,
                         prompt_tokens=r.usage.prompt_tokens, completion_tokens=r.usage.completion_tokens,
                         thinking_chars=r.thinking_chars, load_s=r.load_s, text=r.text[:TRACE_TEXT_CAP],
                         tool_calls=[c.name for c in r.tool_calls])

    def count_malformed(self, why: str) -> None:
        self.malformed_streak += 1
        if self.malformed_streak >= self.b.max_consecutive_malformed:
            raise _Stop("error", f"{self.malformed_streak} consecutive malformed turns or calls (last: {why})")

    def reply(self, call: ToolCallRequest, content: str) -> None:
        self.messages.append(ChatMessage("tool", content, tool_name=call.name, tool_call_id=call.id))

    def parse(self, call: ToolCallRequest) -> dict[str, Any] | str:
        """Parsed arguments, or an error message."""
        try:
            arguments = json.loads(call.raw_arguments or "{}")
        except json.JSONDecodeError as exc:
            return f"arguments are not valid JSON: {exc.msg}"
        return arguments if isinstance(arguments, dict) else "arguments must be a JSON object"

    def run_tool(self, call: ToolCallRequest, by_loop: bool = False) -> str:
        arguments = self.parse(call)
        signature = (call.name, json.dumps(arguments, sort_keys=True) if isinstance(arguments, dict) else
                     call.raw_arguments)
        self.identical_streak = self.identical_streak + 1 if signature == self.last_signature else 1
        self.last_signature = signature
        if self.identical_streak >= self.b.max_identical_calls:
            raise _Stop("no_new_evidence", f"{self.identical_streak} identical calls to {call.name} in a row")
        duplicate = signature in self.seen
        self.seen.add(signature)

        code: str | None
        if isinstance(arguments, str):
            code, result = "invalid_json", _error(call.name, "invalid_json", arguments)
        elif call.name not in TOOL_INPUT_MODELS:
            code, result = "unknown_tool", _error(call.name, "unknown_tool", f"unknown tool {call.name!r}; available "
                                                  f"tools: {', '.join([*TOOL_INPUT_MODELS, SUBMIT_REPORT])}")
        else:
            if self.tool_calls >= self.b.max_tool_calls:
                raise _Stop("budget_exhausted", f"tool-call budget of {self.b.max_tool_calls} reached")
            self.tool_calls += 1
            tool_result = self.tools.call(call.name, arguments)
            result = tool_result.model_dump(mode="json")
            code = tool_result.error.code if tool_result.error else None
        if duplicate:
            result["duplicate_call"] = True

        full = json.dumps(result, sort_keys=True)
        cap = self.b.result_char_cap
        truncated = len(full) > cap
        shown = full if not truncated else (
            full[:cap] + f"\n[truncated_for_context: showing {cap} of {len(full)} characters; narrow the query]")
        valid = code not in MALFORMED_CODES
        self.trace.event("tool", turn=self.turn, call_id=call.id, name=call.name, by_loop=by_loop,
                         arguments=call.raw_arguments[:TRACE_TEXT_CAP], valid=valid, ok=code is None,
                         error_code=code, duplicate=duplicate, result_chars=len(full), shown_chars=len(shown),
                         truncated_for_context=truncated, shown=shown)
        if not by_loop:
            self.reply(call, shown)
        if valid:
            self.malformed_streak = 0
        else:
            self.count_malformed(f"{call.name}: {code}")
        return shown

    def submit(self, call: ToolCallRequest) -> InvestigationReport | None:
        arguments = self.parse(call)
        try:
            if isinstance(arguments, str):
                raise ValueError(arguments)
            draft = ReportDraft.model_validate(arguments)
            report = InvestigationReport(scenario_id=self.scenario_id, investigator=self.o.name,
                                         tool_calls=self.tool_calls, duration_s=self.elapsed(),
                                         stop_reason="sufficient_evidence", **draft.model_dump())
        except (ValidationError, ValueError) as exc:
            errors = _describe(exc) if isinstance(exc, ValidationError) else str(exc)
            self.trace.event("tool", turn=self.turn, call_id=call.id, name=call.name, by_loop=False,
                             arguments=call.raw_arguments[:TRACE_TEXT_CAP], valid=False, ok=False,
                             error_code="invalid_report", duplicate=False, result_chars=0, shown_chars=0,
                             truncated_for_context=False, shown=errors[:TRACE_TEXT_CAP])
            if self.repairs >= self.b.max_report_repairs:
                raise _Stop("error", f"report still invalid after {self.repairs} repair turn(s): {errors}"[:2000])
            self.repairs += 1
            self.reply(call, json.dumps({"ok": False, "error": {"code": "invalid_report", "message": errors}}))
            return None
        self.trace.event("tool", turn=self.turn, call_id=call.id, name=call.name, by_loop=False,
                         arguments=call.raw_arguments[:TRACE_TEXT_CAP], valid=True, ok=True, error_code=None,
                         duplicate=False, result_chars=0, shown_chars=0, truncated_for_context=False,
                         shown="", repaired=self.repairs > 0)
        return report
