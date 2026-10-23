"""Scenario sets generated in a temporary directory for M4 mock runs (never the core scenarios)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from sentinelops.scenario_files import dump_json
from sentinelops.simulator import FaultType, generate_scenario
from sentinelops.simulator.datasets import build_manifest, content_sha256, manifest_path, write_split
from sentinelops.simulator.profiles import Mechanisms, Split, Tier

CELLS = ((FaultType.MEMORY_LEAK, Tier.STANDARD), (FaultType.CONFIG_ERROR, Tier.AMBIGUOUS),
         (FaultType.BAD_DEPLOYMENT, Tier.MISSING_EVIDENCE))


def generated_set(root: Path, seed: int = 4242) -> tuple[Path, Path, list]:
    """Write a small dev-shaped split (with twins) and its own manifest; returns (data_root, manifest_dir, scenarios)."""
    data_root, manifest_dir = root / "dev", root / "manifests"
    scenarios, twins = [], []
    for i, (fault, tier) in enumerate(CELLS):
        scenario = generate_scenario(seed, i, fault, tier)
        scenarios.append(scenario)
        if scenario.ground_truth.injection is not None:
            twins.append(generate_scenario(seed, i, fault, tier,
                                           mechanisms=replace(Mechanisms.for_tier(tier), injection=False)))
    write_split(scenarios, data_root, twins)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    dump_json(manifest_path(Split.DEV, manifest_dir), build_manifest(Split.DEV, scenarios, content_sha256(data_root)))
    return data_root, manifest_dir, scenarios
