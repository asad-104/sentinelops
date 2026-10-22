"""Difficulty tiers: ambiguous decoys and missing evidence, without leaking either."""

from __future__ import annotations

from datetime import timedelta

import pytest

from sentinelops.models import Metric
from sentinelops.simulator import FaultType, Scenario, generate_scenario
from sentinelops.simulator.generator import alert_threshold
from sentinelops.simulator.profiles import DECOY_LEAD_MIN, Tier
from sentinelops.simulator.topology import BASELINES

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


def test_ambiguous_adds_overlap_symptoms_without_thinning_true_ones(by_tier: dict[Tier, list[Scenario]]) -> None:
    assert all(gt.overlap_log_source_ids for _, gt in by_tier[Tier.AMBIGUOUS])
    assert not any(gt.overlap_log_source_ids for t in (Tier.STANDARD, Tier.MISSING_EVIDENCE) for _, gt in by_tier[t])
    standard = sum(len(gt.fault_log_source_ids) for _, gt in by_tier[Tier.STANDARD])
    ambiguous = sum(len(gt.fault_log_source_ids) for _, gt in by_tier[Tier.AMBIGUOUS])
    assert ambiguous > 0.7 * standard, "v4 must not thin the true symptoms"


def test_overlap_logs_use_another_faults_vocabulary(by_tier: dict[Tier, list[Scenario]]) -> None:
    templates = {p.template_id for _, gt in by_tier[Tier.AMBIGUOUS] for p in gt.log_provenance if p.origin == "overlap"}
    assert templates == {"client.timeout", "upstream.connection_error"}


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
        assert gap.end == obs.window_end, "v4 gaps run to the window end"
    assert kinds == {"log_gap", "metric_gap"}


def test_missing_evidence_never_removes_both_logs_and_metrics(by_tier: dict[Tier, list[Scenario]]) -> None:
    for obs, gt in by_tier[Tier.MISSING_EVIDENCE]:
        root = gt.diagnosis.service
        logs_after = any(r.service is root and r.timestamp >= gt.onset for r in obs.logs)
        metrics_after = any(p.service is root and p.timestamp >= gt.onset for p in obs.metrics)
        assert logs_after != metrics_after, "exactly one of the root's logs or metrics is removed"


PRIMARY_TEMPLATES = {
    FaultType.BAD_DEPLOYMENT: {"app.unhandled_exception"},
    FaultType.CONFIG_ERROR: {"client.timeout", "db.pool_wait", "cache.miss", "ratelimit.reject"},
    FaultType.CONNECTION_POOL_EXHAUSTION: {"db.pool_wait", "db.long_query"},
    FaultType.MEMORY_LEAK: {"process.gc_pause", "process.oom_killed"},
    FaultType.CERTIFICATE_EXPIRY: {"tls.handshake_failed", "tls.cert_expired"},
}


def _metric_channel(obs, gt) -> bool:
    root, fault = gt.diagnosis.service, gt.diagnosis.fault_type
    after = [p for p in obs.metrics if p.service is root and p.timestamp >= gt.onset]
    peak = {m: max((p.value for p in after if p.metric is m), default=None) for m in Metric}
    low_rate = min((p.value for p in after if p.metric is Metric.REQUEST_RATE), default=None)
    error = peak[Metric.ERROR_RATE] is not None and peak[Metric.ERROR_RATE] > alert_threshold(root, Metric.ERROR_RATE)
    slow = peak[Metric.LATENCY_P95_MS] is not None and peak[Metric.LATENCY_P95_MS] > 2 * BASELINES[root][Metric.LATENCY_P95_MS]
    pool = (peak[Metric.DB_POOL_UTILIZATION] or 0) > 95
    if fault is FaultType.BAD_DEPLOYMENT:
        return error
    if fault is FaultType.CONFIG_ERROR:
        return error or slow or pool
    if fault is FaultType.CONNECTION_POOL_EXHAUSTION:
        return pool
    if fault is FaultType.MEMORY_LEAK:
        return (peak[Metric.MEMORY_PCT] or 0) > 85
    return low_rate is not None and low_rate < 0.5 * BASELINES[root][Metric.REQUEST_RATE]


def _log_channel(obs, gt) -> bool:
    """A primary symptom log on the root, or (certificate expiry) a caller's TLS error naming the root."""
    by_id = {log.source_id: log for log in obs.logs}
    primary = PRIMARY_TEMPLATES[gt.diagnosis.fault_type]
    for p in gt.log_provenance:
        if p.origin != "fault" or p.template_id not in primary:
            continue
        log = by_id[p.source_id]
        if log.service is gt.diagnosis.service or gt.diagnosis.service.value in log.message:
            return True
    return False


@pytest.mark.parametrize("tier", list(Tier))
def test_every_scenario_keeps_an_independent_evidence_path(by_tier: dict[Tier, list[Scenario]], tier: Tier) -> None:
    for obs, gt in by_tier[tier]:
        change_ids = {r.source_id for r in (*obs.deployments, *obs.config_changes)}
        assert gt.trigger_source_id is None or gt.trigger_source_id in change_ids
        assert _log_channel(obs, gt) or _metric_channel(obs, gt), f"{gt.scenario_id} ({tier}) is unsolvable"


def test_solvability_check_can_fail(by_tier: dict[Tier, list[Scenario]]) -> None:
    """Guard: remove both channels from a scenario and the check must reject it."""
    obs, gt = by_tier[Tier.STANDARD][0]
    root = gt.diagnosis.service
    gutted = obs.model_copy(update={
        "logs": tuple(r for r in obs.logs if r.service is not root and root.value not in r.message),
        "metrics": tuple(p for p in obs.metrics if p.service is not root)})
    assert not (_log_channel(gutted, gt.model_copy(update={"log_provenance": tuple(
        p for p in gt.log_provenance if p.source_id in {r.source_id for r in gutted.logs})})) or _metric_channel(gutted, gt))


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
