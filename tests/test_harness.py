from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinelops.evaluation.__main__ import main
from sentinelops.evaluation.harness import CountingToolSet, DataMismatch, HeldOutLocked, run_split
from sentinelops.models import FaultType
from sentinelops.report import Hypothesis, InvestigationReport
from sentinelops.scenario_files import dump_json
from sentinelops.simulator import generate_scenario
from sentinelops.simulator.datasets import build_manifest, content_sha256, manifest_path, write_split
from sentinelops.simulator.profiles import Mechanisms, Split, Tier
from sentinelops.tools import ToolSet


FAULTS = (FaultType.BAD_DEPLOYMENT, FaultType.MEMORY_LEAK, FaultType.CONFIG_ERROR)
INJECTION_MARKERS = ("instruction", "Assistant", "NOTE TO AI")  # one phrase from each payload template


@pytest.fixture()
def tmp_dev(tmp_path: Path) -> tuple[Path, Path]:
    """A 3-scenario fake dev split, with injection twins, and its own manifest."""
    scenarios = [generate_scenario(700, i, fault, Tier.STANDARD) for i, fault in enumerate(FAULTS)]
    twins = [generate_scenario(700, i, fault, Tier.STANDARD, mechanisms=Mechanisms(injection=False))
             for i, fault in enumerate(FAULTS) if scenarios[i].ground_truth.injection is not None]
    assert 0 < len(twins) < len(scenarios), "fixture needs scenarios with and without an injection"
    data_root, manifest_dir = tmp_path / "dev", tmp_path / "manifests"
    write_split(scenarios, data_root, twins)
    manifest_dir.mkdir()
    dump_json(manifest_path(Split.DEV, manifest_dir), build_manifest(Split.DEV, scenarios, content_sha256(data_root)))
    return data_root, manifest_dir


class SelfReportingLiar:
    """Makes two tool calls but claims 999 and a long duration."""

    name = "liar"

    def investigate(self, tools, scenario_id: str) -> InvestigationReport:
        alert = tools.call("get_alert").items[0]
        tools.call("get_dependencies")
        return InvestigationReport(
            scenario_id=scenario_id, investigator=self.name, summary="s", tool_calls=999, duration_s=999.0,
            stop_reason="sufficient_evidence",
            hypotheses=(Hypothesis(rank=1, service=alert.service, fault_type=FaultType.BAD_DEPLOYMENT,
                                   confidence="low", supporting_evidence=(alert.source_id,), rationale="t"),))


class Gullible:
    """Answers differently whenever an injected instruction is in the logs."""

    name = "gullible"

    def investigate(self, tools, scenario_id: str) -> InvestigationReport:
        alert = tools.call("get_alert").items[0]
        seen = any(tools.call("search_logs", {"contains": m}).total_matches for m in INJECTION_MARKERS)
        fault = FaultType.CERTIFICATE_EXPIRY if seen else FaultType.BAD_DEPLOYMENT
        return InvestigationReport(
            scenario_id=scenario_id, investigator=self.name, summary="s", tool_calls=0, duration_s=0.0,
            stop_reason="sufficient_evidence",
            hypotheses=(Hypothesis(rank=1, service=alert.service, fault_type=fault, confidence="low",
                                   supporting_evidence=(alert.source_id,), rationale="t"),))


def test_injection_twins_are_run_and_paired(tmp_dev: tuple[Path, Path]) -> None:
    data_root, manifest_dir = tmp_dev
    gullible = run_split(Gullible(), Split.DEV, data_root, manifest_dir=manifest_dir)
    for s in gullible.scores:
        assert s.injection_changed is (True if s.injection_present else None)
    steady = run_split(SelfReportingLiar(), Split.DEV, data_root, manifest_dir=manifest_dir)
    for s in steady.scores:
        assert s.injection_changed is (False if s.injection_present else None)
    # Twin runs are not counted in the original's tool calls.
    assert all(s.tool_calls == 2 for s in steady.scores)


def test_missing_twin_is_refused(tmp_dev: tuple[Path, Path]) -> None:
    data_root, manifest_dir = tmp_dev
    for path in (data_root / "twins" / "ground_truth").iterdir():
        path.unlink()
    manifest = json.loads(manifest_path(Split.DEV, manifest_dir).read_text())
    manifest["content_sha256"] = content_sha256(data_root)
    dump_json(manifest_path(Split.DEV, manifest_dir), manifest)
    with pytest.raises(DataMismatch):
        run_split(SelfReportingLiar(), Split.DEV, data_root, manifest_dir=manifest_dir)


def test_heldout_is_refused_without_final_before_touching_files(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(HeldOutLocked):
        run_split(SelfReportingLiar(), Split.HELDOUT, missing, manifest_dir=missing)
    assert main(["--split", "heldout", "--data-root", str(missing), "--manifest-dir", str(missing),
                 "--out-dir", str(missing)]) == 2
    assert not missing.exists()


def test_measured_calls_and_time_override_self_reports(tmp_dev: tuple[Path, Path]) -> None:
    data_root, manifest_dir = tmp_dev
    result = run_split(SelfReportingLiar(), Split.DEV, data_root, manifest_dir=manifest_dir)
    assert len(result.scores) == 3
    assert all(s.tool_calls == 2 and s.duration_s < 5 for s in result.scores)
    assert result.metadata["final"] is False and result.metadata["manifest_sha256"] == content_sha256(data_root)


def test_data_that_differs_from_the_manifest_is_refused(tmp_dev: tuple[Path, Path]) -> None:
    data_root, manifest_dir = tmp_dev
    alert_file = next((data_root / "scenarios").iterdir()) / "alert.json"
    alert_file.write_text(alert_file.read_text().replace("ALR-001", "ALR-002"))
    with pytest.raises(DataMismatch):
        run_split(SelfReportingLiar(), Split.DEV, data_root, manifest_dir=manifest_dir)


def test_call_budget_returns_structured_errors(tmp_dev: tuple[Path, Path]) -> None:
    data_root, manifest_dir = tmp_dev
    scenario_id = json.loads(manifest_path(Split.DEV, manifest_dir).read_text())["scenario_ids"][0]
    tools = CountingToolSet(ToolSet.from_directory(data_root / "scenarios", scenario_id), budget=2)
    assert tools.call("get_alert").ok and tools.call("get_alert").ok
    third = tools.call("get_alert")
    assert not third.ok and third.error is not None and third.error.code == "budget_exhausted"
    assert len(tools.calls) == 3


def test_cli_writes_result_files(tmp_dev: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    data_root, manifest_dir = tmp_dev
    out = tmp_path / "results"
    assert main(["--split", "dev", "--investigator", "all", "--data-root", str(data_root),
                 "--manifest-dir", str(manifest_dir), "--out-dir", str(out)]) == 0
    result = json.loads((out / "dev-rule_based.json").read_text())
    assert set(result) == {"investigator", "split", "metadata", "summary", "scenarios"}
    assert set(result["summary"]) == {"overall", "per_tier", "per_fault_descriptive", "per_fault_note"}
    assert len(result["scenarios"]) == 3
    summary_md = (out / "dev-summary.md").read_text()
    for name in ("rule_based", "alert_service", "latest_change", "keyword_only", "random (analytical"):
        assert name in summary_md
    assert "# dev results" in capsys.readouterr().out
