"""JSONL run traces: one file per investigation, one event per line.

Traces hold what the investigator saw and did (model turns, tool calls with
their validity and status, the text shown to the model, the final report or
validation error). They hold no ground truth and no credentials: the loop never
reads environment variables, and clients expose only ``describe()``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunTrace:
    """Events in memory, and appended to ``path`` if one is given."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.events: list[dict[str, Any]] = []

    def event(self, kind: str, **fields: Any) -> None:
        record = {"event": kind, **fields}
        self.events.append(record)
        if self.path is None:
            return
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, sort_keys=True, default=str) + "\n")


class TraceWriter:
    """Numbers runs in the order they start (an injection twin gets the next number)."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.count = 0

    def start(self, scenario_id: str) -> RunTrace:
        self.count += 1
        path = self.directory / f"{self.count:02d}-{scenario_id}.jsonl"
        path.unlink(missing_ok=True)
        return RunTrace(path)


def read_trace(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
