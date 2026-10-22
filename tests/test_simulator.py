from __future__ import annotations

import string
from collections import Counter

from sentinelops.models import Metric, Service
from sentinelops.simulator import FaultType, Scenario, generate_dataset, generate_scenario
from sentinelops.simulator.generator import alert_threshold
from sentinelops.simulator.profiles import DEV_PROFILE
from sentinelops.simulator.templates import TEMPLATES


def test_same_seed_is_deterministic() -> None:
    a = generate_scenario(3, 0, FaultType.CONFIG_ERROR)
    b = generate_scenario(3, 0, FaultType.CONFIG_ERROR)
    assert a.observable.model_dump_json() == b.observable.model_dump_json()
    assert a.ground_truth.model_dump_json() == b.ground_truth.model_dump_json()


def test_different_seeds_differ() -> None:
    a = generate_scenario(3, 0, FaultType.CONFIG_ERROR)
    b = generate_scenario(4, 0, FaultType.CONFIG_ERROR)
    assert a.observable.logs != b.observable.logs


def test_fault_types_are_balanced() -> None:
    counts = Counter(gt.diagnosis.fault_type for _, gt in generate_dataset(seed=2, n=10))
    assert counts == {fault: 2 for fault in FaultType}


def test_source_ids_are_unique_and_follow_timestamp_order(small_dataset: list[Scenario]) -> None:
    for obs, _ in small_dataset:
        for records in (obs.logs, obs.metrics, obs.deployments, obs.config_changes):
            ids = [r.source_id for r in records]
            assert len(ids) == len(set(ids))
            assert ids == sorted(ids), "IDs must be numbered in order"
            timestamps = [r.timestamp for r in records]
            assert timestamps == sorted(timestamps), "ID order must equal timestamp order"


def test_fault_logs_are_not_clustered_by_id(large_dataset: list[Scenario]) -> None:
    """Fault records must be interleaved with background records, not a contiguous ID block."""
    for obs, gt in large_dataset:
        position = {log.source_id: i for i, log in enumerate(obs.logs)}
        fault_positions = sorted(position[sid] for sid in gt.fault_log_source_ids)
        assert fault_positions, f"{gt.scenario_id} has no fault logs"
        span = fault_positions[-1] - fault_positions[0] + 1
        other_in_span = span - len(fault_positions)
        assert other_in_span / span > 0.2, f"{gt.scenario_id}: fault logs clustered by ID"
        # Faults start after the window opens, so pre-incident background logs come first.
        assert fault_positions[0] > 0


def test_ground_truth_is_consistent_with_observable(large_dataset: list[Scenario]) -> None:
    for obs, gt in large_dataset:
        change_ids = {r.source_id for r in (*obs.deployments, *obs.config_changes)}
        assert gt.diagnosis.service in gt.affected_services
        assert obs.window_start <= gt.onset < obs.alert.timestamp < obs.window_end
        assert set(gt.red_herring_source_ids) | ({gt.trigger_source_id} - {None}) == change_ids
        if gt.diagnosis.fault_type is FaultType.BAD_DEPLOYMENT:
            trigger = next(d for d in obs.deployments if d.source_id == gt.trigger_source_id)
        elif gt.diagnosis.fault_type is FaultType.CONFIG_ERROR:
            trigger = next(c for c in obs.config_changes if c.source_id == gt.trigger_source_id)
        else:
            assert gt.trigger_source_id is None
            continue
        assert trigger.service is gt.diagnosis.service
        assert trigger.timestamp < gt.onset


def test_alert_reflects_a_real_breach(large_dataset: list[Scenario]) -> None:
    for obs, gt in large_dataset:
        alert = obs.alert
        assert alert.service in gt.affected_services
        assert alert.observed_value > alert.threshold == alert_threshold(alert.service, alert.metric)


def test_alert_service_is_not_always_the_root_cause(large_dataset: list[Scenario]) -> None:
    on_root = sum(obs.alert.service is gt.diagnosis.service for obs, gt in large_dataset)
    assert 0.1 < on_root / len(large_dataset) < 0.7


def test_there_is_no_database_service(large_dataset: list[Scenario]) -> None:
    obs = large_dataset[0].observable
    assert {d.caller for d in obs.dependencies} | {d.callee for d in obs.dependencies} == {
        Service.GATEWAY, Service.AUTH, Service.ORDERS, Service.PAYMENTS}
    pool_services = {p.service for p in obs.metrics if p.metric is Metric.DB_POOL_UTILIZATION}
    assert pool_services == {Service.AUTH, Service.ORDERS, Service.PAYMENTS}


def test_pool_faults_saturate_the_pool_metric(large_dataset: list[Scenario]) -> None:
    for obs, gt in large_dataset:
        if gt.diagnosis.fault_type is FaultType.CONNECTION_POOL_EXHAUSTION:
            peak = max(p.value for p in obs.metrics
                       if p.service is gt.diagnosis.service and p.metric is Metric.DB_POOL_UTILIZATION)
            assert peak > 95


def test_metric_values_are_in_range(small_dataset: list[Scenario]) -> None:
    for obs, _ in small_dataset:
        for point in obs.metrics:
            assert point.value >= 0
            if point.metric is Metric.ERROR_RATE:
                assert point.value <= 1
            if point.metric in (Metric.CPU_PCT, Metric.MEMORY_PCT):
                assert point.value <= 100


def test_every_template_has_interchangeable_variants() -> None:
    formatter = string.Formatter()
    for template in TEMPLATES.values():
        assert len(template.variants) == 4, template.template_id
        fields = [{name for _, name, _, _ in formatter.parse(v) if name} for v in template.variants]
        assert all(f == fields[0] for f in fields), f"{template.template_id} variants use different fields"


def test_variants_are_actually_used(large_dataset: list[Scenario]) -> None:
    used: dict[str, set[int]] = {}
    for _, gt in large_dataset:
        for p in gt.log_provenance:
            used.setdefault(p.template_id, set()).add(p.variant_id)
    for template_id, variants in used.items():
        assert variants == set(DEV_PROFILE.variants), template_id
