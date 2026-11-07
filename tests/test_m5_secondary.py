"""M5 section 7 secondary measures (``m5_secondary``): per-run rules on hand-built events, and the development check
on the committed dev-gate outputs (skipped when ``data/dev`` has not been generated). Never the fresh split."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinelops.agent.single_pass import SinglePassInvestigator
from sentinelops.evaluation import m5_gate, m5_secondary
from sentinelops.evaluation.m5_secondary import (INVESTIGATED_PARTS, aggregate, directory_measures, run_measures,
                                                 secondary_lines)
from sentinelops.llm.trace import read_trace
from sentinelops.tools import ToolSet

GATE = Path("eval/agent/generator-v5")
V1, V2 = GATE / "m5-dev-gate-mistral-ministral-14b-2512-prompt-v1", GATE / "m5-dev-gate-mistral-ministral-14b-2512-prompt-v2"
FULL = GATE / "m5-dev-gate-single-pass-full-mistral-ministral-14b-2512"
BARE = GATE / "m5-dev-gate-single-pass-no-timeline-mistral-ministral-14b-2512"
DEV = Path("data/dev")
needs_dev = pytest.mark.skipif(not (DEV / "ground_truth").is_dir() or not V1.is_dir(), reason="data/dev not generated")


class _Truth:
    def __init__(self, trigger: str | None) -> None:
        self.trigger_source_id = trigger


def _row(valid: bool) -> dict:
    return {"scenario_id": "sc-x", "report_valid": valid}


def test_a_run_without_a_valid_report_cites_nothing_and_trigger_needs_to_be_shown() -> None:
    events = [{"event": "model", "wait_s": 2.0}, {"event": "stop", "elapsed_s": 10.0, "report": None}]
    r = run_measures("single_pass", _row(False), events, _Truth("DEP-003"), None, shown={"DEP-001"})
    assert (r["valid"], r["cited"], r["hypotheses"], r["unsupported"]) == (False, 0, 0, 0)
    assert r["has_trigger"] and not r["trigger_seen"] and (r["wall_s"], r["active_s"]) == (10.0, 8.0)
    r = run_measures("single_pass", _row(False), events, _Truth("DEP-003"), None, shown={"DEP-003"})
    assert r["trigger_seen"]
    r = run_measures("single_pass", _row(False), events, _Truth(None), None, shown={"DEP-003"})
    assert not r["has_trigger"] and not r["trigger_seen"]


def test_aggregate_counts_trigger_seen_only_over_runs_with_a_trigger_and_marks_inapplicable_measures() -> None:
    base = dict(valid=True, cited=2, headline_valid=1, strict_valid=2, lenient_valid=2, fabricated=0, hypotheses=2,
                unsupported=1, wall_s=5.0, active_s=4.0)
    rows = [{**base, "has_trigger": True, "trigger_seen": True}, {**base, "has_trigger": False, "trigger_seen": False},
            {**base, "has_trigger": True, "trigger_seen": False}]
    a = aggregate("single_pass", rows)
    assert (a["trigger_seen"]["k"], a["trigger_seen"]["n"]) == (1, 2)
    assert a["evidence_headline"] == {"k": 3, "n": 6, "pct": 50.0} and a["unsupported_hypotheses"] == {"k": 3, "n": 6}
    assert a["tool_calls"] is None and a["investigated"] is None and a["valid_change_call"] is None
    local = aggregate("local", [{**base, "tool_calls": 50}, {**base, "tool_calls": 54}])
    assert local["tool_calls"]["median"] == 52 and local["trigger_seen"] is None
    assert "n/a" in "\n".join(secondary_lines({"single_pass": a, "local": local}))


def test_the_cli_reads_dev_outputs_only(tmp_path: Path, capsys) -> None:
    d = tmp_path / "m5-fresh-x-slice1"
    d.mkdir()
    (d / "summary.json").write_text(json.dumps({"metadata": {"split": "m5fresh"}, "runs": []}))
    assert m5_secondary.main(["--dir", str(d), "--data-root", str(tmp_path)]) == 2
    assert "dev outputs only" in capsys.readouterr().err


@needs_dev
@pytest.mark.slow
def test_on_the_dev_gate_agent_outputs_the_measures_match_what_the_runs_recorded() -> None:
    for directory in (V1, V2):
        result = directory_measures(directory, DEV)
        summary = json.loads((directory / "summary.json").read_text())
        by_id = {r["scenario_id"]: r for r in summary["runs"]}
        assert len(result["rows"]) == 22
        for r in result["rows"]:
            stored = by_id[r["scenario_id"]]
            assert r["valid"] == stored["report_valid"] and r["tool_calls"] == stored["tool_calls"]
            assert all(r[p] == stored[f"investigated_{p}" if p != "investigated" else p] for p in INVESTIGATED_PARTS)
        gate = m5_gate.arm(directory)
        assert result["aggregate"]["valid_change_call"]["k"] == gate["valid_change_call_runs"]
    assert directory_measures(V1, DEV)["aggregate"]["valid_change_call"]["k"] == 0  # the M4 pattern
    assert directory_measures(V2, DEV)["aggregate"]["valid_change_call"]["k"] == 22


@needs_dev
@pytest.mark.slow
def test_on_the_dev_gate_single_pass_outputs_the_rebuilt_bundle_is_the_one_that_was_sent() -> None:
    for directory, variant in ((FULL, "full"), (BARE, "no-timeline")):
        summary = json.loads((directory / "summary.json").read_text())
        for r in summary["runs"]:
            bundle = next(e for e in read_trace(directory / "traces" / r["trace"]) if e["event"] == "bundle")
            _, estimate, reductions = SinglePassInvestigator(None, variant=variant)._fitting_request(
                ToolSet.from_directory(DEV / "scenarios", r["scenario_id"]))
            assert (estimate, reductions) == (bundle["estimated_tokens"], bundle["reductions"])
        result = directory_measures(directory, DEV)
        assert result["kind"] == "single_pass" and all(row["valid"] == by["report_valid"] for row, by in
                                                      zip(result["rows"], summary["runs"]))
