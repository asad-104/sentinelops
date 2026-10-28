"""The M4 investigator: an explicit state machine over the read-only tools, with managed context.

The loop owns every transition and bound (pre-registered in docs/PROGRESS.md, 2026-10-23). The model
chooses tool calls within a state; a tool the state does not allow returns ``wrong_state``. Problems
are data, as in M3: malformed calls, failed preconditions and invalid submissions become structured
errors shown to the model; model failures arrive as ``LLMError`` values. A run that ends without a
valid report raises ``InvestigationFailed`` with its stop reason, and the harness records an error row.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from pydantic import BaseModel, ValidationError

from sentinelops.agent.context import (
    ContextBuilder,
    ContextExhausted,
    Exchange,
    Ledger,
    id_kind,
)
from sentinelops.agent.prompt import (
    DATA_HEADERS,
    HARNESS_MESSAGES,
    HARNESS_NOTES,
    STATE_INSTRUCTIONS,
    SYSTEM_PROMPT,
    prompt_sha256,
)
from sentinelops.agent.schemas import STATE_TOOL_MODELS, HypothesesDraft, agent_tool_specs, state_tool_specs
from sentinelops.agent.states import (
    ALLOWED,
    FINISH_GATHERING,
    FINISH_VERIFYING,
    READ_TOOLS,
    RETURN_TO_GATHER,
    SUBMIT_HYPOTHESES,
    SUBMIT_REPORT,
    TRANSITIONS,
    TRIAGE_CALLS,
    AgentBounds,
    State,
)
from sentinelops.llm.client import LLMClient, LLMError, LLMResponse, ToolCallRequest
from sentinelops.llm.schemas import ReportDraft
from sentinelops.llm.trace import RunTrace, TraceWriter
from sentinelops.report import InvestigationFailed, InvestigationReport, StopReason, ToolCaller

MALFORMED_CODES = frozenset({"invalid_json", "unknown_tool", "invalid_arguments", "wrong_state", "precondition",
                             "invalid_hypotheses", "invalid_report", "truncated_output", "no_tool_call"})
CALL_KINDS = {"search_logs": "logs", "get_metrics": "metrics", "list_deployments": "changes",
              "list_config_changes": "changes", "get_timeline": "changes", "get_dependencies": "dependencies",
              "get_alert": "alert", "get_window": "window"}
TRACE_TEXT_CAP = 4000


class _Stop(Exception):
    def __init__(self, reason: StopReason, message: str) -> None:
        super().__init__(message)
        self.reason, self.message = reason, message


def _describe(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in exc.errors())


def _error(tool: str, code: str, message: str) -> dict[str, Any]:
    return {"tool": tool, "ok": False, "items": [], "total_matches": 0, "truncated": False,
            "error": {"code": code, "message": message}}


def call_kind(name: str, arguments: dict[str, Any]) -> str | None:
    """The data kind a read call asks for (``get_record``: the kind of the requested ID)."""
    if name == "get_record":
        sid = arguments.get("source_id")
        return id_kind(sid) if isinstance(sid, str) else None
    return CALL_KINDS.get(name)


class StateMachineInvestigator:
    def __init__(self, client: LLMClient, *, name: str = "m4_agent", bounds: AgentBounds = AgentBounds(),
                 traces: TraceWriter | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.name, self.client, self.bounds, self.traces, self.clock = name, client, bounds, traces, clock
        self.specs = agent_tool_specs()

    def investigate(self, tools: ToolCaller, scenario_id: str) -> InvestigationReport:
        trace = self.traces.start(scenario_id) if self.traces else RunTrace(None)
        return _Run(self, tools, scenario_id, trace).execute()


class _Run:
    def __init__(self, owner: StateMachineInvestigator, tools: ToolCaller, scenario_id: str, trace: RunTrace) -> None:
        self.o, self.tools, self.scenario_id, self.trace, self.b = owner, tools, scenario_id, trace, owner.bounds
        self.builder = ContextBuilder(self.b, owner.specs)
        self.started = owner.clock()
        self.state = State.TRIAGE
        self.ledger = Ledger()
        self.exchanges: list[Exchange] = []
        self.triage_text = ""
        self.notes: list[str] = []
        self.ranking: list[dict[str, Any]] = []
        self.tool_calls = self.turns = 0
        self.gather_evidence_first_pass = self.gather_calls_first_pass = 0
        self.gather_evidence_second_pass = 0  # shown in the STAGE block only; no precondition on the second pass
        self.verify_calls = self.returns = 0
        self.malformed = self.timeouts = self.client_errors = self.repairs = 0
        self.identical = self.no_new = 0
        self.last_signature: tuple[str, str] | None = None
        self.seen: set[tuple[str, str]] = set()
        self.rendered_ids: frozenset[str] = frozenset()

    # Bookkeeping

    def elapsed(self) -> float:
        return self.o.clock() - self.started

    def move(self, target: State, reason: str) -> None:
        if (self.state, target) not in TRANSITIONS:
            raise AssertionError(f"illegal transition {self.state} -> {target}")  # a loop bug, never model input
        self.trace.event("state_exit", state=self.state.value, turn=self.turns, reason=reason)
        if self.state is State.VERIFY and target is State.GATHER:
            self.returns += 1
        self.state = target
        self.trace.event("state_enter", state=target.value, turn=self.turns, reason=reason)

    def stop(self, reason: StopReason, message: str) -> _Stop:
        return _Stop(reason, message)

    # Main loop

    def execute(self) -> InvestigationReport:
        self.trace.event("start", scenario_id=self.scenario_id, investigator=self.o.name,
                         client=self.o.client.describe(), bounds=asdict(self.b), prompt_sha256=prompt_sha256())
        self.trace.event("state_enter", state=State.TRIAGE.value, turn=0, reason="start")
        try:
            self.triage()
            while True:
                report = self.step()
                if report is not None:
                    self.trace.event("stop", stop_reason="sufficient_evidence", message="", tool_calls=self.tool_calls,
                                     turns=self.turns, elapsed_s=self.elapsed(), state=self.state.value,
                                     report=report.model_dump(mode="json"))
                    return report
        except _Stop as stop:
            self.trace.event("stop", stop_reason=stop.reason, message=stop.message, tool_calls=self.tool_calls,
                             turns=self.turns, elapsed_s=self.elapsed(), state=self.state.value, report=None)
            raise InvestigationFailed(stop.reason, stop.message) from None

    def triage(self) -> None:
        """Loop-issued (decision D8): the alert, the window and the dependency graph, as data."""
        parts = [DATA_HEADERS["triage"]]
        for name in TRIAGE_CALLS:
            result = self.tools.call(name, {})
            self.tool_calls += 1
            dump = result.model_dump(mode="json")
            new = self.ledger.add(dump["items"])
            self.seen.add((name, "{}"))
            parts.append(json.dumps({"tool": name, "result": dump}, sort_keys=True))
            self.trace.event("tool", turn=0, state=State.TRIAGE.value, call_id=f"triage-{name}", name=name,
                             by_loop=True, arguments="{}", valid=True, ok=result.ok,
                             error_code=result.error.code if result.error else None, duplicate=False,
                             new_ids=new, records=self._records(dump["items"]), data_kind=CALL_KINDS.get(name),
                             evidence=False, result_chars=len(json.dumps(dump)), shown="", compacted="")
        self.triage_text = "\n".join(parts)
        self.move(State.GATHER, "triage done")

    def step(self) -> InvestigationReport | None:
        if self.elapsed() >= self.b.total_timeout_s:
            raise self.stop("timeout", f"total wall time of {self.b.total_timeout_s:.0f} s reached")
        if self.turns >= self.b.max_turns:
            raise self.stop("budget_exhausted", f"model turn cap of {self.b.max_turns} reached")
        progress = {"evidence": self.gather_evidence_first_pass if self.returns == 0 else self.gather_evidence_second_pass,
                    "verify": self.verify_calls}
        stage = self.builder.stage_block(self.state, STATE_INSTRUCTIONS[self.state], self.tool_calls, self.notes,
                                         progress)
        try:
            request = self.builder.build(SYSTEM_PROMPT, self.triage_text, self.ledger, self.exchanges, stage,
                                         self.cited_in_ranking(), state_tool_specs(self.state, self.o.specs))
        except ContextExhausted as exc:
            raise self.stop("context_exhausted", str(exc)) from None
        self.notes = []
        self.turns += 1
        self.rendered_ids = request.rendered_ids
        self.trace.event("context", turn=self.turns, state=self.state.value, chars=request.chars,
                         estimated_tokens=request.estimated_tokens, budget=self.b.prompt_budget, level=request.level,
                         min_level=self.builder.min_level, ledger_size=len(self.ledger),
                         rendered_ids=len(request.rendered_ids), exchanges=len(self.exchanges),
                         messages=len(request.messages), components=request.components)
        response = self.o.client.chat(request.messages, request.specs)
        if isinstance(response, LLMError):
            self.on_client_error(response)
            return None
        self.timeouts = self.client_errors = 0
        guard = self.builder.on_reported(request.chars, response.usage.prompt_tokens)
        self.trace_model(response, guard)
        if response.truncated:
            self.count_malformed("truncated_output")
            self.notes.append(HARNESS_NOTES["truncated_output"])
            return None
        if not response.tool_calls:
            self.count_malformed("no_tool_call")
            self.notes.append(HARNESS_NOTES["no_tool_call"])
            return None
        for call in response.tool_calls:
            report = self.handle(call)
            if report is not None:
                return report
        return None

    def on_client_error(self, error: LLMError) -> None:
        self.trace.event("model", turn=self.turns, state=self.state.value, error=error.code,
                         message=error.message[:TRACE_TEXT_CAP], latency_s=error.latency_s, retries=error.retries,
                         wait_s=error.wait_s)
        if error.code == "timeout":
            self.timeouts += 1
            unload = getattr(self.o.client, "unload", None)
            if unload is not None:  # kill any generation still running before retrying (decision D3)
                failure = unload()
                self.trace.event("unload", turn=self.turns, reason="after timeout",
                                 error=None if failure is None else f"{failure.code}: {failure.message}")
            if self.timeouts >= self.b.max_consecutive_timeouts:
                raise self.stop("timeout", f"{self.timeouts} consecutive model-call timeouts")
        else:
            self.client_errors += 1
            if self.client_errors >= self.b.max_consecutive_client_errors:
                raise self.stop("error", f"model client failed {self.client_errors} times in a row: {error.code}")

    def trace_model(self, r: LLMResponse, guard: bool) -> None:
        self.trace.event("model", turn=self.turns, state=self.state.value, error=None, latency_s=r.latency_s,
                         prompt_tokens=r.usage.prompt_tokens, completion_tokens=r.usage.completion_tokens,
                         prompt_eval_s=r.prompt_eval_s, load_s=r.load_s, total_s=r.total_s, truncated=r.truncated,
                         thinking_chars=r.thinking_chars, guard_fired=guard, text=r.text[:TRACE_TEXT_CAP],
                         tool_calls=[c.name for c in r.tool_calls], retries=r.retries, wait_s=r.wait_s)

    def count_malformed(self, why: str) -> None:
        self.malformed += 1
        if self.malformed >= self.b.max_consecutive_malformed:
            raise self.stop("error", f"{self.malformed} consecutive malformed turns or calls (last: {why})")

    # Tool calls

    def parse(self, call: ToolCallRequest) -> dict[str, Any] | str:
        try:
            arguments = json.loads(call.raw_arguments or "{}")
        except json.JSONDecodeError as exc:
            return HARNESS_MESSAGES["invalid_json"].format(detail=exc.msg)
        return arguments if isinstance(arguments, dict) else HARNESS_MESSAGES["not_an_object"]

    def handle(self, call: ToolCallRequest) -> InvestigationReport | None:
        arguments = self.parse(call)
        if isinstance(arguments, str):
            return self.reject(call, "invalid_json", arguments)
        if call.name not in READ_TOOLS and call.name not in STATE_TOOL_MODELS:
            return self.reject(call, "unknown_tool", HARNESS_MESSAGES["unknown_tool"].format(name=call.name))
        if call.name not in ALLOWED[self.state]:
            allowed = ", ".join(sorted(ALLOWED[self.state]))
            return self.reject(call, "wrong_state", HARNESS_MESSAGES["wrong_state"].format(name=call.name, state=self.state.value,
                                                                                         allowed=allowed))
        if call.name in READ_TOOLS:
            self.read(call, arguments)
            return None
        return self.state_tool(call, arguments)

    def reject(self, call: ToolCallRequest, code: str, message: str, *, counts: bool = True) -> None:
        result = _error(call.name, code, message)
        self.record(call, result, valid=False, code=code, new=[], records=[], kind=None, evidence=False,
                    duplicate=False)
        if counts:
            self.count_malformed(f"{call.name}: {code}")
        return None

    def read(self, call: ToolCallRequest, arguments: dict[str, Any]) -> None:
        signature = (call.name, json.dumps(arguments, sort_keys=True))
        self.identical = self.identical + 1 if signature == self.last_signature else 1
        self.last_signature = signature
        if self.identical >= self.b.max_identical_calls:
            # Change B amendment (2026-10-28): in GATHER, once finish_gathering would be accepted, advance instead;
            # the identical call is not run either way
            if self.state is not State.GATHER or not self.may_finish_gathering():
                raise self.stop("no_new_evidence", f"{self.identical} identical calls to {call.name} in a row")
            self.notes.append(HARNESS_NOTES["identical_calls"].format(count=self.identical))
            self.identical = self.no_new = 0
            self.last_signature = None
            self.move(State.HYPOTHESIZE, "identical calls")
            return
        if self.tool_calls >= self.b.max_tool_calls:
            raise self.stop("budget_exhausted", f"tool-call budget of {self.b.max_tool_calls} reached")
        duplicate = signature in self.seen
        self.seen.add(signature)
        self.tool_calls += 1
        result = self.tools.call(call.name, arguments)
        dump = result.model_dump(mode="json")
        code = result.error.code if result.error else None
        valid = code not in ("unknown_tool", "invalid_arguments")
        if duplicate:
            dump["duplicate_call"] = True
        shown = self.cap(json.dumps(dump, sort_keys=True))
        new = self.ledger.add(dump["items"], shown) if result.ok else []  # only IDs the model was shown
        evidence = result.ok and bool(new)
        self.record(call, dump, valid=valid, code=code, new=new, records=self._records(dump["items"]),
                    kind=call_kind(call.name, arguments), evidence=evidence, duplicate=duplicate)
        if valid:
            self.malformed = 0
        else:
            self.count_malformed(f"{call.name}: {code}")
        if self.state is State.GATHER:
            if valid:  # invalid calls are counted by the malformed streak instead
                self.no_new = 0 if new else self.no_new + 1
            if self.returns > 0:
                self.gather_evidence_second_pass += int(evidence)
            else:
                self.gather_calls_first_pass += 1
                self.gather_evidence_first_pass += int(evidence)
            if self.no_new >= self.b.max_no_new_evidence:
                # Change B (2026-10-28): once finish_gathering would be accepted, advance like the cap does
                if not self.may_finish_gathering():
                    raise self.stop("no_new_evidence", f"{self.no_new} GATHER calls in a row returned no new source ID")
                self.notes.append(HARNESS_NOTES["no_new_evidence"].format(count=self.no_new))
                self.no_new = 0
                self.move(State.HYPOTHESIZE, "no new evidence")
            elif self.returns == 0 and self.gather_calls_first_pass >= self.b.gather_first_pass_cap:
                self.notes.append(HARNESS_NOTES["gather_cap"].format(cap=self.b.gather_first_pass_cap))
                self.move(State.HYPOTHESIZE, "gather cap")
        elif self.state is State.VERIFY:
            self.verify_calls += 1
            if self.verify_calls >= self.b.verify_cap:
                self.notes.append(HARNESS_NOTES["verify_cap"].format(cap=self.b.verify_cap))
                self.move(State.REPORT, "verify cap")

    def state_tool(self, call: ToolCallRequest, arguments: dict[str, Any]) -> InvestigationReport | None:
        model: type[BaseModel] = STATE_TOOL_MODELS[call.name]
        if call.name == SUBMIT_REPORT:
            return self.submit_report(call, arguments)
        try:
            draft = model.model_validate(arguments)
        except ValidationError as exc:
            return self.reject(call, "invalid_arguments", _describe(exc))
        if call.name == FINISH_GATHERING:
            if not self.may_finish_gathering():
                return self.reject(call, "precondition", HARNESS_MESSAGES["need_gather_evidence"].format(
                    needed=self.b.min_gather_evidence, have=self.gather_evidence_first_pass))
            self.accept(call, HARNESS_MESSAGES["accepted_finish_gathering"])
            self.move(State.HYPOTHESIZE, FINISH_GATHERING)
        elif call.name == SUBMIT_HYPOTHESES:
            assert isinstance(draft, HypothesesDraft)
            problem = self.check_ranking(draft)
            if problem:
                return self.reject(call, "invalid_hypotheses", problem)
            self.ranking = [h.model_dump(mode="json") for h in draft.hypotheses]
            self.trace.event("hypotheses", turn=self.turns, state=self.state.value, ranking=self.ranking)
            self.accept(call, HARNESS_MESSAGES["accepted_hypotheses"])
            if self.state is State.HYPOTHESIZE:
                self.move(State.VERIFY, SUBMIT_HYPOTHESES)
        elif call.name == RETURN_TO_GATHER:
            if self.returns >= self.b.max_returns_to_gather:
                return self.reject(call, "precondition", HARNESS_MESSAGES["return_once"])
            self.accept(call, HARNESS_MESSAGES["accepted_return"])
            self.move(State.GATHER, RETURN_TO_GATHER)
        elif call.name == FINISH_VERIFYING:
            if self.verify_calls < self.b.min_verify_reads:
                return self.reject(call, "precondition", HARNESS_MESSAGES["need_verify_read"])
            self.accept(call, HARNESS_MESSAGES["accepted_finish_verifying"])
            self.move(State.REPORT, FINISH_VERIFYING)
        return None

    def may_finish_gathering(self) -> bool:
        """The finish_gathering precondition: 4 evidence calls on the first pass; none after a return."""
        return self.returns > 0 or self.gather_evidence_first_pass >= self.b.min_gather_evidence

    def check_ranking(self, draft: HypothesesDraft) -> str | None:
        ranks = [h.rank for h in draft.hypotheses]
        if ranks != list(range(1, len(ranks) + 1)):
            return HARNESS_MESSAGES["rank_order"]
        pairs = [(h.service, h.fault_type) for h in draft.hypotheses]
        if len(set(pairs)) != len(pairs):
            return HARNESS_MESSAGES["unique_pairs"]
        unknown = sorted({i for h in draft.hypotheses for i in (*h.supporting_evidence, *h.contradicting_evidence)
                          if i not in self.ledger})
        return HARNESS_MESSAGES["unknown_ids"].format(ids=", ".join(unknown)) if unknown else None

    def accept(self, call: ToolCallRequest, message: str) -> None:
        self.malformed = 0
        self.record(call, {"tool": call.name, "ok": True, "message": message}, valid=True, code=None, new=[],
                    records=[], kind=None, evidence=False, duplicate=False)

    def submit_report(self, call: ToolCallRequest, arguments: dict[str, Any]) -> InvestigationReport | None:
        try:
            draft = ReportDraft.model_validate(arguments)
            cited = [i for h in draft.hypotheses for i in (*h.supporting_evidence, *h.contradicting_evidence)]
            unknown = sorted({i for i in cited if i not in self.ledger})
            if unknown:
                raise ValueError(HARNESS_MESSAGES["unknown_ids"].format(ids=", ".join(unknown)))
            report = InvestigationReport(scenario_id=self.scenario_id, investigator=self.o.name,
                                         tool_calls=self.tool_calls, duration_s=self.elapsed(),
                                         stop_reason="sufficient_evidence", **draft.model_dump())
        except (ValidationError, ValueError) as exc:
            errors = _describe(exc) if isinstance(exc, ValidationError) else str(exc)
            self.record(call, _error(call.name, "invalid_report", errors), valid=False, code="invalid_report", new=[],
                        records=[], kind=None, evidence=False, duplicate=False)
            if self.repairs >= self.b.max_report_repairs:
                raise self.stop("error", f"report still invalid after {self.repairs} repair turn(s): {errors}"[:2000])
            self.repairs += 1
            return None
        self.accept(call, HARNESS_MESSAGES["accepted_report"])
        self.trace.event("claim_check", turn=self.turns, repaired=self.repairs > 0,
                         claims=[{"id": i, "in_seen_set": i in self.ledger,
                                  "rendered_in_request": i in self.rendered_ids} for i in cited])
        return report

    def cap(self, full: str) -> str:
        cap = self.b.result_char_cap
        return full if len(full) <= cap else (
            full[:cap] + HARNESS_MESSAGES["capped_result"].format(cap=cap, total=len(full)))

    def cited_in_ranking(self) -> set[str]:
        return {i for h in self.ranking for i in (*h.get("supporting_evidence", ()), *h.get("contradicting_evidence", ()))}

    def record(self, call: ToolCallRequest, result: dict[str, Any], *, valid: bool, code: str | None, new: list[str],
               records: list[dict[str, Any]], kind: str | None, evidence: bool, duplicate: bool) -> None:
        full = json.dumps(result, sort_keys=True)
        shown = self.cap(full)
        arguments = self.parse(call)
        summary = {"tool": call.name, "state": self.state.value,
                   "arguments": arguments if isinstance(arguments, dict) else call.raw_arguments[:200],
                   "ok": code is None and result.get("ok", True), "error": code,
                   "total_matches": result.get("total_matches"), "truncated": result.get("truncated"),
                   "new_ids": len(new), "sample_ids": new[:3],
                   "excerpts": [self.ledger.entries[i].excerpt for i in new[:3] if i in self.ledger]}
        exchange = Exchange(call, shown, summary)
        self.exchanges.append(exchange)
        self.trace.event("tool", turn=self.turns, state=self.state.value, call_id=call.id, name=call.name,
                         by_loop=False, arguments=call.raw_arguments[:TRACE_TEXT_CAP], valid=valid,
                         ok=code is None and bool(result.get("ok", True)), error_code=code, duplicate=duplicate,
                         new_ids=new, records=records, data_kind=kind, evidence=evidence, result_chars=len(full), shown=shown[:TRACE_TEXT_CAP], compacted=exchange.compact(160))

    def _records(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"id": i["source_id"], "kind": id_kind(i["source_id"]), "service": i.get("service") or i.get("caller")}
                for i in items if isinstance(i.get("source_id"), str)]
