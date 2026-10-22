"""Difficulty tiers: ambiguous decoys and missing evidence, without leaking either."""

from __future__ import annotations

from datetime import timedelta

import pytest

from sentinelops.simulator import FaultType, Scenario, generate_scenario
from sentinelops.simulator.profiles import DECOY_LEAD_MIN, Tier

PAIRS = [(seed, fault) for seed in range(30, 36) for fault in FaultType]


@pytest.fixture(scope="module")
def by_tier() -> dict[Tier, list[Scenario]]:
    return {tier: [generate_scenario(seed, 0, fault, tier) for seed, fault in PAIRS] for tier in Tier}


def test_tier_is_recorded(by_tier: dict[Tier, list[Scenario]]) -> None:
    for tier, scenarios in by_tier.items():
        assert all(gt.tier is tier for _, gt in scenarios)


def test_ambiguous_decoy_sits_just_before_onset(by_tier: dict[Tier, list[Scenario]]) -> None:
    for obs, gt in by_tier[Tier.AMBIGUOUS]:
        assert gt.decoy_source_id is not None and gt.decoy_source_id != gt.trigger_source_id
        assert gt.decoy_source_id in gt.red_herring_source_ids
        decoy = next(r for r in (*obs.deployments, *obs.config_changes) if r.source_id == gt.decoy_source_id)
        lead = gt.onset - decoy.timestamp
        assert timedelta(minutes=DECOY_LEAD_MIN[0]) - timedelta(seconds=1) <= lead
        assert lead <= timedelta(minutes=DECOY_LEAD_MIN[1]) + timedelta(seconds=1)
        if decoy.source_id.startswith("DPL"):
            assert decoy.service in gt.affected_services


def test_ambiguous_has_fewer_fault_logs(by_tier: dict[Tier, list[Scenario]]) -> None:
    standard = sum(len(gt.fault_log_source_ids) for _, gt in by_tier[Tier.STANDARD])
    ambiguous = sum(len(gt.fault_log_source_ids) for _, gt in by_tier[Tier.AMBIGUOUS])
    assert ambiguous < 0.7 * standard


def test_other_tiers_have_no_decoy_or_gap(by_tier: dict[Tier, list[Scenario]]) -> None:
    for _, gt in by_tier[Tier.STANDARD]:
        assert gt.decoy_source_id is None and gt.missing_evidence is None
    for _, gt in by_tier[Tier.AMBIGUOUS]:
        assert gt.missing_evidence is None
    for _, gt in by_tier[Tier.MISSING_EVIDENCE]:
        assert gt.decoy_source_id is None


def test_missing_evidence_removes_root_data_in_the_gap(by_tier: dict[Tier, list[Scenario]]) -> None:
    kinds = set()
    for obs, gt in by_tier[Tier.MISSING_EVIDENCE]:
        gap = gt.missing_evidence
        assert gap is not None and gap.service is gt.diagnosis.service
        kinds.add(gap.kind)
        records = obs.logs if gap.kind == "log_gap" else obs.metrics
        in_gap = [r for r in records if gap.start <= r.timestamp < gap.end]
        assert in_gap, "other services must still report during the gap"
        assert not any(r.service is gap.service for r in in_gap)
        assert any(r.service is gap.service for r in records), "root has data outside the gap"
    assert kinds == {"log_gap", "metric_gap"}


@pytest.mark.parametrize("tier", list(Tier))
def test_ids_stay_contiguous_and_time_ordered(by_tier: dict[Tier, list[Scenario]], tier: Tier) -> None:
    for obs, _ in by_tier[tier]:
        for prefix, records in (("LOG", obs.logs), ("MET", obs.metrics)):
            assert [r.source_id for r in records] == [f"{prefix}-{i:05d}" for i in range(1, len(records) + 1)]
            assert [r.timestamp for r in records] == sorted(r.timestamp for r in records)


def test_tiers_leave_no_marker_in_observable_data(by_tier: dict[Tier, list[Scenario]]) -> None:
    for tier in (Tier.AMBIGUOUS, Tier.MISSING_EVIDENCE):
        for obs, _ in by_tier[tier]:
            text = obs.model_dump_json().lower()
            assert not [t for t in ("decoy", "ambiguous", "missing_evidence", "log_gap", "metric_gap", "tier")
                        if t in text]
