"""Evaluation harness: the only consumer of ground truth.

Investigators receive a ``CountingToolSet`` built from the scenarios directory
only. Tool calls and wall time are measured here and override whatever the
report claims. The held-out split is refused unless ``final=True``.

Scenarios with injected lines are also run on their injection twin (under
``twins/``, covered by the manifest hash) for the paired injection metric.
Twin runs get their own budget and are not counted in tool calls or latency.

An investigator that raises gets an error row (stop reason from
``InvestigationFailed``, otherwise ``error``) and the run continues. Only
``HarnessAbort`` (e.g. the pilot's disk or memory guard) stops the whole run.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from sentinelops.evaluation.metrics import ScenarioScore, error_score, score_report
from sentinelops.report import InvestigationFailed, InvestigationReport, Investigator
from sentinelops.scenario_files import load_observable
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR, TWINS_DIR, content_sha256, load_manifest
from sentinelops.simulator.ground_truth import GroundTruth
from sentinelops.simulator.profiles import Split
from sentinelops.tools import ToolErrorInfo, ToolResult, ToolSet

DEFAULT_CALL_BUDGET = 200


class HeldOutLocked(Exception):
    """Raised when the held-out split is requested without final=True."""


class DataMismatch(Exception):
    """Raised when on-disk data does not match the frozen manifest."""


class HarnessAbort(Exception):
    """Raised by an investigator wrapper to stop the whole run (not recorded as an error row)."""


class CountingToolSet:
    """Counts every call and refuses calls beyond the budget with a structured error."""

    def __init__(self, tools: ToolSet, budget: int = DEFAULT_CALL_BUDGET) -> None:
        self._tools = tools
        self._budget = budget
        self.calls: list[str] = []

    def call(self, name: str, arguments: Any = None) -> ToolResult:
        tool = name if isinstance(name, str) else repr(name)
        self.calls.append(tool)
        if len(self.calls) > self._budget:
            return ToolResult(tool=tool, ok=False, error=ToolErrorInfo(
                code="budget_exhausted", message=f"call budget of {self._budget} tool calls is exhausted"))
        return self._tools.call(name, arguments)


@dataclass(frozen=True)
class RunResult:
    investigator: str
    split: str
    scores: list[ScenarioScore]
    metadata: dict[str, Any]


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                               text=True, check=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def verify_split(split: Split, data_root: Path, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> dict[str, Any]:
    """The split's frozen manifest, after checking the data on disk matches its hash."""
    manifest = load_manifest(split, manifest_dir)
    if manifest is None:
        raise DataMismatch(f"no manifest for {split.value}")
    if content_sha256(data_root) != manifest["content_sha256"]:
        raise DataMismatch(f"{split.value} data does not match its frozen manifest; regenerate with "
                           f"python -m sentinelops.simulator --split {split.value}")
    return manifest


def _truth(root: Path, scenario_id: str) -> GroundTruth:
    path = root / "ground_truth" / f"{scenario_id}.json"
    if not path.is_file():
        raise DataMismatch(f"missing ground truth for {scenario_id} under {root.name}")
    return GroundTruth.model_validate_json(path.read_text(encoding="utf-8"))


def _investigate(investigator: Investigator, tools: CountingToolSet,
                 scenario_id: str) -> tuple[InvestigationReport | None, str, str | None]:
    """(report, stop reason, error). Any exception except HarnessAbort becomes an error, never a crash."""
    try:
        return investigator.investigate(tools, scenario_id), "sufficient_evidence", None
    except HarnessAbort:
        raise
    except InvestigationFailed as failed:
        return None, failed.stop_reason, failed.message
    except Exception as exc:  # an investigator bug must not stop the evaluation
        return None, "error", f"{type(exc).__name__}: {exc}"


def run_split(investigator: Investigator, split: Split, data_root: Path, *, final: bool = False,
              manifest_dir: Path = DEFAULT_MANIFEST_DIR, budget: int = DEFAULT_CALL_BUDGET,
              scenario_ids: Sequence[str] | None = None) -> RunResult:
    """``scenario_ids`` restricts the run to a subset of the manifest, in the given order."""
    if split is Split.HELDOUT and not final:
        raise HeldOutLocked("the held-out split is locked; it runs only with --final at milestones")
    manifest = verify_split(split, data_root, manifest_dir)
    sha256 = manifest["content_sha256"]
    ids = list(manifest["scenario_ids"] if scenario_ids is None else scenario_ids)
    unknown = [i for i in ids if i not in set(manifest["scenario_ids"])]
    if unknown:
        raise DataMismatch(f"{len(unknown)} requested scenario(s) are not in the {split.value} manifest")

    scores = []
    for scenario_id in ids:
        tools = CountingToolSet(ToolSet.from_directory(data_root / "scenarios", scenario_id), budget)
        started = time.perf_counter()
        report, stop_reason, error = _investigate(investigator, tools, scenario_id)
        elapsed = time.perf_counter() - started
        truth = _truth(data_root, scenario_id)
        twin_report, twin_error = None, None
        if truth.injection is not None:
            twin_root = data_root / TWINS_DIR
            if _truth(twin_root, scenario_id).mechanisms_off != ("injection",):
                raise DataMismatch(f"{scenario_id} has no valid injection twin")
            twin_tools = CountingToolSet(ToolSet.from_directory(twin_root / "scenarios", scenario_id), budget)
            twin_report, twin_stop, twin_error = _investigate(investigator, twin_tools, scenario_id)
            twin_error = None if twin_report is not None else f"{twin_stop}: {twin_error}"
        if report is None:
            score = error_score(scenario_id, truth, stop_reason, error or "", len(tools.calls), elapsed)
        else:
            report = report.model_copy(update={"tool_calls": len(tools.calls), "duration_s": elapsed})
            score = score_report(report, truth, load_observable(data_root / "scenarios" / scenario_id),
                                 twin_report=twin_report)
        if twin_error is not None:
            score = replace(score, twin_error=twin_error[:2000])
        scores.append(score)
    return RunResult(
        investigator=investigator.name,
        split=split.value,
        scores=scores,
        metadata={"generator_version": manifest["generator_version"], "manifest_sha256": sha256,
                  "git_commit": git_commit(), "call_budget": budget, "final": final},
    )
