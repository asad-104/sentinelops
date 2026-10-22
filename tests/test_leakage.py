"""Ground truth must not leak into anything an investigator can see."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sentinelops.simulator import FaultType, Scenario
from sentinelops.tools import ToolError, ToolSet

from conftest import REPO_ROOT

# Words that name or hint at a cause rather than describe a symptom.
CAUSE_TERMS = (
    *(f.value for f in FaultType),
    *(f.value.replace("_", " ") for f in FaultType),
    "deploy", "release", "rollout", "version", "config", "setting",
    "leak", "exhaust", "pool", "connection", "oom",
    "root cause", "caused by", "because", "due to",
)
GROUND_TRUTH_ONLY_TERMS = ("variant_id", "template_id", "origin", "trigger", "red_herring", "fault",
                           "ground_truth", "onset", "provenance", "blip", "injection", "diagnosis")


def test_alert_summary_describes_symptoms_only(large_dataset: list[Scenario]) -> None:
    for obs, _ in large_dataset:
        summary = obs.alert.summary.lower()
        leaked = [term for term in CAUSE_TERMS if term in summary]
        assert not leaked, f"{obs.scenario_id} alert summary names a cause: {leaked}"


def test_observable_data_contains_no_ground_truth(large_dataset: list[Scenario]) -> None:
    for obs, _ in large_dataset:
        text = obs.model_dump_json().lower()
        leaked = [term for term in GROUND_TRUTH_ONLY_TERMS if term in text]
        assert not leaked, f"{obs.scenario_id} observable data contains {leaked}"


def test_scenario_id_does_not_reveal_seed_or_index(small_dataset: list[Scenario]) -> None:
    for obs, gt in small_dataset:
        assert obs.scenario_id.startswith("sc-")
        assert f"-{gt.seed}-" not in obs.scenario_id


def _imported_modules(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("path", [
    *sorted((REPO_ROOT / "sentinelops" / "tools").glob("*.py")),
    REPO_ROOT / "sentinelops" / "models.py",
    REPO_ROOT / "sentinelops" / "scenario_files.py",
], ids=lambda p: p.name)
def test_tool_side_modules_never_import_the_simulator(path: Path) -> None:
    assert not [m for m in _imported_modules(path) if m.startswith("sentinelops.simulator")]


@pytest.mark.parametrize("bad_id", ["../ground_truth", "sc-../../x", "SC-0123456789", "sc-0123", ""])
def test_toolset_rejects_paths_outside_scenarios(scenarios_root: Path, bad_id: str) -> None:
    with pytest.raises(ToolError):
        ToolSet.from_directory(scenarios_root, bad_id)
