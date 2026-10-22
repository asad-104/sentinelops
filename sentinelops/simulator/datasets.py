"""Frozen dev and held-out datasets.

Each split has its own seed, its own generation profile (see ``profiles``) and
a balanced (fault type x tier) schedule. A manifest records the split's
scenario IDs and a SHA-256 of every file written, so any change to the
generator that alters the data is detected.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from sentinelops.scenario_files import dump_json, write_observable
from sentinelops.simulator.faults import FaultType
from sentinelops.simulator.generator import GENERATOR_VERSION, Scenario, generate_scenario
from sentinelops.simulator.profiles import PROFILES, Split, Tier

SPLIT_SEEDS: dict[Split, int] = {Split.DEV: 1001, Split.HELDOUT: 2002}

# Scenarios per fault type in each tier.
TIER_COUNTS: dict[Split, dict[Tier, int]] = {
    Split.DEV: {Tier.STANDARD: 4, Tier.AMBIGUOUS: 2, Tier.MISSING_EVIDENCE: 2},
    Split.HELDOUT: {Tier.STANDARD: 6, Tier.AMBIGUOUS: 3, Tier.MISSING_EVIDENCE: 3},
}

DEFAULT_MANIFEST_DIR = Path("eval/manifests")


def split_schedule(split: Split) -> list[tuple[FaultType, Tier]]:
    cells = [(fault, tier) for fault in FaultType for tier, k in TIER_COUNTS[split].items() for _ in range(k)]
    random.Random(f"sentinelops:{GENERATOR_VERSION}:{split}:{SPLIT_SEEDS[split]}:schedule").shuffle(cells)
    return cells


def build_split(split: Split) -> list[Scenario]:
    profile, seed = PROFILES[split], SPLIT_SEEDS[split]
    return [generate_scenario(seed, i, fault, tier, profile) for i, (fault, tier) in enumerate(split_schedule(split))]


def write_split(scenarios: list[Scenario], root: Path) -> None:
    """Observable files to ``root/scenarios/<id>/``, ground truth to ``root/ground_truth/<id>.json``."""
    (root / "ground_truth").mkdir(parents=True, exist_ok=True)
    for observable, truth in scenarios:
        write_observable(observable, root / "scenarios" / observable.scenario_id)
        dump_json(root / "ground_truth" / f"{truth.scenario_id}.json", truth.model_dump(mode="json"))


def content_sha256(root: Path) -> str:
    """Hash of every file under ``root/scenarios`` and ``root/ground_truth``: sorted paths and bytes."""
    digest = hashlib.sha256()
    files = [p for sub in ("scenarios", "ground_truth") for p in (root / sub).rglob("*") if p.is_file()]
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def build_manifest(split: Split, scenarios: list[Scenario], sha256: str) -> dict[str, Any]:
    return {
        "split": split.value,
        "generator_version": GENERATOR_VERSION,
        "seed": SPLIT_SEEDS[split],
        "n": len(scenarios),
        "scenario_ids": sorted(o.scenario_id for o, _ in scenarios),
        "content_sha256": sha256,
    }


def manifest_path(split: Split, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> Path:
    return manifest_dir / f"{split.value}.json"


def load_manifest(split: Split, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> dict[str, Any] | None:
    path = manifest_path(split, manifest_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
