"""Dev/held-out split integrity.

Held-out hygiene: held-out data is generated only into a tmp directory, and
every held-out assertion compares a precomputed bool, count or hash with a
short message, so a failure cannot print held-out records.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from pathlib import Path

import pytest

from sentinelops.simulator import FaultType, Scenario
from sentinelops.simulator.datasets import (
    TIER_COUNTS,
    build_split,
    content_sha256,
    load_manifest,
    write_split,
)
from sentinelops.simulator.profiles import DEV_PROFILE, HELDOUT_PROFILE, Split

from conftest import REPO_ROOT

MANIFEST_DIR = REPO_ROOT / "eval" / "manifests"


@pytest.fixture(scope="module")
def splits(tmp_path_factory: pytest.TempPathFactory) -> dict[Split, tuple[list[Scenario], Path]]:
    result = {}
    for split in Split:
        root = tmp_path_factory.mktemp(split.value)
        scenarios = build_split(split)
        write_split(scenarios, root)
        result[split] = (scenarios, root)
    return result


def _trigger_lags(scenarios: list[Scenario]) -> list[timedelta]:
    lags = []
    for obs, gt in scenarios:
        if gt.trigger_source_id is not None:
            trigger = next(r for r in (*obs.deployments, *obs.config_changes) if r.source_id == gt.trigger_source_id)
            lags.append(gt.onset - trigger.timestamp)
    return lags


@pytest.mark.parametrize("split", list(Split))
def test_split_matches_frozen_manifest(splits: dict, split: Split) -> None:
    scenarios, root = splits[split]
    manifest = load_manifest(split, MANIFEST_DIR)
    assert manifest is not None, f"run: python -m sentinelops.simulator --split {split.value} --freeze"
    hash_matches = manifest["content_sha256"] == content_sha256(root)
    ids_match = manifest["scenario_ids"] == sorted(o.scenario_id for o, _ in scenarios)
    assert hash_matches, f"{split.value} content differs from the frozen manifest (see freeze rule in PROGRESS.md)"
    assert ids_match, f"{split.value} scenario IDs differ from the frozen manifest"
    assert manifest["n"] == len(scenarios)


@pytest.mark.parametrize("split", list(Split))
def test_split_records_profile_and_has_balanced_cells(splits: dict, split: Split) -> None:
    scenarios, _ = splits[split]
    correct_split = all(gt.split is split for _, gt in scenarios)
    cells = Counter((gt.diagnosis.fault_type, gt.tier) for _, gt in scenarios)
    expected = Counter({(f, t): k for f in FaultType for t, k in TIER_COUNTS[split].items()})
    balanced = cells == expected
    assert correct_split, "ground truth records the wrong split"
    assert balanced, "unbalanced fault x tier cells"


def test_scenario_ids_are_disjoint(splits: dict) -> None:
    dev = {o.scenario_id for o, _ in splits[Split.DEV][0]}
    heldout = {o.scenario_id for o, _ in splits[Split.HELDOUT][0]}
    overlap = len(dev & heldout)
    assert overlap == 0, f"{overlap} scenario IDs appear in both splits"


def test_dev_never_uses_the_heldout_phrasing(splits: dict) -> None:
    unseen = set(HELDOUT_PROFILE.variants) - set(DEV_PROFILE.variants)
    leaks = sum(p.variant_id in unseen for _, gt in splits[Split.DEV][0] for p in gt.log_provenance)
    assert leaks == 0


def test_every_heldout_scenario_uses_the_unseen_phrasing(splits: dict) -> None:
    unseen = set(HELDOUT_PROFILE.variants) - set(DEV_PROFILE.variants)
    without = sum(not any(p.variant_id in unseen for p in gt.log_provenance) for _, gt in splits[Split.HELDOUT][0])
    assert without == 0, f"{without} held-out scenarios never use the unseen phrasing"


def test_heldout_has_longer_trigger_lags_than_dev(splits: dict) -> None:
    dev_cap = timedelta(minutes=DEV_PROFILE.trigger_lag_min[1], seconds=1)
    dev_over = sum(lag > dev_cap for lag in _trigger_lags(splits[Split.DEV][0]))
    heldout_over = sum(lag > dev_cap for lag in _trigger_lags(splits[Split.HELDOUT][0]))
    assert dev_over == 0, f"{dev_over} dev lags exceed the dev range"
    assert heldout_over > 0, "held-out has no lag beyond the dev range"


def test_regeneration_is_byte_identical(splits: dict, tmp_path: Path) -> None:
    _, root = splits[Split.DEV]
    write_split(build_split(Split.DEV), tmp_path)
    assert content_sha256(tmp_path) == content_sha256(root)


@pytest.mark.parametrize("split", list(Split))
def test_every_frozen_scenario_is_solvable(splits: dict, split: Split) -> None:
    from test_tiers import _log_channel, _metric_channel

    unsolvable = sum(not (_log_channel(obs, gt) or _metric_channel(obs, gt)) for obs, gt in splits[split][0])
    assert unsolvable == 0, f"{unsolvable} {split.value} scenarios have no independent evidence path"
