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


def _files(out: Path) -> dict[str, bytes]:
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()}


def test_progress_display_changes_no_output_file(dev, tmp_path: Path) -> None:
    """Traces, summary and run log are byte-identical with progress on and off (fixed clock and stats)."""
    import io

    from sentinelops.llm.prompt import prompt_sha256
    from test_llm_schemas import FROZEN_PROMPT_SHA256

    data_root, manifest_dir, _ = dev
    stream = io.StringIO()
    outputs = {}
    for flag in (False, True):
        out = tmp_path / ("on" if flag else "off")
        run_pilot(DemoPolicyClient(), "mock", "scripted", data_root, out, manifest_dir, stats=_calm,
                  clock=lambda: 0.0, progress=flag, progress_stream=stream)
        outputs[flag] = _files(out)
    assert outputs[True] == outputs[False] and len(outputs[True]) == 10  # 7 traces, 2 summaries, run log
    assert prompt_sha256() == FROZEN_PROMPT_SHA256
    lines = stream.getvalue().splitlines()
    assert lines[0] == "run 1/7 sc-06b280fbed | turn 1 | tool calls 1/30 | 0 s | swap 1000 MB | free disk 50.0 GB"
    assert "run 7/7 sc-4141664f86 done: sufficient_evidence" in lines[-1]
    assert sum("done:" in line for line in lines) == 7


def test_quiet_turns_progress_off(dev, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                  capsys: pytest.CaptureFixture) -> None:
    data_root, manifest_dir, _ = dev
    monkeypatch.setattr(pilot, "system_stats", _calm)
    args = ["--backend", "mock", "--data-root", str(data_root), "--manifest-dir", str(manifest_dir)]
    assert main([*args, "--out-root", str(tmp_path / "a"), "--quiet"]) == 0
    assert capsys.readouterr().err == ""
    assert main([*args, "--out-root", str(tmp_path / "b")]) == 0
    err = capsys.readouterr().err
    assert "run 1/7 sc-06b280fbed | turn 1 |" in err and err.count("done:") == 7


class UnloadingMock(DemoPolicyClient):
    """Mock with a model that is 'loaded' while chatting and freed by unload()."""

    def __init__(self) -> None:
        self.loaded, self.unloads = False, 0

    def chat(self, messages, tools):
        self.loaded = True
        return super().chat(messages, tools)

    def unload(self):
        self.loaded, self.unloads = False, self.unloads + 1
        return None


def test_model_is_unloaded_after_every_run_and_the_guard_sees_the_post_unload_reading(dev, tmp_path: Path) -> None:
    data_root, manifest_dir, _ = dev
    client = UnloadingMock()

    def stats(path):  # swap is high only while the model is loaded: a check before unloading would abort
        return {"free_disk_gb": 50.0, "swap_used_mb": 3500.0 if client.loaded else 100.0, "pressure_level": 1}

    summary = run_pilot(client, "fake", "scripted", data_root, tmp_path, manifest_dir, stats=stats)
    assert client.unloads == 7 and summary["metadata"]["unload_between_runs"] is True
    log = [json.loads(line) for line in (tmp_path / "run_log.jsonl").read_text().splitlines()]
    events = [e["event"] for e in log]
    assert events == ["batch_start"] + ["run_start", "run_end", "unload"] * 7
    assert all(e["swap_used_mb"] == 3500.0 for e in log if e["event"] == "run_end")
    assert all(e["swap_used_mb"] == 100.0 and e["error"] is None for e in log if e["event"] == "unload")
    assert summary["rule"]["complete"] is True


def test_a_single_run_that_grows_swap_too_much_still_trips_the_guard(dev, tmp_path: Path) -> None:
    data_root, manifest_dir, _ = dev
    client = UnloadingMock()
    readings = iter([100.0, 100.0, 2500.0, 2400.0, 2400.0])  # baseline, check 1, run_end, unload, check 2

    def stats(path):
        return {"free_disk_gb": 50.0, "swap_used_mb": next(readings), "pressure_level": 1}

    with pytest.raises(HarnessAbort, match="swap grew"):
        run_pilot(client, "fake", "scripted", data_root, tmp_path, manifest_dir, stats=stats)


def test_an_aborted_batch_still_writes_a_summary_marked_incomplete(dev, tmp_path: Path) -> None:
    data_root, manifest_dir, _ = dev
    readings = iter([_calm(tmp_path)] * 5 + [{"free_disk_gb": 50.0, "swap_used_mb": 9000.0, "pressure_level": 1}])
    with pytest.raises(HarnessAbort):
        run_pilot(DemoPolicyClient(), "fake", "scripted", data_root, tmp_path, manifest_dir,
                  stats=lambda path: next(readings, {"free_disk_gb": 50.0, "swap_used_mb": 9000.0,
                                                     "pressure_level": 1}), attempt=2)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["metadata"]["aborted"].startswith("swap grew") and summary["metadata"]["attempt"] == 2
    assert 0 < len(summary["runs"]) < 7
    assert summary["rule"]["complete"] is False and summary["rule"]["verdict"] == "propose_hosted"
    assert "Aborted batch (attempt 2)" in (tmp_path / "summary.md").read_text()


def test_an_existing_attempt_is_never_overwritten(dev, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, _ = dev
    monkeypatch.setattr(pilot, "system_stats", _calm)
    out = tmp_path / "generator-v5" / "mock-scripted"
    (out / "traces").mkdir(parents=True)
    old = out / "traces" / "01-sc-06b280fbed.jsonl"
    old.write_text('{"event": "start"}\n')
    with pytest.raises(pilot.OutputExists):
        run_pilot(DemoPolicyClient(), "mock", "scripted", data_root, out, manifest_dir)
    args = ["--backend", "mock", "--data-root", str(data_root), "--out-root", str(tmp_path),
            "--manifest-dir", str(manifest_dir), "--quiet"]
    assert main(args) == 2 and old.read_text() == '{"event": "start"}\n'
    assert main([*args, "--attempt", "2"]) == 0
    assert (tmp_path / "generator-v5" / "mock-scripted-attempt2" / "summary.json").is_file()


def test_context_overflow_heuristic() -> None:
    from sentinelops.evaluation.pilot import context_overflow

    growing = context_overflow([1645, 2728, 5592], 8192)
    assert growing == {"prompt_drops": 0, "max_prompt_tokens": 5592, "likely_context_overflow": False}
    attempt1_run3 = context_overflow([1645, 2449, 4436, 5676, 7046, 4098, 8095, 6834], 8192)
    assert attempt1_run3["prompt_drops"] == 2 and attempt1_run3["likely_context_overflow"] is True
    assert context_overflow([1000, 8100], 8192)["likely_context_overflow"] is True  # reached ~num_ctx
    assert context_overflow([None, 10, 10], None)["likely_context_overflow"] is False  # mock
