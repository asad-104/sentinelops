"""Real (causal) and red-herring changes must be statistically indistinguishable
on author, version format, summary, key and timing."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from sentinelops.models import ConfigChange, Deployment
from sentinelops.simulator import Scenario
from sentinelops.simulator.changes import AUTHORS, CONFIG_KEYS, DEPLOY_SUMMARIES
from sentinelops.simulator.profiles import Tier

VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")


def ks_statistic(a: Sequence[float], b: Sequence[float]) -> float:
    """Two-sample Kolmogorov-Smirnov D statistic."""
    a, b = sorted(a), sorted(b)
    i = j = 0
    d = 0.0
    while i < len(a) and j < len(b):
        x = min(a[i], b[j])
        while i < len(a) and a[i] <= x:
            i += 1
        while j < len(b) and b[j] <= x:
            j += 1
        d = max(d, abs(i / len(a) - j / len(b)))
    return d


def ks_critical(n: int, m: int, alpha: float = 0.01) -> float:
    return math.sqrt(-math.log(alpha / 2) / 2) * math.sqrt((n + m) / (n * m))


def _split(dataset: list[Scenario], kind: str) -> tuple[list, list]:
    """Standard tier only: the ambiguous tier deliberately moves one red herring next to onset."""
    real, decoy = [], []
    for obs, gt in dataset:
        if gt.tier is not Tier.STANDARD:
            continue
        records: tuple[Deployment | ConfigChange, ...] = obs.deployments if kind == "deploy" else obs.config_changes
        for record in records:
            offset = (record.timestamp - obs.window_start).total_seconds() / 60
            (real if record.source_id == gt.trigger_source_id else decoy).append((record, offset))
    return real, decoy


def _minor_bump(d: Deployment) -> bool:
    return d.version.split(".")[1] != d.previous_version.split(".")[1]


def test_deployments_are_alike(large_dataset: list[Scenario]) -> None:
    real, decoy = _split(large_dataset, "deploy")
    assert len(real) == 40 and len(decoy) > 40

    for record, _ in real + decoy:
        assert VERSION_RE.match(record.version) and VERSION_RE.match(record.previous_version)
        assert record.author in AUTHORS and record.summary in DEPLOY_SUMMARIES
    assert len({r.author for r, _ in real}) >= 4, "triggers must not come from a special author"

    d = ks_statistic([t for _, t in real], [t for _, t in decoy])
    assert d < ks_critical(len(real), len(decoy)), f"timing differs (KS D={d:.3f})"

    real_minor = sum(_minor_bump(r) for r, _ in real) / len(real)
    decoy_minor = sum(_minor_bump(r) for r, _ in decoy) / len(decoy)
    assert abs(real_minor - decoy_minor) < 0.2


def test_config_changes_are_alike(large_dataset: list[Scenario]) -> None:
    real, decoy = _split(large_dataset, "config")
    assert len(real) == 40 and len(decoy) > 40

    for record, _ in real + decoy:
        assert record.author in AUTHORS
        assert record.key in CONFIG_KEYS[record.service]
    assert len({r.author for r, _ in real}) >= 4
    assert len({r.key for r, _ in real}) == len({r.key for r, _ in decoy}) == 4

    d = ks_statistic([t for _, t in real], [t for _, t in decoy])
    assert d < ks_critical(len(real), len(decoy)), f"timing differs (KS D={d:.3f})"


def test_ks_helper_detects_a_real_difference() -> None:
    """Guard against a KS implementation that can never fail."""
    a = [i / 100 for i in range(100)]
    b = [0.5 + i / 100 for i in range(100)]
    assert ks_statistic(a, a) == 0
    assert ks_statistic(a, b) > ks_critical(100, 100)
