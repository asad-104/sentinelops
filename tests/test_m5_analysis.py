"""M5 headline analysis (D1 primary, secondary arms, tiers, fault types, ablation, natural exposure, safety slices),
built before any fresh-split run. Offline: a tiny fresh-shaped set cut into 3 slices of 1, a scripted agent policy,
a scripted single-pass policy and the local baselines. Never the real fresh split."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_sets import fresh_shaped_set
from sentinelops.agent import single_pass as sp
from sentinelops.agent.mock import DemoAgentPolicy
from sentinelops.evaluation import agent_run, m5_analysis, safety
from sentinelops.evaluation.agent_run import Refused, run_agent
from sentinelops.evaluation.harness import DataMismatch
from sentinelops.evaluation.m5_analysis import AGENT, BARE, FULL, analyse, paired, resolve, sign_test, stems
from sentinelops.evaluation.single_pass_run import run_single_pass
from sentinelops.llm.mock import call
from sentinelops.simulator.profiles import Split


def _calm(path: Path) -> dict:
    return {"free_disk_gb": 50.0, "swap_used_mb": 100.0, "pressure_level": 1}


class CiteFirst:
    """Single-pass policy: blames orders/memory_leak, citing the alert and the first log in the bundle."""

    def describe(self):
        return {"backend": "policy"}

    def chat(self, messages, tools):
        ids = sorted(sp._ids("\n".join(m.content for m in messages[1:])))
        return call("submit_report", {"summary": "s", "hypotheses": [{
            "rank": 1, "service": "orders", "fault_type": "memory_leak", "confidence": "low", "rationale": "r",
            "supporting_evidence": [next(i for i in ids if i.startswith("ALR-")),
                                    next(i for i in ids if i.startswith("LOG-"))]}]})


@pytest.fixture()
def small_slices(monkeypatch):
    monkeypatch.setattr(agent_run, "FRESH_SLICES", 3)
    monkeypatch.setattr(agent_run, "FRESH_SLICE_SIZE", 1)


def _run_all(root: Path, data_root: Path, manifests: Path, skip: tuple[str, int] | None = None) -> Path:
    names = stems("fake", "scripted")
    out = root / "agent"
    for k in (1, 2, 3):
        ids = agent_run.fresh_slice(manifests, k)
        for arm, run in ((AGENT, lambda d: run_agent(DemoAgentPolicy(), "fake", "scripted", data_root, d, ids, manifests,
                                                     stats=_calm, twins=False, split=Split.M5FRESH, fresh_slice_k=k)),
                         (FULL, lambda d: run_single_pass(CiteFirst(), "fake", "scripted", "full", data_root, d, ids,
                                                          manifests, stats=_calm, split=Split.M5FRESH, fresh_slice_k=k)),
                         (BARE, lambda d: run_single_pass(CiteFirst(), "fake", "scripted", "no-timeline", data_root, d,
                                                          ids, manifests, stats=_calm, split=Split.M5FRESH,
                                                          fresh_slice_k=k))):
            if skip != (arm, k):
                run(out / names[arm].format(k=k))
        safety.run_safety(DemoAgentPolicy(), "fake", "scripted", data_root,
                          root / "safety" / names["safety"].format(k=k), manifest_dir=manifests, stats=_calm, slice_k=k)
    return out


def test_sign_test_is_exact_and_two_sided() -> None:
    assert sign_test(0, 0) == 1.0 and sign_test(5, 5) == 1.0
    assert sign_test(8, 2) == pytest.approx(2 * (1 + 10 + 45) / 1024)
    assert sign_test(2, 8) == sign_test(8, 2) and sign_test(10, 0) == pytest.approx(2 / 1024)


def test_paired_counts_only_scenarios_both_arms_ran() -> None:
    a = {"s1": {"top1": True}, "s2": {"top1": True}, "s3": {"top1": False}, "s4": {"top1": True}}
    b = {"s1": {"top1": False}, "s2": {"top1": True}, "s3": {"top1": True}}
    assert paired(a, b) == {"n_pairs": 3, "a_right_b_wrong": 1, "b_right_a_wrong": 1, "discordant": 2,
                            "p_two_sided": 1.0}


def test_resolve_prefers_attempt_2_and_refuses_a_third(tmp_path: Path) -> None:
    assert resolve(tmp_path, "x-slice1") == (None, None)
    (tmp_path / "x-slice1").mkdir()
    assert resolve(tmp_path, "x-slice1") == (tmp_path / "x-slice1", 1)
    (tmp_path / "x-slice1-attempt2").mkdir()
    (tmp_path / "x-slice10").mkdir()  # another slice's directory is never mistaken for an attempt
    assert resolve(tmp_path, "x-slice1") == (tmp_path / "x-slice1-attempt2", 2)
    (tmp_path / "x-slice1-attempt3").mkdir()
    with pytest.raises(Refused, match="one rerun"):
        resolve(tmp_path, "x-slice1")


def test_the_analysis_end_to_end(small_slices, tmp_path: Path) -> None:
    data_root, manifests, scenarios = fresh_shaped_set(tmp_path / "set")
    out = _run_all(tmp_path, data_root, manifests)
    a = analyse(out, tmp_path / "safety", data_root, manifests, backend="fake", model="scripted")
    assert a["metadata"]["complete"] and a["metadata"]["safety_complete"]
    assert set(a["arms"]) == {AGENT, FULL, BARE, "rule_based", "alert_service", "latest_change", "keyword_only"}
    n = len(scenarios)
    assert all(r["top1"]["n"] == n for r in a["arms"].values())
    # The primary is exactly the paired comparison of the two arms' per-scenario top-1
    rows = {arm: {r["scenario_id"]: r["top1"] for k in (1, 2, 3) for r in json.loads(
        (out / stems("fake", "scripted")[arm].format(k=k) / "summary.json").read_text())["runs"]} for arm in (AGENT, FULL)}
    b = sum(rows[AGENT][s] and not rows[FULL][s] for s in rows[AGENT])
    c = sum(rows[FULL][s] and not rows[AGENT][s] for s in rows[AGENT])
    assert (a["primary"]["n_pairs"], a["primary"]["a_right_b_wrong"], a["primary"]["b_right_a_wrong"]) == (n, b, c)
    agent = a["arms"][AGENT]
    assert sum(t["top1"]["n"] for t in agent["by_tier"].values()) == n
    assert sum(f["n"] for f in agent["by_fault_type"].values()) == n
    assert set(agent["by_fault_type"]["memory_leak"]) == {"top1", "top3", "n"}  # counts only, no interval
    injected = sum(t.injection is not None for _, t in scenarios)
    ne = a["natural_exposure"]
    assert ne["injected_originals"] == injected == ne["agent_runs"]
    assert 0 <= ne["agent_exposed"] <= injected and 0 <= ne["single_pass_full_exposed"] <= injected
    assert a["safety"]["exposed_pairs"] == injected and a["safety"]["counts"]["pairs_run"] == injected
    sec = a["secondary"]
    assert set(sec) == set(a["arms"]) and all(x["runs"] == n for x in sec.values())
    assert sec[AGENT]["investigated"]["a_valid_report"]["n"] == n and sec[FULL]["investigated"] is None
    assert sec[FULL]["tool_calls"] is None and sec["rule_based"]["tool_calls"]["median"] > 0
    assert sec[FULL]["trigger_seen"]["n"] == sum(t.trigger_source_id is not None for _, t in scenarios)
    assert sec["rule_based"]["trigger_seen"] is None and sec[AGENT]["valid_change_call"]["n"] == n
    text = m5_analysis.report_markdown(a)
    assert "INCOMPLETE" not in text and "Primary (D1)" in text and "No pass/fail verdict" in text
    assert "Other section 7 measures" in text and "Investigated (a)-(f)" in text


def test_attempt_2_replaces_attempt_1_and_a_missing_slice_is_incomplete(small_slices, tmp_path: Path) -> None:
    data_root, manifests, scenarios = fresh_shaped_set(tmp_path / "set")
    out = _run_all(tmp_path, data_root, manifests, skip=(BARE, 3))
    names = stems("fake", "scripted")
    ids = agent_run.fresh_slice(manifests, 2)
    run_agent(DemoAgentPolicy(), "fake", "scripted", data_root, out / f"{names[AGENT].format(k=2)}-attempt2", ids,
              manifests, stats=_calm, twins=False, split=Split.M5FRESH, fresh_slice_k=2, attempt=2)
    a = analyse(out, tmp_path / "safety", data_root, manifests, backend="fake", model="scripted", local=False)
    assert [s["attempt"] for s in a["slices"][AGENT]] == [1, 2, 1]
    assert not a["metadata"]["complete"] and a["arms"][BARE]["top1"]["n"] == len(scenarios) - 1
    assert a["ablation"]["n_pairs"] == len(scenarios) - 1
    assert "INCOMPLETE:** single_pass_no_timeline slice 3" in m5_analysis.report_markdown(a)


def test_metadata_must_match_the_slice(small_slices, tmp_path: Path) -> None:
    data_root, manifests, _ = fresh_shaped_set(tmp_path / "set")
    out = _run_all(tmp_path, data_root, manifests)
    path = out / stems("fake", "scripted")[FULL].format(k=1) / "summary.json"
    summary = json.loads(path.read_text())
    summary["metadata"]["scenarios"] = agent_run.fresh_slice(manifests, 2)
    path.write_text(json.dumps(summary))
    with pytest.raises(DataMismatch, match="scenarios"):
        analyse(out, tmp_path / "safety", data_root, manifests, backend="fake", model="scripted", local=False)
    summary["metadata"].update(scenarios=agent_run.fresh_slice(manifests, 1), model="other")
    path.write_text(json.dumps(summary))
    with pytest.raises(DataMismatch, match="model"):
        analyse(out, tmp_path / "safety", data_root, manifests, backend="fake", model="scripted", local=False)


def test_the_cli_writes_its_report(small_slices, tmp_path: Path, capsys) -> None:
    data_root, manifests, _ = fresh_shaped_set(tmp_path / "set")
    _run_all(tmp_path, data_root, manifests)
    # The CLI uses the mistral directory names; with only "fake" directories every slice is missing
    assert m5_analysis.main(["--agent-root", str(tmp_path / "agent"), "--safety-root", str(tmp_path / "safety"),
                             "--data-root", str(data_root), "--manifest-dir", str(manifests),
                             "--model", "scripted", "--out", str(tmp_path / "report")]) == 0
    assert "INCOMPLETE" in capsys.readouterr().out
    assert json.loads((tmp_path / "report" / "m5_analysis.json").read_text())["metadata"]["complete"] is False
    assert (tmp_path / "report" / "m5_analysis.md").is_file()
