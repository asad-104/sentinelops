"""M3 pilot CLI with the mock backend: fixed set, dev only, guards, summary, no secrets. No model, no network."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sentinelops.evaluation import pilot
from sentinelops.evaluation.harness import HarnessAbort
from sentinelops.evaluation.pilot import (
    CORE_SCENARIOS,
    PILOT_SCENARIOS,
    PROBE_SCENARIO,
    apply_rule,
    main,
    run_pilot,
    system_stats,
)
from sentinelops.llm.mock import DemoPolicyClient
from sentinelops.scenario_files import dump_json
from sentinelops.simulator.datasets import (
    build_injection_twins,
    build_manifest,
    build_split,
    content_sha256,
    manifest_path,
    write_split,
)
from sentinelops.simulator.profiles import Split

# Pre-registered in docs/PROGRESS.md on 2026-10-23; duplicated here on purpose.
PREREGISTERED_CORE = ("sc-06b280fbed", "sc-1499febf6f", "sc-203fe8a4ca", "sc-2d438d4575", "sc-32aaf79bfd")
PREREGISTERED_PROBE = "sc-4141664f86"


@pytest.fixture(scope="module")
def dev(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, list]:
    root = tmp_path_factory.mktemp("pilot")
    data_root, manifest_dir = root / "dev", root / "manifests"
    scenarios = build_split(Split.DEV)
    write_split(scenarios, data_root, build_injection_twins(Split.DEV, scenarios))
    manifest_dir.mkdir()
    dump_json(manifest_path(Split.DEV, manifest_dir), build_manifest(Split.DEV, scenarios, content_sha256(data_root)))
    return data_root, manifest_dir, scenarios


def _calm(path: Path) -> dict:
    return {"free_disk_gb": 50.0, "swap_used_mb": 1000.0, "pressure_level": 1}


def test_pilot_set_is_the_preregistered_one() -> None:
    assert CORE_SCENARIOS == PREREGISTERED_CORE and PROBE_SCENARIO == PREREGISTERED_PROBE
    assert PILOT_SCENARIOS == (*PREREGISTERED_CORE, PREREGISTERED_PROBE)


def test_pilot_set_follows_its_selection_rule(dev) -> None:
    data_root, manifest_dir, scenarios = dev
    truth = {o.scenario_id: t for o, t in scenarios}
    order = json.loads(manifest_path(Split.DEV, manifest_dir).read_text())["scenario_ids"]
    first_per_fault: dict[str, str] = {}
    for sid in order:
        first_per_fault.setdefault(truth[sid].diagnosis.fault_type.value, sid)
    assert tuple(first_per_fault.values()) == CORE_SCENARIOS
    assert next(sid for sid in order if truth[sid].injection is not None) == PROBE_SCENARIO
    assert (data_root / "twins" / "scenarios" / PROBE_SCENARIO).is_dir()
    assert not any(truth[sid].tier.value == "ambiguous" for sid in PILOT_SCENARIOS)  # stated in every write-up


def test_mock_pilot_runs_end_to_end(dev, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, _ = dev
    monkeypatch.setattr(pilot, "system_stats", _calm)
    assert main(["--backend", "mock", "--data-root", str(data_root), "--out-root", str(tmp_path),
                 "--manifest-dir", str(manifest_dir)]) == 0
    out = tmp_path / "generator-v5" / "mock-scripted"
    traces = sorted((out / "traces").glob("*.jsonl"))
    assert [p.name[3:-6] for p in traces] == [*PILOT_SCENARIOS, PROBE_SCENARIO]
    summary = json.loads((out / "summary.json").read_text())
    runs = summary["runs"]
    assert [r["variant"] for r in runs] == ["original"] * 6 + ["twin"]
    assert all(r["stop_reason"] == "sufficient_evidence" and r["report_valid"] for r in runs)
    assert all(r["valid_calls"] == r["model_calls"] - 1 for r in runs)  # the mock's one invalid call per run
    assert summary["rule"]["verdict"] == "not applicable (mock backend)"
    assert summary["metadata"]["prompt_sha256"] and summary["metadata"]["bounds"]["max_tool_calls"] == 30
    md = (out / "summary.md").read_text()
    assert "Mock backend" in md and "ambiguous tier" in md and "can hide source IDs" in md
    log = [json.loads(line) for line in (out / "run_log.jsonl").read_text().splitlines()]
    assert [e["event"] for e in log][:3] == ["batch_start", "run_start", "run_end"]
    assert sum(e["event"] == "run_start" for e in log) == 7


def test_pilot_has_no_split_argument() -> None:
    with pytest.raises(SystemExit):
        main(["--backend", "mock", "--split", "heldout"])


def test_pilot_refuses_data_that_differs_from_the_manifest(tmp_path: Path) -> None:
    assert main(["--backend", "mock", "--data-root", str(tmp_path / "none"), "--out-root", str(tmp_path),
                 "--manifest-dir", str(tmp_path / "none")]) == 2


@pytest.mark.parametrize("stats, reason", [
    ({"free_disk_gb": 9.5, "swap_used_mb": 1000.0, "pressure_level": 1}, "free disk"),
    ({"free_disk_gb": 50.0, "swap_used_mb": 3100.0, "pressure_level": 1}, "swap grew"),
    ({"free_disk_gb": 50.0, "swap_used_mb": 1000.0, "pressure_level": 4}, "critical"),
], ids=["disk", "swap", "pressure"])
def test_guards_abort_the_batch(dev, tmp_path: Path, stats: dict, reason: str) -> None:
    data_root, manifest_dir, _ = dev
    readings = iter([_calm(tmp_path), stats])
    with pytest.raises(HarnessAbort, match=reason):
        run_pilot(DemoPolicyClient(), "mock", "scripted", data_root, tmp_path, manifest_dir,
                  stats=lambda path: next(readings))
    log = (tmp_path / "run_log.jsonl").read_text()
    assert '"event": "abort"' in log and not list((tmp_path / "traces").glob("*.jsonl"))


def test_no_secret_can_reach_pilot_outputs(dev, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, _ = dev
    secret = "sk-test-DO-NOT-LEAK-0123456789"
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SENTINELOPS_API_KEY", "OLLAMA_API_KEY"):
        monkeypatch.setenv(var, secret)
    monkeypatch.setattr(pilot, "system_stats", _calm)
    assert main(["--backend", "mock", "--data-root", str(data_root), "--out-root", str(tmp_path),
                 "--manifest-dir", str(manifest_dir)]) == 0
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files and not any(secret in p.read_text() for p in files)


def _row(**kw) -> dict:
    base = {"role": "core", "model_calls": 10, "valid_calls": 9, "stop_reason": "sufficient_evidence",
            "report_valid": True, "cited": 10, "cited_existing": 10, "elapsed_s": 300.0}
    return base | kw


def test_decision_rule_boundaries() -> None:
    assert apply_rule([_row()] * 5)["verdict"] == "local_feasible"
    assert apply_rule([_row(valid_calls=8)] * 5)["verdict"] == "local_feasible"  # exactly 80%
    assert apply_rule([_row(valid_calls=7)] * 5)["verdict"] == "in_between"  # 70%
    assert apply_rule([_row(valid_calls=5)] * 5)["verdict"] == "propose_hosted"  # 50% < 60%
    three_good = [_row()] * 3 + [_row(report_valid=False, stop_reason="error")] * 2
    assert apply_rule(three_good)["verdict"] == "in_between"
    two_good = [_row()] * 2 + [_row(report_valid=False, stop_reason="timeout")] * 3
    assert apply_rule(two_good)["verdict"] == "propose_hosted"
    assert apply_rule([_row(cited_existing=8)] * 5)["verdict"] == "in_between"  # 80% real citations
    assert apply_rule([_row(cited=0, cited_existing=0)] * 5)["verdict"] == "in_between"  # no citations at all
    assert apply_rule([_row(elapsed_s=900.0)] * 5)["verdict"] == "in_between"
    assert apply_rule([_row(elapsed_s=1300.0)] * 5)["verdict"] == "propose_hosted"
    assert apply_rule([_row()] * 5 + [_row(role="probe", valid_calls=0)] * 2)["verdict"] == "local_feasible"


def test_system_stats_reads_only_sysctl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        out = {"vm.swapusage": "total = 2048.00M  used = 1194.00M  free = 854.00M  (encrypted)",
               "kern.memorystatus_vm_pressure_level": "1"}[cmd[-1]]
        return subprocess.CompletedProcess(cmd, 0, stdout=out + "\n", stderr="")

    monkeypatch.setattr(pilot.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(pilot.subprocess, "run", fake_run)
    stats = system_stats(tmp_path)
    assert stats["swap_used_mb"] == 1194.0 and stats["pressure_level"] == 1 and stats["free_disk_gb"] > 0
    assert all(cmd[0] == "sysctl" for cmd in commands)  # memory_pressure (which applies pressure) is never run


def test_cli_uses_the_live_stats_and_refuses_on_low_disk(dev, tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, _ = dev
    monkeypatch.setattr(pilot, "system_stats", lambda path: {"free_disk_gb": 3.0, "swap_used_mb": None,
                                                             "pressure_level": None})
    assert main(["--backend", "mock", "--data-root", str(data_root), "--out-root", str(tmp_path),
                 "--manifest-dir", str(manifest_dir)]) == 2


def test_smoke_runs_one_non_pilot_scenario_and_is_never_scored(dev, tmp_path: Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, _ = dev
    monkeypatch.setattr(pilot, "system_stats", _calm)
    order = json.loads(manifest_path(Split.DEV, manifest_dir).read_text())["scenario_ids"]
    smoke = next(i for i in order if i not in PILOT_SCENARIOS)
    assert main(["--backend", "mock", "--smoke", smoke, "--data-root", str(data_root), "--out-root",
                 str(tmp_path), "--manifest-dir", str(manifest_dir)]) == 0
    summary = json.loads((tmp_path / "generator-v5" / "smoke-mock-scripted" / "summary.json").read_text())
    assert [r["scenario_id"] for r in summary["runs"]] == [smoke] and summary["metadata"]["smoke"] is True
    assert summary["rule"]["verdict"] == "not applicable (smoke run)"
    with pytest.raises(SystemExit):
        main(["--backend", "mock", "--smoke", PILOT_SCENARIOS[0]])

