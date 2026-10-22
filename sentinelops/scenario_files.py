"""Read and write a scenario's observable files.

Output is deterministic: keys are sorted, separators are fixed and newlines
are always ``\\n``, so the same scenario always produces the same bytes.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sentinelops.models import ScenarioObservable

MANIFEST_FILE = "manifest.json"
ALERT_FILE = "alert.json"
LOGS_FILE = "logs.jsonl"
METRICS_FILE = "metrics.jsonl"
DEPLOYMENTS_FILE = "deployments.json"
CONFIG_CHANGES_FILE = "config_changes.json"
DEPENDENCIES_FILE = "dependencies.json"

OBSERVABLE_FILES = (
    MANIFEST_FILE,
    ALERT_FILE,
    LOGS_FILE,
    METRICS_FILE,
    DEPLOYMENTS_FILE,
    CONFIG_CHANGES_FILE,
    DEPENDENCIES_FILE,
)


def dump_json(path: Path, data: Any) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def _dump_jsonl(path: Path, rows: Iterable[Any]) -> None:
    lines = [json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for row in rows]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8", newline="\n")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Any]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_observable(observable: ScenarioObservable, scenario_dir: Path) -> None:
    scenario_dir.mkdir(parents=True, exist_ok=True)
    data = observable.model_dump(mode="json")
    manifest = {
        key: data[key] for key in ("schema_version", "scenario_id", "window_start", "window_end")
    }
    dump_json(scenario_dir / MANIFEST_FILE, manifest)
    dump_json(scenario_dir / ALERT_FILE, data["alert"])
    _dump_jsonl(scenario_dir / LOGS_FILE, data["logs"])
    _dump_jsonl(scenario_dir / METRICS_FILE, data["metrics"])
    dump_json(scenario_dir / DEPLOYMENTS_FILE, data["deployments"])
    dump_json(scenario_dir / CONFIG_CHANGES_FILE, data["config_changes"])
    dump_json(scenario_dir / DEPENDENCIES_FILE, data["dependencies"])


def load_observable(scenario_dir: Path) -> ScenarioObservable:
    missing = [name for name in OBSERVABLE_FILES if not (scenario_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"scenario directory {scenario_dir} is missing {', '.join(missing)}")
    return ScenarioObservable.model_validate(
        {
            **_load_json(scenario_dir / MANIFEST_FILE),
            "alert": _load_json(scenario_dir / ALERT_FILE),
            "logs": _load_jsonl(scenario_dir / LOGS_FILE),
            "metrics": _load_jsonl(scenario_dir / METRICS_FILE),
            "deployments": _load_json(scenario_dir / DEPLOYMENTS_FILE),
            "config_changes": _load_json(scenario_dir / CONFIG_CHANGES_FILE),
            "dependencies": _load_json(scenario_dir / DEPENDENCIES_FILE),
        }
    )
