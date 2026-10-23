"""M4 agent CLI: fixed set, mock refusals (core scenarios, eval/agent/), mock end to end on a generated set,
no overwrite, summary on abort, no secrets, frozen prompt. No model, no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_sets import generated_set
from sentinelops.agent.mock import DemoAgentPolicy
from sentinelops.agent.prompt import SYSTEM_PROMPT, prompt_sha256
from sentinelops.evaluation import agent_run
from sentinelops.evaluation.agent_run import (
    CORE_SCENARIOS,
    REAL_RESULTS,
    Refused,
    check_mock_target,
    main,
    run_agent,
)
from sentinelops.evaluation.harness import HarnessAbort
from sentinelops.evaluation.pilot import PILOT_SCENARIOS, OutputExists
from sentinelops.simulator.datasets import build_split, manifest_path
from sentinelops.simulator.profiles import Split

PREREGISTERED_CORE = ("sc-30385ffc64", "sc-3836c69ef7", "sc-3e3ceb314e", "sc-4001bf784c", "sc-408b514aeb",
                      "sc-4251e8920a", "sc-497fd61898", "sc-5b55b772de", "sc-5c5b9b9197", "sc-91404ea5fc")
# Frozen 2026-10-23 in stage A; a change needs a logged prompt revision in docs/PROGRESS.md first.
FROZEN_AGENT_PROMPT_SHA256 = "bd63ce71ce3480dc75b97a453af525f3dc18e0dd48e44d6cf816235dd8ae5e17"


def _calm(path: Path) -> dict:
    return {"free_disk_gb": 50.0, "swap_used_mb": 100.0, "pressure_level": 1}


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory):
    return generated_set(tmp_path_factory.mktemp("agentset"))


def test_core_set_is_the_preregistered_one() -> None:
    assert CORE_SCENARIOS == PREREGISTERED_CORE


def test_core_set_follows_its_selection_rule() -> None:
    scenarios = build_split(Split.DEV)
    truth = {o.scenario_id: t for o, t in scenarios}
    order = sorted(truth)  # the manifest lists IDs sorted
    excluded = set(PILOT_SCENARIOS) | {"sc-2c422896a9"}
    picked, per = [], {}
    for sid in order:
        fault = truth[sid].diagnosis.fault_type.value
        if sid not in excluded and per.get(fault, 0) < 2:
            per[fault] = per.get(fault, 0) + 1
            picked.append(sid)
    assert tuple(picked) == CORE_SCENARIOS
    tiers = [truth[s].tier.value for s in CORE_SCENARIOS]
    assert (tiers.count("standard"), tiers.count("ambiguous"), tiers.count("missing_evidence")) == (5, 2, 3)
    assert sorted(s for s in CORE_SCENARIOS if truth[s].injection) == ["sc-5b55b772de", "sc-5c5b9b9197"]


def test_mock_refuses_core_scenarios_and_the_real_results_directory(tmp_path: Path) -> None:
    with pytest.raises(Refused, match="core"):
        check_mock_target([CORE_SCENARIOS[0]], tmp_path / "out")
    with pytest.raises(Refused, match="eval/agent"):
        check_mock_target(["sc-0000000001"], REAL_RESULTS / "generator-v5" / "mock-scripted")
    assert not (REAL_RESULTS / "generator-v5" / "mock-scripted").exists()


def test_mock_cli_refuses_the_real_dev_manifest_and_the_default_output(generated, tmp_path: Path) -> None:
    from conftest import REPO_ROOT

    real_manifest = REPO_ROOT / "eval" / "manifests"
    assert main(["--backend", "mock", "--manifest-dir", str(real_manifest), "--out-root", str(tmp_path / "never-used"),
                 "--quiet"]) == 2  # the real dev manifest contains the core scenarios
    data_root, manifest_dir, _ = generated
    assert main(["--backend", "mock", "--data-root", str(data_root), "--manifest-dir", str(manifest_dir),
                 "--quiet"]) == 2  # default --out-root is eval/agent/
    assert not any(REAL_RESULTS.glob("**/*.jsonl"))


def test_mock_runs_end_to_end_on_a_generated_set(generated, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, scenarios = generated
    monkeypatch.setattr(agent_run, "system_stats", _calm)
    secret = "sk-test-DO-NOT-LEAK-0123456789"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    assert main(["--backend", "mock", "--data-root", str(data_root), "--manifest-dir", str(manifest_dir),
                 "--out-root", str(tmp_path), "--quiet"]) == 0
    out = tmp_path / "generator-v5" / "mock-scripted"
    summary = json.loads((out / "summary.json").read_text())
    twins = sum(t.injection is not None for _, t in scenarios)
    assert len(summary["runs"]) == len(scenarios) + twins
    assert summary["rule"]["verdict"] == "not applicable (mock backend)"
    assert summary["rule"]["budgets"] == {"agent": 40, "rule_baseline": 52}
    assert all(r["stop_reason"] == "sufficient_evidence" for r in summary["runs"])
    assert all(r["investigated"] for r in summary["runs"])  # the scripted policy is built to satisfy (a)-(f)
    assert "process, not insight" in (out / "summary.md").read_text()
    assert not any(secret in p.read_text() for p in out.rglob("*") if p.is_file())


def test_existing_attempts_are_never_overwritten(generated, tmp_path: Path) -> None:
    data_root, manifest_dir, scenarios = generated
    ids = [o.scenario_id for o, _ in scenarios]
    (tmp_path / "traces").mkdir()
    (tmp_path / "traces" / "01-sc-0000000001.jsonl").write_text("{}\n")
    with pytest.raises(OutputExists):
        run_agent(DemoAgentPolicy(), "mock", "scripted", data_root, tmp_path, ids, manifest_dir, stats=_calm)


def test_an_aborted_batch_writes_a_summary_marked_incomplete(generated, tmp_path: Path) -> None:
    data_root, manifest_dir, scenarios = generated
    ids = [o.scenario_id for o, _ in scenarios]
    readings = iter([_calm(tmp_path)] * 3)
    with pytest.raises(HarnessAbort):
        run_agent(DemoAgentPolicy(), "fake", "scripted", data_root, tmp_path, ids, manifest_dir,
                  stats=lambda p: next(readings, {"free_disk_gb": 5.0, "swap_used_mb": 100.0, "pressure_level": 1}),
                  attempt=2)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["metadata"]["aborted"] and summary["rule"]["complete"] is False
    assert summary["rule"]["verdict"] == "propose_hosted"


def test_agent_prompt_is_frozen() -> None:
    assert prompt_sha256() == FROZEN_AGENT_PROMPT_SHA256, "agent prompt changed: log a revision first"
    assert "untrusted data" in SYSTEM_PROMPT
