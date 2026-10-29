"""M4 state machine with scripted clients: transitions, wrong_state, caps, preconditions, stop reasons."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from sentinelops.agent.machine import StateMachineInvestigator
from sentinelops.agent.states import ALLOWED, TRANSITIONS, AgentBounds, State
from sentinelops.evaluation.harness import CountingToolSet
from sentinelops.llm.client import LLMError, LLMResponse
from sentinelops.llm.mock import ScriptedClient, call, text
from sentinelops.llm.trace import RunTrace
from sentinelops.report import InvestigationFailed
from sentinelops.tools import ToolSet

import sentinelops.agent.machine as machine


@pytest.fixture()
def run_events(monkeypatch: pytest.MonkeyPatch):
    """Capture each run's in-memory trace events."""
    captured: list[RunTrace] = []
    original = machine._Run.__init__

    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        captured.append(self.trace)

    monkeypatch.setattr(machine._Run, "__init__", init)
    return captured


def _searches(n: int, start: int = 1) -> list[LLMResponse]:
    """Read calls that each return new IDs (different services/levels/limits give different results)."""
    services = ["api-gateway", "auth", "orders", "payments"]
    out = []
    for i in range(start, start + n):
        out.append(call("search_logs", {"service": services[i % 4], "limit": 3 + i}, f"s{i}"))
    return out


def _ranking(ids: list[str], second: bool = True) -> dict:
    hyps = [{"rank": 1, "service": "orders", "fault_type": "memory_leak", "confidence": "low",
             "supporting_evidence": ids[:2], "rationale": "r"}]
    if second:
        hyps.append({"rank": 2, "service": "auth", "fault_type": "config_error", "confidence": "low",
                     "supporting_evidence": ids[2:3], "rationale": "r"})
    return {"hypotheses": hyps}


def _investigate(toolset: ToolSet, script, bounds: AgentBounds = AgentBounds(), clock=None):
    client = ScriptedClient(script)
    kwargs = {"clock": clock} if clock else {}
    agent = StateMachineInvestigator(client, bounds=bounds, **kwargs)
    sid = toolset.call("get_window").items[0].scenario_id
    return agent, client, CountingToolSet(toolset), sid


def _full_script(ids: list[str]) -> list[LLMResponse]:
    return [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h1"),
            call("search_logs", {"service": "auth", "limit": 2}, "v1"), call("finish_verifying", {}, "fv"),
            call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]


def _alert_ids(toolset: ToolSet) -> list[str]:
    alert = toolset.call("get_alert").items[0].source_id
    deps = [d.source_id for d in toolset.call("get_dependencies").items]
    return [alert, *deps]


def test_transition_table_is_exactly_the_preregistered_one() -> None:
    assert TRANSITIONS == {(State.TRIAGE, State.GATHER), (State.GATHER, State.HYPOTHESIZE),
                           (State.HYPOTHESIZE, State.VERIFY), (State.VERIFY, State.GATHER),
                           (State.VERIFY, State.REPORT)}
    assert ALLOWED[State.HYPOTHESIZE] == {"submit_hypotheses"} and ALLOWED[State.REPORT] == {"submit_report"}


def test_happy_path_walks_every_state_in_order(toolset: ToolSet, run_events) -> None:
    agent, client, tools, sid = _investigate(toolset, _full_script(_alert_ids(toolset)))
    report = agent.investigate(tools, sid)
    assert report.stop_reason == "sufficient_evidence"
    events = run_events[-1].events
    assert [e["state"] for e in events if e["event"] == "state_enter"] == ["TRIAGE", "GATHER", "HYPOTHESIZE",
                                                                          "VERIFY", "REPORT"]
    assert tools.calls[:3] == ["get_alert", "get_window", "get_dependencies"]  # TRIAGE is loop-issued
    assert report.tool_calls == 3 + 4 + 1


def test_hypothesize_to_gather_is_rejected_as_wrong_state(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    script = [*_searches(4), call("finish_gathering", {}, "fg"),
              call("search_logs", {"limit": 1}, "x1"), call("finish_gathering", {}, "x2"),
              call("return_to_gather", {}, "x3")]
    agent, client, tools, sid = _investigate(toolset, script)
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "error"  # three wrong_state calls in a row
    codes = [e["error_code"] for e in run_events[-1].events if e["event"] == "tool" and e["state"] == "HYPOTHESIZE"]
    assert codes == ["wrong_state", "wrong_state", "wrong_state"]
    assert "search_logs" not in tools.calls[7:]  # the rejected read never reached the ToolSet
    assert ids  # (the run never got far enough to cite them)


def test_finish_gathering_needs_four_evidence_calls(toolset: ToolSet, run_events) -> None:
    agent, client, tools, sid = _investigate(toolset, [*_searches(3), call("finish_gathering", {}, "fg"),
                                                       *_searches(1, 10), call("finish_gathering", {}, "fg2"),
                                                       LLMError("connection", "x"), LLMError("connection", "x")])
    with pytest.raises(InvestigationFailed):
        agent.investigate(tools, sid)
    events = run_events[-1].events
    fg = [e for e in events if e["event"] == "tool" and e["name"] == "finish_gathering"]
    assert [e["error_code"] for e in fg] == ["precondition", None]


def test_gather_first_pass_cap_moves_to_hypothesize(toolset: ToolSet, run_events) -> None:
    bounds = replace(AgentBounds(), gather_first_pass_cap=5)
    agent, client, tools, sid = _investigate(toolset, [*_searches(5), LLMError("connection", "x"),
                                                       LLMError("connection", "x")], bounds)
    with pytest.raises(InvestigationFailed):
        agent.investigate(tools, sid)
    enters = [e for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[-1]["state"] == "HYPOTHESIZE" and enters[-1]["reason"] == "gather cap"


def test_verify_cap_covers_both_passes_and_return_is_allowed_once(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    bounds = replace(AgentBounds(), verify_cap=3)
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              *_searches(2, 20), call("return_to_gather", {}, "rg"), *_searches(1, 30), call("finish_gathering", {}, "f2"),
              call("submit_hypotheses", _ranking(ids), "h2"), *_searches(1, 40),  # third VERIFY read: cap of 3 reached
              call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]
    agent, client, tools, sid = _investigate(toolset, script, bounds)
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    enters = [(e["state"], e["reason"]) for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[-1] == ("REPORT", "verify cap") and ("GATHER", "return_to_gather") in enters
    script2 = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
               call("return_to_gather", {}, "rg"), call("finish_gathering", {}, "f2"),
               call("submit_hypotheses", _ranking(ids), "h2"), call("return_to_gather", {}, "rg2"),
               LLMError("connection", "x"), LLMError("connection", "x")]
    agent, client, tools, sid = _investigate(toolset, script2)
    with pytest.raises(InvestigationFailed):
        agent.investigate(tools, sid)
    second = [e for e in run_events[-1].events if e["event"] == "tool" and e.get("call_id") == "rg2"]
    assert second[0]["error_code"] == "precondition"


def test_gather_after_return_comes_out_of_the_global_budget(toolset: ToolSet) -> None:
    ids = _alert_ids(toolset)
    bounds = replace(AgentBounds(), max_tool_calls=10)
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              *_searches(1, 20), call("return_to_gather", {}, "rg"), *_searches(5, 30)]
    agent, client, tools, sid = _investigate(toolset, script, bounds)
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "budget_exhausted" and len(tools.calls) == 10


def test_finish_verifying_needs_a_verify_read(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              call("finish_verifying", {}, "fv"), *_searches(1, 50), call("finish_verifying", {}, "fv2"),
              call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]
    agent, client, tools, sid = _investigate(toolset, script)
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    fv = [e["error_code"] for e in run_events[-1].events if e["event"] == "tool" and e["name"] == "finish_verifying"]
    assert fv == ["precondition", None]


def test_hypotheses_and_reports_may_cite_only_seen_ids(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    fake = {"hypotheses": [{"rank": 1, "service": "orders", "fault_type": "memory_leak", "confidence": "low",
                            "supporting_evidence": ["LOG-99999"], "rationale": "r"}]}
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", fake, "bad"),
              call("submit_hypotheses", _ranking(ids), "h"), *_searches(1, 60), call("finish_verifying", {}, "fv"),
              call("submit_report", {"summary": "s", **fake}, "r1"), call("submit_report", {"summary": "s", **_ranking(ids)}, "r2")]
    agent, client, tools, sid = _investigate(toolset, script)
    report = agent.investigate(tools, sid)
    events = run_events[-1].events
    codes = {e["call_id"]: e["error_code"] for e in events if e["event"] == "tool"}
    assert codes["bad"] == "invalid_hypotheses" and codes["r1"] == "invalid_report"
    check = next(e for e in events if e["event"] == "claim_check")
    assert check["repaired"] is True
    assert all(c["in_seen_set"] for c in check["claims"])
    assert {"rendered_in_request", "in_seen_set"} <= set(check["claims"][0])
    assert report.executed_actions == ()


def test_report_still_invalid_after_one_repair_stops_with_error(toolset: ToolSet) -> None:
    ids = _alert_ids(toolset)
    bad = call("submit_report", {"summary": "s", "hypotheses": []}, "r")
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              *_searches(1, 60), call("finish_verifying", {}, "fv"), bad, bad]
    agent, client, tools, sid = _investigate(toolset, script)
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "error" and "still invalid" in failed.value.message


def test_truncated_output_is_malformed_and_never_executed(toolset: ToolSet, run_events) -> None:
    cut = LLMResponse(text="", tool_calls=call("search_logs", {"limit": 2}, "cut").tool_calls, truncated=True)
    agent, client, tools, sid = _investigate(toolset, [cut, cut, cut])
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "error"
    assert tools.calls == ["get_alert", "get_window", "get_dependencies"]  # nothing from the cut replies ran
    assert "cut off at the output limit" in client.requests[1][0][-1].content


def test_text_only_replies_are_malformed(toolset: ToolSet) -> None:
    agent, client, tools, sid = _investigate(toolset, [text("hm"), text("hm"), text("hm")])
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "error"


def test_no_new_evidence_and_identical_calls(toolset: ToolSet) -> None:
    same = call("search_logs", {"limit": 2}, "same")
    agent, client, tools, sid = _investigate(toolset, [same, same, same])
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "no_new_evidence"
    stale = [call("search_logs", {"limit": 2}, "a"), call("search_logs", {"limit": 1}, "b"),
             call("search_logs", {"limit": 2, "min_level": "INFO"}, "c"), call("search_logs", {"limit": 1, "min_level": "INFO"}, "d")]
    agent, client, tools, sid = _investigate(toolset, stale)
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "no_new_evidence"  # precondition not met: the run still ends


def _empties() -> list[LLMResponse]:
    """Valid, non-identical reads whose results are subsets of what ``_searches(4)`` already showed."""
    return [call("search_logs", {"service": s, "limit": 1}, f"e-{s}") for s in ("auth", "orders", "payments")]


NO_NEW_NOTE = "3 GATHER calls in a row returned no new source ID; moved to HYPOTHESIZE."


def test_no_new_evidence_after_the_precondition_moves_to_hypothesize(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    script = [*_searches(4), *_empties(), call("submit_hypotheses", _ranking(ids), "h"),
              call("search_logs", {"service": "auth", "limit": 2}, "v1"), call("finish_verifying", {}, "fv"),
              call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]
    agent, client, tools, sid = _investigate(toolset, script)
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    events = run_events[-1].events
    assert [e["new_ids"] for e in events if e["event"] == "tool" and e["call_id"].startswith("e-")] == [[], [], []]
    enters = [(e["state"], e["reason"]) for e in events if e["event"] == "state_enter"]
    assert enters == [("TRIAGE", "start"), ("GATHER", "triage done"), ("HYPOTHESIZE", "no new evidence"),
                      ("VERIFY", "submit_hypotheses"), ("REPORT", "finish_verifying")]
    stage = client.requests[7][0][-1].content  # the request after the third empty call
    assert "STAGE (from the harness): HYPOTHESIZE" in stage and NO_NEW_NOTE in stage
    assert NO_NEW_NOTE not in client.requests[8][0][-1].content  # notes are shown once


def test_no_new_evidence_after_return_to_gather_moves_to_hypothesize(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              call("search_logs", {"service": "auth", "limit": 2}, "v1"), call("return_to_gather", {}, "rg"),
              *_empties(), call("submit_hypotheses", _ranking(ids), "h2"), call("finish_verifying", {}, "fv"),
              call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]
    agent, client, tools, sid = _investigate(toolset, script)
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    enters = [(e["state"], e["reason"]) for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[4:] == [("GATHER", "return_to_gather"), ("HYPOTHESIZE", "no new evidence"),
                          ("VERIFY", "submit_hypotheses"), ("REPORT", "finish_verifying")]


IDENTICAL_NOTE = "3 identical GATHER calls in a row; the last one was not run. Moved to HYPOTHESIZE."


def _rest(ids: list[str]) -> list[LLMResponse]:
    return [call("submit_hypotheses", _ranking(ids), "h"), call("search_logs", {"service": "auth", "limit": 2}, "v1"),
            call("finish_verifying", {}, "fv"), call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]


def test_identical_calls_before_the_precondition_still_end_the_run(toolset: ToolSet) -> None:
    same = call("search_logs", {"service": "auth", "limit": 20}, "same")
    agent, client, tools, sid = _investigate(toolset, [*_searches(2), same, same, same])
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "no_new_evidence" and "identical" in str(failed.value)


def test_identical_calls_after_the_precondition_move_to_hypothesize(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    same = call("search_logs", {"service": "auth", "limit": 20}, "same")  # new IDs once, then nothing new
    agent, client, tools, sid = _investigate(toolset, [*_searches(4), same, same, same, *_rest(ids)])
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    events = run_events[-1].events
    assert [len(e["new_ids"]) > 0 for e in events if e["event"] == "tool" and e["call_id"] == "same"] == [True, False]
    assert tools.calls.count("search_logs") == 4 + 2 + 1  # the third identical call was not run
    enters = [(e["state"], e["reason"]) for e in events if e["event"] == "state_enter"]
    assert enters == [("TRIAGE", "start"), ("GATHER", "triage done"), ("HYPOTHESIZE", "identical calls"),
                      ("VERIFY", "submit_hypotheses"), ("REPORT", "finish_verifying")]
    stage = client.requests[7][0][-1].content  # the request after the third identical call
    assert "STAGE (from the harness): HYPOTHESIZE" in stage and IDENTICAL_NOTE in stage
    assert IDENTICAL_NOTE not in client.requests[8][0][-1].content


def test_identical_calls_after_return_to_gather_move_to_hypothesize(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    same = call("search_logs", {"service": "orders", "limit": 30}, "same")
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              call("search_logs", {"service": "auth", "limit": 2}, "v1"), call("return_to_gather", {}, "rg"),
              same, same, same, call("submit_hypotheses", _ranking(ids), "h2"), call("finish_verifying", {}, "fv"),
              call("submit_report", {"summary": "s", **_ranking(ids)}, "r")]
    agent, client, tools, sid = _investigate(toolset, script)
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    enters = [(e["state"], e["reason"]) for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[4:] == [("GATHER", "return_to_gather"), ("HYPOTHESIZE", "identical calls"),
                          ("VERIFY", "submit_hypotheses"), ("REPORT", "finish_verifying")]


def test_identical_and_empty_triggers_on_the_same_call_move_once(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    same = call("search_logs", {"service": "auth", "limit": 1}, "same")  # empty: run, the no-new streak would be 3
    agent, client, tools, sid = _investigate(toolset, [*_searches(4), same, same, same, *_rest(ids)])
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    enters = [(e["state"], e["reason"]) for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[2] == ("HYPOTHESIZE", "identical calls") and len(enters) == 5
    stage = client.requests[7][0][-1].content
    assert IDENTICAL_NOTE in stage and NO_NEW_NOTE not in stage


def test_identical_calls_on_the_cap_call_move_once(toolset: ToolSet, run_events) -> None:
    ids = _alert_ids(toolset)
    bounds = replace(AgentBounds(), gather_first_pass_cap=7)  # the third identical call would be the cap call
    same = call("search_logs", {"service": "auth", "limit": 20}, "same")
    agent, client, tools, sid = _investigate(toolset, [*_searches(4), same, same, same, *_rest(ids)], bounds)
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    enters = [(e["state"], e["reason"]) for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[2] == ("HYPOTHESIZE", "identical calls") and len(enters) == 5


def test_identical_calls_in_verify_still_end_the_run(toolset: ToolSet) -> None:
    ids = _alert_ids(toolset)
    same = call("search_logs", {"service": "auth", "limit": 2}, "same")
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("submit_hypotheses", _ranking(ids), "h"),
              same, same, same]
    agent, client, tools, sid = _investigate(toolset, script)
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "no_new_evidence" and "identical" in str(failed.value)


def test_no_new_evidence_on_the_cap_call_moves_once(toolset: ToolSet, run_events) -> None:
    bounds = replace(AgentBounds(), gather_first_pass_cap=7)  # the third empty call is also the cap call
    agent, client, tools, sid = _investigate(toolset, [*_searches(4), *_empties(), LLMError("connection", "x"),
                                                       LLMError("connection", "x")], bounds)
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "error"  # the two client errors, in HYPOTHESIZE
    enters = [(e["state"], e["reason"]) for e in run_events[-1].events if e["event"] == "state_enter"]
    assert enters[-1] == ("HYPOTHESIZE", "no new evidence") and len(enters) == 3


def test_timeout_unloads_then_retries_once_and_two_stop(toolset: ToolSet, run_events) -> None:
    class Unloading(ScriptedClient):
        unloads = 0

        def unload(self):
            Unloading.unloads += 1
            return None

    ids = _alert_ids(toolset)
    client = Unloading([LLMError("timeout", "slow"), *_full_script(ids)])
    agent = StateMachineInvestigator(client)
    sid = toolset.call("get_window").items[0].scenario_id
    assert agent.investigate(CountingToolSet(toolset), sid).stop_reason == "sufficient_evidence"
    assert Unloading.unloads == 1
    assert any(e["event"] == "unload" and e["reason"] == "after timeout" for e in run_events[-1].events)
    client = Unloading([LLMError("timeout", "slow"), LLMError("timeout", "slow")])
    with pytest.raises(InvestigationFailed) as failed:
        StateMachineInvestigator(client).investigate(CountingToolSet(toolset), sid)
    assert failed.value.stop_reason == "timeout" and Unloading.unloads == 3


def test_total_wall_time_and_turn_cap(toolset: ToolSet) -> None:
    ticks = iter([0.0, 0.0, 1000.0, 1900.0, 1900.0])
    agent, client, tools, sid = _investigate(toolset, _searches(5), clock=lambda: next(ticks))
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "timeout"
    agent, client, tools, sid = _investigate(toolset, _searches(10), replace(AgentBounds(), max_turns=2))
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "budget_exhausted" and "turn cap" in failed.value.message


def test_bounds_are_the_preregistered_values() -> None:
    b = AgentBounds()
    assert (b.max_tool_calls, b.gather_first_pass_cap, b.verify_cap, b.min_gather_evidence) == (40, 16, 8, 4)
    assert (b.call_timeout_s, b.total_timeout_s, b.max_consecutive_timeouts, b.max_turns) == (180.0, 1800.0, 2, 60)
    assert (b.num_ctx, b.num_predict, b.prompt_budget, b.server_guard_fraction) == (8192, 2048, 6144, 0.9)
    assert b.prompt_budget + b.num_predict == b.num_ctx


def test_every_tool_message_is_valid_json_or_capped(toolset: ToolSet) -> None:
    agent, client, tools, sid = _investigate(toolset, _full_script(_alert_ids(toolset)))
    agent.investigate(tools, sid)
    for messages, _ in client.requests:
        for m in messages:
            if m.role == "tool" and "[truncated_for_context" not in m.content:
                json.loads(m.content)


def test_unload_after_timeout_reaches_the_model_through_the_progress_wrapper(toolset: ToolSet, run_events) -> None:
    """Regression (smoke run 2): ProgressClient did not forward unload, so D3's unload-then-retry was skipped."""
    import io

    from sentinelops.evaluation.pilot import Progress, ProgressClient
    from sentinelops.llm.mock import ScriptedClient as Plain

    class Unloading(Plain):
        def __init__(self, script):
            super().__init__(script)
            self.unloads = 0

        def unload(self):
            self.unloads += 1
            return None

    inner = Unloading([LLMError("timeout", "slow"), LLMError("timeout", "slow")])
    progress = Progress(1, 40, lambda p: {"free_disk_gb": 50.0, "swap_used_mb": 1.0, "pressure_level": 1},
                        Path("."), io.StringIO())
    wrapped = ProgressClient(inner, progress)
    sid = toolset.call("get_window").items[0].scenario_id
    tools = CountingToolSet(toolset)
    progress.start_run(sid, tools)
    with pytest.raises(InvestigationFailed) as failed:
        StateMachineInvestigator(wrapped).investigate(tools, sid)
    assert failed.value.stop_reason == "timeout"
    assert inner.unloads == 2
    assert sum(e["event"] == "unload" for e in run_events[-1].events) == 2
    assert not hasattr(ProgressClient(Plain([]), progress), "unload")  # nothing to forward, nothing exposed


def test_each_state_sends_its_tool_list_through_the_full_loop(toolset: ToolSet, run_events) -> None:
    """Context revision 3: HYPOTHESIZE and REPORT carry only their own tool; GATHER and VERIFY carry all."""
    from sentinelops.agent.context import specs_chars
    from sentinelops.agent.schemas import agent_tool_specs

    every = [s.name for s in agent_tool_specs()]
    agent, client, tools, sid = _investigate(toolset, _full_script(_alert_ids(toolset)))
    assert agent.investigate(tools, sid).stop_reason == "sufficient_evidence"
    contexts = [e for e in run_events[-1].events if e["event"] == "context"]
    sent = [[t.name for t in specs] for _, specs in client.requests]
    assert [c["state"] for c in contexts] == ["GATHER"] * 5 + ["HYPOTHESIZE", "VERIFY", "VERIFY", "REPORT"]
    for context, names, (_, specs) in zip(contexts, sent, client.requests):
        expected = {"HYPOTHESIZE": ["submit_hypotheses"], "REPORT": ["submit_report"]}.get(context["state"], every)
        assert names == expected
        assert context["components"]["tool_specs"] == specs_chars(specs)  # the estimate counted what was sent


def test_the_tool_list_per_state_is_frozen() -> None:
    from sentinelops.agent.schemas import NARROW_STATES, agent_tool_specs, state_tool_specs

    specs = agent_tool_specs()
    assert NARROW_STATES == {State.HYPOTHESIZE, State.REPORT}
    assert {s: [t.name for t in state_tool_specs(s, specs)] for s in NARROW_STATES} == {
        State.HYPOTHESIZE: ["submit_hypotheses"], State.REPORT: ["submit_report"]}
    for state in (State.GATHER, State.VERIFY):
        assert state_tool_specs(state, specs) == specs  # unchanged, in the fixed order


def test_a_tool_not_sent_is_still_rejected_as_wrong_state(toolset: ToolSet, run_events) -> None:
    script = [*_searches(4), call("finish_gathering", {}, "fg"), call("search_logs", {"limit": 1}, "x"),
              LLMError("connection", "x"), LLMError("connection", "x")]
    agent, client, tools, sid = _investigate(toolset, script)
    with pytest.raises(InvestigationFailed):
        agent.investigate(tools, sid)
    hypothesize_tools = [t.name for t in client.requests[5][1]]
    assert hypothesize_tools == ["submit_hypotheses"]  # search_logs was not offered...
    rejected = [e for e in run_events[-1].events if e["event"] == "tool" and e["call_id"] == "x"]
    assert rejected[0]["error_code"] == "wrong_state"  # ...and calling it anyway is rejected, as before


class _WaitingClient:
    """Scripted reads that advance a fake clock by ``step_s`` per call, of which ``wait_s`` is reported as a
    provider rate-limit wait, as a paced hosted client would."""

    def __init__(self, wait_s: float, step_s: float) -> None:
        self.wait_s, self.step_s, self.now, self.n = wait_s, step_s, 0.0, 0

    def clock(self) -> float:
        return self.now

    def describe(self) -> dict:
        return {"backend": "waiting"}

    def chat(self, messages, tools):
        self.now += self.step_s
        self.n += 1
        services = ["api-gateway", "auth", "orders", "payments"]
        return replace(call("search_logs", {"service": services[self.n % 4], "limit": 3 + self.n}, f"w{self.n}"),
                       wait_s=self.wait_s)


def test_the_time_bound_counts_active_time_not_provider_waits(toolset: ToolSet, run_events) -> None:
    """User decision 2026-10-28: the 30-minute bound applies to wall time minus provider waits."""
    sid = toolset.call("get_window").items[0].scenario_id
    bounds = replace(AgentBounds(), max_turns=6)
    waiting = _WaitingClient(wait_s=1000.0, step_s=1001.0)  # 6 turns: 6,006 s wall, 6 s active
    with pytest.raises(InvestigationFailed) as failed:
        StateMachineInvestigator(waiting, clock=waiting.clock, bounds=bounds).investigate(CountingToolSet(toolset), sid)
    stop = next(e for e in run_events[-1].events if e["event"] == "stop")
    assert failed.value.stop_reason == "budget_exhausted" and "turn cap" in failed.value.message
    assert stop["elapsed_s"] > 1800 and stop["active_s"] == pytest.approx(6.0) and stop["wait_s"] == 6000.0
    control = _WaitingClient(wait_s=0.0, step_s=1001.0)  # the same wall time with no waits is all active
    with pytest.raises(InvestigationFailed) as failed:
        StateMachineInvestigator(control, clock=control.clock, bounds=bounds).investigate(CountingToolSet(toolset), sid)
    stop = next(e for e in run_events[-1].events if e["event"] == "stop")
    assert failed.value.stop_reason == "timeout" and "active time" in failed.value.message
    assert stop["active_s"] == stop["elapsed_s"] >= 1800 and stop["wait_s"] == 0.0


def test_a_provider_caused_error_stops_the_run_at_once_and_is_flagged(toolset: ToolSet, run_events) -> None:
    limit = LLMError("http_status", "HTTP 429: provider asks to wait 445 s", wait_s=60.0, provider_caused=True)
    agent, client, tools, sid = _investigate(toolset, [*_searches(4), limit, *_searches(3, 10)])
    with pytest.raises(InvestigationFailed) as failed:
        agent.investigate(tools, sid)
    assert failed.value.stop_reason == "error" and failed.value.provider_caused
    assert failed.value.message.startswith("provider-caused: http_status")
    assert len(client.requests) == 5  # no retry by the loop after a provider-caused error
    events = run_events[-1].events
    stop = next(e for e in events if e["event"] == "stop")
    assert stop["provider_caused"] is True and stop["wait_s"] == 60.0
    assert [e["provider_caused"] for e in events if e["event"] == "model" and e.get("error")] == [True]
