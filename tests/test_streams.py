"""Independent random streams (generator v5): switching one mechanism off changes only its own records.

For each mechanism a scenario is generated with it on (the tier default) and off. After removing the
mechanism's own records from the "on" version, everything else must be identical, compared by
content because source IDs renumber. Values a mechanism legitimately changes are exempted explicitly.
"""

from dataclasses import replace

import pytest

from sentinelops.models import Metric
from sentinelops.simulator.faults import FaultType
from sentinelops.simulator.generator import Scenario, generate_scenario
from sentinelops.simulator.profiles import DEV_PROFILE, HELDOUT_PROFILE, Mechanisms, Tier

CASES = [(seed, index, fault) for seed in (5, 23) for index, fault in enumerate(FaultType)]
PROFILES = (DEV_PROFILE, HELDOUT_PROFILE)


def _pair(seed: int, index: int, fault: FaultType, tier: Tier, profile, mechanism: str) -> tuple[Scenario, Scenario]:
    on = generate_scenario(seed, index, fault, tier, profile)
    off = generate_scenario(seed, index, fault, tier, profile,
                            replace(Mechanisms.for_tier(tier), **{mechanism: False}))
    return on, off


def _logs(s: Scenario, drop_origins: frozenset[str] = frozenset()) -> list[tuple]:
    origins = {p.source_id: p.origin for p in s.ground_truth.log_provenance}
    return [(r.timestamp, r.service, r.level, r.message) for r in s.observable.logs
            if origins[r.source_id] not in drop_origins]


def _metrics(s: Scenario) -> list[tuple]:
    return [(p.timestamp, p.service, p.metric, p.value) for p in s.observable.metrics]


def _changes(s: Scenario) -> list[tuple]:
    o = s.observable
    return ([(d.timestamp, d.service, d.version, d.author, d.summary) for d in o.deployments]
            + [(c.timestamp, c.service, c.key, c.old_value, c.new_value, c.author) for c in o.config_changes])


def _alert(s: Scenario) -> tuple:
    return s.observable.alert.model_dump(exclude={"source_id"}).items()


def _same_fault(on: Scenario, off: Scenario) -> None:
    a, b = on.ground_truth, off.ground_truth
    assert (a.diagnosis, a.onset, a.affected_services, a.metric_blip) == (b.diagnosis, b.onset, b.affected_services,
                                                                         b.metric_blip)
    assert on.observable.window_start == off.observable.window_start


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.split.value)
@pytest.mark.parametrize("tier", list(Tier))
def test_injection_off_removes_only_injected_lines(profile, tier: Tier) -> None:
    with_injection = 0
    for seed, index, fault in CASES:
        on, off = _pair(seed, index, fault, tier, profile, "injection")
        _same_fault(on, off)
        assert off.ground_truth.injection is None and off.ground_truth.mechanisms_off == ("injection",)
        assert _logs(on, frozenset({"injection"})) == _logs(off)
        assert _metrics(on) == _metrics(off) and _changes(on) == _changes(off)
        assert list(_alert(on)) == list(_alert(off))
        if on.ground_truth.injection is None:
            assert on.observable == off.observable
        else:
            with_injection += 1
            assert len(on.observable.logs) > len(off.observable.logs)
    assert with_injection > 0, "no case exercised an injection"


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.split.value)
def test_overlap_off_removes_only_overlap_symptoms(profile) -> None:
    for seed, index, fault in CASES:
        on, off = _pair(seed, index, fault, Tier.AMBIGUOUS, profile, "overlap")
        _same_fault(on, off)
        assert off.ground_truth.overlap_log_source_ids == () and on.ground_truth.overlap_log_source_ids
        assert _logs(on, frozenset({"overlap"})) == _logs(off)
        assert _changes(on) == _changes(off)
        assert on.ground_truth.decoy_source_id == off.ground_truth.decoy_source_id
        # Overlap adds metric deltas to the root only (memory for bad deployments, pool for memory leaks).
        # Those series, and therefore which alert fires, may legitimately differ; nothing else may.
        root = on.ground_truth.diagnosis.service
        exempt = {(root, Metric.MEMORY_PCT), (root, Metric.DB_POOL_UTILIZATION)}
        assert ([m for m in _metrics(on) if (m[1], m[2]) not in exempt]
                == [m for m in _metrics(off) if (m[1], m[2]) not in exempt])


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.split.value)
def test_decoy_off_moves_only_the_decoy(profile) -> None:
    for seed, index, fault in CASES:
        on, off = _pair(seed, index, fault, Tier.AMBIGUOUS, profile, "decoy")
        _same_fault(on, off)
        assert on.ground_truth.decoy_source_id is not None and off.ground_truth.decoy_source_id is None
        # Change logs follow their change (and deploy versions re-chain), so they are compared via the records.
        assert _logs(on, frozenset({"change"})) == _logs(off, frozenset({"change"}))
        assert _metrics(on) == _metrics(off) and list(_alert(on)) == list(_alert(off))
        o_on, o_off = on.observable, off.observable
        # Ignoring versions, exactly one change record (the decoy) differs.
        keyed = [lambda o: {(d.timestamp, d.service, d.author, d.summary) for d in o.deployments},
                 lambda o: {(c.timestamp, c.service, c.key, c.old_value, c.new_value, c.author)
                            for c in o.config_changes}]
        differing = sum(len(k(o_on) - k(o_off)) for k in keyed)
        assert differing == 1
        assert ((len(o_on.deployments), len(o_on.config_changes))
                == (len(o_off.deployments), len(o_off.config_changes)))


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.split.value)
def test_gap_off_restores_exactly_the_gapped_records(profile) -> None:
    kinds = set()
    for seed, index, fault in CASES:
        on, off = _pair(seed, index, fault, Tier.MISSING_EVIDENCE, profile, "gap")
        _same_fault(on, off)
        gap = on.ground_truth.missing_evidence
        assert gap is not None and off.ground_truth.missing_evidence is None
        kinds.add(gap.kind)

        def outside(record: tuple) -> bool:
            return not (record[1] is gap.service and gap.start <= record[0] < gap.end)

        assert _changes(on) == _changes(off) and list(_alert(on)) == list(_alert(off))
        if gap.kind == "log_gap":
            assert _logs(on) == [r for r in _logs(off) if outside(r)] != _logs(off)
            assert _metrics(on) == _metrics(off)
        else:
            assert _metrics(on) == [m for m in _metrics(off) if outside(m)] != _metrics(off)
            assert _logs(on) == _logs(off)
    assert kinds == {"log_gap", "metric_gap"}, "both gap kinds must be exercised"


def test_default_mechanisms_match_the_tier() -> None:
    for tier in Tier:
        assert generate_scenario(5, 0, FaultType.MEMORY_LEAK, tier) == generate_scenario(
            5, 0, FaultType.MEMORY_LEAK, tier, mechanisms=Mechanisms.for_tier(tier))
