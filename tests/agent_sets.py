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


def fresh_shaped_set(root: Path, n_injected: int = 2, seed: int = 4242) -> tuple[Path, Path, list]:
    """A tiny split written as m5fresh (data root named m5fresh, manifest m5fresh.json) with injected scenarios and
    their twins, plus one scenario without injection."""
    data_root, manifest_dir = root / "m5fresh", root / "manifests"
    scenarios, twins, plain = [], [], None
    cells = [(f, t) for f in (FaultType.MEMORY_LEAK, FaultType.CONFIG_ERROR, FaultType.BAD_DEPLOYMENT)
             for t in (Tier.STANDARD, Tier.AMBIGUOUS)]
    for i in range(40):
        fault, tier = cells[i % len(cells)]
        s = generate_scenario(seed, i, fault, tier)
        if s.ground_truth.injection is not None and sum(x.ground_truth.injection is not None for x in scenarios) < n_injected:
            scenarios.append(s)
            twins.append(generate_scenario(seed, i, fault, tier,
                                           mechanisms=replace(Mechanisms.for_tier(tier), injection=False)))
        elif s.ground_truth.injection is None and plain is None:
            plain = s
            scenarios.append(s)
        if plain is not None and len(twins) == n_injected:
            break
    write_split(scenarios, data_root, twins)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    dump_json(manifest_path(Split.M5FRESH, manifest_dir),
              build_manifest(Split.M5FRESH, scenarios, content_sha256(data_root)))
    return data_root, manifest_dir, scenarios
