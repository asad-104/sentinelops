"""Dev-only data access for the viewer.

Guards every path so the viewer can never read held-out data. Imports neither
Streamlit (so it is testable without it) nor ``sentinelops.simulator`` (which
owns ground truth); the dev answer key is read as plain JSON.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, NamedTuple

from sentinelops.models import SCENARIO_ID_PATTERN
from sentinelops.tools import ToolSet

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS_ROOT = REPO_ROOT / "data" / "dev" / "scenarios"
DEFAULT_MANIFEST = REPO_ROOT / "eval" / "manifests" / "dev.json"

# Test-only overrides. The held-out guard applies to them too.
ROOT_ENV = "SENTINELOPS_VIEWER_ROOT"
MANIFEST_ENV = "SENTINELOPS_VIEWER_MANIFEST"


class ViewerDataError(Exception):
    """A path or ID the viewer refuses to read."""


def _refuse_heldout(path: Path) -> None:
    if any("heldout" in part.lower() for part in path.parts):
        raise ViewerDataError(f"the viewer never reads held-out data: {path}")


def dev_scenarios_root(raw: str | None = None) -> Path:
    raw = raw if raw is not None else os.environ.get(ROOT_ENV)
    root = Path(raw).resolve() if raw else DEFAULT_SCENARIOS_ROOT.resolve()
    _refuse_heldout(root)
    if root.name != "scenarios":
        raise ViewerDataError(f"expected a .../scenarios directory, got {root}")
    return root


def dev_scenario_ids(root: Path, manifest: Path | None = None) -> list[str]:
    """IDs from the dev manifest that also exist on disk."""
    manifest = manifest or Path(os.environ.get(MANIFEST_ENV) or DEFAULT_MANIFEST).resolve()
    _refuse_heldout(manifest)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("split") != "dev":
        raise ViewerDataError(f"{manifest} is not the dev manifest")
    return [sid for sid in data["scenario_ids"] if (root / sid).is_dir()]


def open_toolset(root: Path, scenario_id: str) -> ToolSet:
    return ToolSet.from_directory(root, scenario_id)


RESULTS_ROOT = REPO_ROOT / "eval" / "results"
RESULTS_ENV = "SENTINELOPS_VIEWER_RESULTS"


def results_root() -> Path:
    root = Path(os.environ.get(RESULTS_ENV) or RESULTS_ROOT).resolve()
    _refuse_heldout(root)
    return root


def dev_result_versions(root: Path) -> list[str]:
    """Generator versions with dev results, newest first, e.g. ["generator-v4", "generator-v3"]."""
    versions = [d.name for d in root.glob("generator-v*")
                if re.fullmatch(r"generator-v\d+", d.name) and any(d.glob("dev-*.json"))]
    return sorted(versions, key=lambda v: int(v.removeprefix("generator-v")), reverse=True)


class DevResults(NamedTuple):
    investigators: dict[str, dict[str, Any]]  # investigator name -> summary
    skipped: list[str]  # dev-*.json files that are not investigator results (e.g. dev-ablation.json)


def _version_dir(root: Path, version: str) -> Path:
    if not re.fullmatch(r"generator-v\d+", version):
        raise ViewerDataError(f"invalid results version {version!r}")
    return root / version


def _load_dev_json(path: Path) -> Any:
    _refuse_heldout(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("split") != "dev":
        raise ViewerDataError(f"{path.name} is not a dev result")
    return data


def dev_results(root: Path, version: str) -> DevResults:
    """Investigator summaries from dev result files. Files of any other shape are skipped and named."""
    investigators, skipped = {}, []
    for path in sorted(_version_dir(root, version).glob("dev-*.json")):
        try:
            data = _load_dev_json(path)
        except json.JSONDecodeError:
            skipped.append(path.name)
            continue
        summary = data.get("summary")
        if (isinstance(data.get("investigator"), str) and isinstance(summary, dict)
                and isinstance(summary.get("overall"), dict) and isinstance(summary.get("per_tier"), dict)):
            investigators[data["investigator"]] = summary
        else:
            skipped.append(path.name)
    return DevResults(investigators, skipped)


def dev_ablation(root: Path, version: str) -> dict[str, Any] | None:
    """The paired-ablation file for a version, as written by the evaluation (None if absent or malformed)."""
    path = _version_dir(root, version) / "dev-ablation.json"
    if not path.is_file():
        return None
    try:
        data = _load_dev_json(path)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data.get("ablation"), dict) else None


def dev_tier_counts(root: Path, scenario_ids: list[str]) -> list[dict[str, Any]]:
    """Rows of (tier, fault_type, scenarios) for the dev split on disk."""
    counts: dict[tuple[str, str], int] = {}
    for scenario_id in scenario_ids:
        truth = dev_ground_truth(root, scenario_id)
        key = (truth["tier"], truth["fault_type"])
        counts[key] = counts.get(key, 0) + 1
    return [{"tier": t, "fault_type": f, "scenarios": n} for (t, f), n in sorted(counts.items())]


def dev_ground_truth(root: Path, scenario_id: str) -> dict[str, Any]:
    """The four answer fields for one dev scenario, read as plain JSON."""
    if not re.fullmatch(SCENARIO_ID_PATTERN, scenario_id):
        raise ViewerDataError(f"invalid scenario id {scenario_id!r}")
    truth_dir = (root.parent / "ground_truth").resolve()
    _refuse_heldout(truth_dir)
    path = (truth_dir / f"{scenario_id}.json").resolve()
    if not path.is_relative_to(truth_dir):
        raise ViewerDataError(f"{scenario_id!r} escapes the ground-truth directory")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "fault_type": data["diagnosis"]["fault_type"],
            "root_service": data["diagnosis"]["service"],
            "tier": data["tier"],
            "onset": data["onset"],
        }
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ViewerDataError(f"{path.name} is not a ground-truth file ({type(exc).__name__})") from exc
