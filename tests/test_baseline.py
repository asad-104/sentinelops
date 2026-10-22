"""Baselines and floors on a small dev-profile set in a tmp dir (never the real splits)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sentinelops.baselines import INVESTIGATORS
from sentinelops.evaluation.harness import CountingToolSet
from sentinelops.report import InvestigationReport
from sentinelops.scenario_files import write_observable
from sentinelops.simulator import FaultType, Scenario, generate_scenario
from sentinelops.simulator.profiles import Tier
from sentinelops.tools import ToolSet

from conftest import REPO_ROOT


@pytest.fixture(scope="module")
def small_set(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[Scenario]]:
    root = tmp_path_factory.mktemp("baseline") / "scenarios"
    scenarios = [generate_scenario(500 + i, 0, fault, tier)
                 for i, (fault, tier) in enumerate((f, t) for f in FaultType for t in Tier)]
    for obs, _ in scenarios:
        write_observable(obs, root / obs.scenario_id)
    return root, scenarios


def _run(name: str, root: Path, scenario_id: str) -> tuple[InvestigationReport, CountingToolSet]:
    tools = CountingToolSet(ToolSet.from_directory(root, scenario_id))
    return INVESTIGATORS[name].investigate(tools, scenario_id), tools


@pytest.mark.parametrize("name", list(INVESTIGATORS))
def test_reports_are_valid_and_cite_only_existing_records(small_set: tuple[Path, list[Scenario]], name: str) -> None:
    root, scenarios = small_set
    for obs, _ in scenarios:
        report, tools = _run(name, root, obs.scenario_id)
        assert report.scenario_id == obs.scenario_id and report.investigator == name
        assert 1 <= len(report.hypotheses) <= 3
        existing = {obs.alert.source_id} | {r.source_id for rs in (obs.logs, obs.metrics, obs.deployments,
                                                                   obs.config_changes) for r in rs}
        cited = [i for h in report.hypotheses for i in h.supporting_evidence]
        assert cited and set(cited) <= existing
        assert report.executed_actions == ()
        assert set(tools.calls) <= set(ToolSet.from_directory(root, obs.scenario_id).tool_names)


@pytest.mark.parametrize("name", list(INVESTIGATORS))
def test_investigators_are_deterministic(small_set: tuple[Path, list[Scenario]], name: str) -> None:
    root, scenarios = small_set
    for obs, _ in scenarios[:5]:
        first, _ = _run(name, root, obs.scenario_id)
        second, _ = _run(name, root, obs.scenario_id)
        assert first == second


def test_rule_baseline_stays_within_the_call_budget(small_set: tuple[Path, list[Scenario]]) -> None:
    root, scenarios = small_set
    for obs, _ in scenarios:
        _, tools = _run("rule_based", root, obs.scenario_id)
        assert len(tools.calls) <= 80, len(tools.calls)


def test_keyword_only_uses_no_metrics_or_changes(small_set: tuple[Path, list[Scenario]]) -> None:
    root, scenarios = small_set
    _, tools = _run("keyword_only", root, scenarios[0][0].scenario_id)
    assert "list_deployments" not in tools.calls and "list_config_changes" not in tools.calls
    assert tools.calls.count("get_metrics") == 1  # only the window-start lookup


def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


@pytest.mark.parametrize("path", [REPO_ROOT / "sentinelops" / "report.py",
                                  *sorted((REPO_ROOT / "sentinelops" / "baselines").glob("*.py"))],
                         ids=lambda p: p.name)
def test_investigator_side_never_imports_the_simulator(path: Path) -> None:
    assert not [m for m in _imports(path) if m.startswith("sentinelops.simulator") or m.startswith("sentinelops.evaluation")]
