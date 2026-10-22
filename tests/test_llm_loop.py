"""The M3 tool loop with a scripted client: bounds, stop reasons, malformed calls, injection as data."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from sentinelops.evaluation.harness import CountingToolSet
from sentinelops.llm.client import LLMError
from sentinelops.llm.loop import LoopBounds, ToolLoopInvestigator
from sentinelops.llm.mock import ScriptedClient, call, text
from sentinelops.llm.prompt import SYSTEM_PROMPT
from sentinelops.llm.trace import TraceWriter, read_trace
from sentinelops.report import InvestigationFailed
from sentinelops.simulator import FaultType, generate_scenario
from sentinelops.tools import ToolSet

REPORT = {"summary": "s", "hypotheses": [{"rank": 1, "service": "orders", "fault_type": "memory_leak",
                                          "confidence": "low", "supporting_evidence": ["ALR-001"],
                                          "rationale": "r"}]}


def _run(toolset: ToolSet, script, bounds: LoopBounds = LoopBounds(), tmp_path: Path | None = None, clock=None):
    client = ScriptedClient(script)
    traces = TraceWriter(tmp_path) if tmp_path else None
    kwargs = {"clock": clock} if clock else {}
    loop = ToolLoopInvestigator(client, bounds=bounds, traces=traces, **kwargs)
    tools = CountingToolSet(toolset)
    sid = toolset.call("get_window").items[0].scenario_id
    return loop, client, tools, sid


def _events(tmp_path: Path) -> list[dict]:
    return read_trace(next(tmp_path.glob("*.jsonl")))


def test_happy_path_reports_sufficient_evidence(toolset: ToolSet, tmp_path: Path) -> None:
    loop, client, tools, sid = _run(toolset, [call("search_logs", {"limit": 5}), call("submit_report", REPORT)],
                                    tmp_path=tmp_path)
    report = loop.investigate(tools, sid)
    assert report.stop_reason == "sufficient_evidence" and report.tool_calls == 2
    assert tools.calls == ["get_alert", "search_logs"]  # the loop's alert fetch plus one model call
    first_messages = client.requests[0][0]
    assert first_messages[0].role == "system" and first_messages[0].content == SYSTEM_PROMPT
    assert "ALR-001" in first_messages[1].content
    second = client.requests[1][0]
    assert second[-1].role == "tool" and second[-1].tool_name == "search_logs"
    stop = _events(tmp_path)[-1]
    assert stop["event"] == "stop" and stop["stop_reason"] == "sufficient_evidence" and stop["report"]


def test_malformed_calls_become_structured_errors(toolset: ToolSet, tmp_path: Path) -> None:
    # Three malformed calls in a row stop the run, so a valid call is interleaved after two.
    script = [call("search_logs", raw="{oops"), call("delete_logs", {}), call("get_window", {}, "ok1"),
              call("search_logs", {"limit": 0}), call("get_window", {}), call("submit_report", REPORT)]
    loop, client, tools, sid = _run(toolset, script, tmp_path=tmp_path)
    assert loop.investigate(tools, sid).stop_reason == "sufficient_evidence"
    tool_events = [e for e in _events(tmp_path) if e["event"] == "tool" and not e["by_loop"]]
    codes = [e["error_code"] for e in tool_events]
    assert codes[:4] == ["invalid_json", "unknown_tool", None, "invalid_arguments"]
    assert [e["valid"] for e in tool_events] == [False, False, True, False, True, True]
    replies = [m for m in client.requests[-1][0] if m.role == "tool"]
    assert json.loads(replies[0].content)["error"]["code"] == "invalid_json"
    assert "available tools" in json.loads(replies[1].content)["error"]["message"]
    assert "delete_logs" not in tools.calls  # unknown tools never reach the ToolSet


def test_three_malformed_in_a_row_stop_with_error(toolset: ToolSet) -> None:
    loop, _, tools, sid = _run(toolset, [call("x", {}), call("search_logs", raw="["), call("search_logs", {"limit": -1})])
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "error"


def test_text_only_replies_count_as_malformed(toolset: ToolSet) -> None:
    loop, client, tools, sid = _run(toolset, [text("thinking..."), text("still thinking"), text("done?")])
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "error"
    assert "No tool call received" in client.requests[1][0][-1].content


def test_tool_call_budget(toolset: ToolSet) -> None:
    script = [call("search_logs", {"limit": i}) for i in range(1, 10)]
    loop, _, tools, sid = _run(toolset, script, LoopBounds(max_tool_calls=3))
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "budget_exhausted"
    assert len(tools.calls) == 3  # get_alert + two searches; the third search was refused


def test_default_budget_is_thirty_tool_calls(toolset: ToolSet) -> None:
    script = [call("search_logs", {"limit": i}) for i in range(1, 40)]
    loop, _, tools, sid = _run(toolset, script)
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "budget_exhausted" and len(tools.calls) == 30


def test_model_turn_cap(toolset: ToolSet) -> None:
    script = [call("search_logs", {"limit": i}) for i in range(1, 10)]
    loop, _, tools, sid = _run(toolset, script, LoopBounds(max_turns=2))
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "budget_exhausted" and "turn cap" in failed.value.message


def test_consecutive_timeouts_stop_but_one_is_retried(toolset: ToolSet) -> None:
    loop, _, tools, sid = _run(toolset, [LLMError("timeout", "slow"), call("submit_report", REPORT)])
    assert loop.investigate(tools, sid).stop_reason == "sufficient_evidence"
    loop, _, tools, sid = _run(toolset, [LLMError("timeout", "slow"), LLMError("timeout", "slow")])
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "timeout"


def test_persistent_client_errors_stop_with_error(toolset: ToolSet) -> None:
    loop, _, tools, sid = _run(toolset, [LLMError("connection", "refused"), LLMError("http_status", "500")])
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "error"


def test_total_wall_time_is_enforced_without_sleeping(toolset: ToolSet) -> None:
    ticks = iter([0.0, 0.0, 700.0, 1300.0, 1300.0])
    script = [call("search_logs", {"limit": 1}), call("search_logs", {"limit": 2}), call("submit_report", REPORT)]
    loop, _, tools, sid = _run(toolset, script, clock=lambda: next(ticks))
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "timeout"


def test_identical_calls_are_flagged_then_stopped(toolset: ToolSet, tmp_path: Path) -> None:
    same = call("search_logs", {"limit": 3})
    loop, client, tools, sid = _run(toolset, [same, same, same], tmp_path=tmp_path)
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "no_new_evidence"
    flags = [e["duplicate"] for e in _events(tmp_path) if e["event"] == "tool" and not e["by_loop"]]
    assert flags == [False, True]
    assert json.loads(client.requests[-1][0][-1].content)["duplicate_call"] is True


def test_invalid_report_gets_one_repair_turn(toolset: ToolSet, tmp_path: Path) -> None:
    bad = call("submit_report", {"summary": "no hypotheses"})
    loop, client, tools, sid = _run(toolset, [bad, call("submit_report", REPORT)], tmp_path=tmp_path)
    assert loop.investigate(tools, sid).stop_reason == "sufficient_evidence"
    assert "hypotheses" in json.loads(client.requests[1][0][-1].content)["error"]["message"]
    submits = [e for e in _events(tmp_path) if e.get("name") == "submit_report"]
    assert [e["valid"] for e in submits] == [False, True] and submits[-1]["repaired"] is True
    loop, _, tools, sid = _run(toolset, [bad, bad])
    with pytest.raises(InvestigationFailed) as failed:
        loop.investigate(tools, sid)
    assert failed.value.stop_reason == "error" and "still invalid" in failed.value.message


def test_reports_cannot_claim_executed_actions(toolset: ToolSet) -> None:
    acting = call("submit_report", {**REPORT, "executed_actions": ["restarted payments"]})
    loop, _, tools, sid = _run(toolset, [acting, acting])
    with pytest.raises(InvestigationFailed):
        loop.investigate(tools, sid)


def test_oversized_results_are_capped_and_flagged(toolset: ToolSet, tmp_path: Path) -> None:
    loop, client, tools, sid = _run(toolset, [call("search_logs", {"limit": 200}), call("submit_report", REPORT)],
                                    tmp_path=tmp_path)
    loop.investigate(tools, sid)
    shown = client.requests[1][0][-1].content
    assert len(shown) < 4200 and "[truncated_for_context: showing 4000 of" in shown
    event = next(e for e in _events(tmp_path) if e.get("name") == "search_logs")
    assert event["truncated_for_context"] is True and event["result_chars"] > 4000


@pytest.fixture(scope="module")
def injected():
    for index in range(40):
        scenario = generate_scenario(91, index, FaultType.MEMORY_LEAK)
        if scenario.ground_truth.injection is not None:
            return scenario
    raise AssertionError("no injected scenario found")


def test_injected_text_reaches_the_model_only_as_tool_data(injected) -> None:
    observable, truth = injected
    injected_id = truth.injection.source_ids[0]
    payload = next(r.message for r in observable.logs if r.source_id == injected_id)
    toolset = ToolSet(observable)
    loop, client, tools, sid = _run(toolset, [call("get_record", {"source_id": injected_id}),
                                              call("submit_report", REPORT)])
    report = loop.investigate(tools, sid)
    messages = client.requests[-1][0]
    tool_message = messages[-1]
    assert tool_message.role == "tool" and payload in json.loads(tool_message.content)["items"][0]["message"]
    assert [m.role for m in messages].count("system") == 1 and payload not in messages[0].content
    assert all(payload not in m.content for m in messages if m.role != "tool")
    assert report.executed_actions == () and tools.calls == ["get_alert", "get_record"]


def test_loop_without_trace_writer_keeps_no_files(toolset: ToolSet, tmp_path: Path) -> None:
    loop, _, tools, sid = _run(toolset, [call("submit_report", REPORT)])
    loop.investigate(tools, sid)
    assert loop.traces is None and not any(tmp_path.iterdir())


def test_bounds_are_the_preregistered_values() -> None:
    b = LoopBounds()
    assert (b.max_tool_calls, b.max_turns, b.call_timeout_s, b.total_timeout_s, b.result_char_cap) == (
        30, 40, 180.0, 1200.0, 4000)
    assert (b.max_consecutive_timeouts, b.max_identical_calls, b.max_consecutive_malformed,
            b.max_report_repairs) == (2, 3, 3, 1)
    assert replace(b, max_turns=1).max_turns == 1
