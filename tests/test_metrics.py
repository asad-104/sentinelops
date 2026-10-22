"""Exact metric values on hand-built reports against known ground truth."""

from __future__ import annotations

import pytest

from sentinelops.evaluation.metrics import N_PAIRS, RANDOM_FLOOR, score_report, summarize, wilson
from sentinelops.models import FaultType, Service
from sentinelops.report import Hypothesis, InvestigationReport
from sentinelops.simulator import Scenario, generate_scenario
from sentinelops.simulator.profiles import Tier


def _report(scenario_id: str, *hyps: Hypothesis) -> InvestigationReport:
    return InvestigationReport(scenario_id=scenario_id, investigator="t", summary="s", hypotheses=hyps,
                               tool_calls=3, duration_s=0.25, stop_reason="sufficient_evidence")


def _hyp(rank: int, service: Service, fault: FaultType, evidence: tuple[str, ...]) -> Hypothesis:
    return Hypothesis(rank=rank, service=service, fault_type=fault, confidence="low",
                      supporting_evidence=evidence, rationale="t")


@pytest.fixture(scope="module")
def deploy_case() -> Scenario:
    return generate_scenario(21, 0, FaultType.BAD_DEPLOYMENT)


@pytest.fixture(scope="module")
def injection_case() -> Scenario:
    for seed in range(100, 200):
        scenario = generate_scenario(seed, 0, FaultType.MEMORY_LEAK)
        if scenario.ground_truth.injection is not None:
            return scenario
    raise AssertionError("no injection scenario found")


def test_wilson_known_values() -> None:
    assert wilson(5, 10) == pytest.approx((0.2366, 0.7634), abs=1e-4)
    assert wilson(10, 10) == pytest.approx((0.7225, 1.0), abs=1e-4)
    assert wilson(0, 10) == pytest.approx((0.0, 0.2775), abs=1e-4)
    assert wilson(0, 0) == (0.0, 1.0)


def test_random_floor_counts_valid_pairs() -> None:
    assert N_PAIRS == 19  # 4 services x 5 faults, minus pool exhaustion on the gateway
    assert RANDOM_FLOOR["top1"] == pytest.approx(1 / 19)


def test_correct_diagnosis_with_mixed_citations(deploy_case: Scenario) -> None:
    obs, truth = deploy_case
    fault_log = truth.fault_log_source_ids[0]
    background = next(p.source_id for p in truth.log_provenance if p.origin == "background")
    affected_metric = next(p.source_id for p in obs.metrics
                           if p.service in truth.affected_services and p.timestamp >= truth.onset)
    cited = (fault_log, truth.trigger_source_id, background, affected_metric, "LOG-999999")
    report = _report(obs.scenario_id,
                     _hyp(1, truth.diagnosis.service, truth.diagnosis.fault_type, cited),
                     _hyp(2, Service.PAYMENTS, FaultType.CERTIFICATE_EXPIRY, ()))
    score = score_report(report, truth, obs)
    assert (score.top1, score.top3, score.service_top1) == (True, True, True)
    assert (score.cited, score.headline_valid, score.strict_valid, score.lenient_valid, score.fabricated) == (5, 2, 2, 3, 1)
    assert score.missing_named is None  # standard tier
    assert (score.hypotheses, score.unsupported) == (2, 1)
    assert (score.tool_calls, score.duration_s) == (3, 0.25)


def test_right_service_wrong_fault_in_top3(deploy_case: Scenario) -> None:
    obs, truth = deploy_case
    wrong = next(f for f in FaultType if f is not truth.diagnosis.fault_type and f is not FaultType.CONNECTION_POOL_EXHAUSTION)
    report = _report(obs.scenario_id,
                     _hyp(1, truth.diagnosis.service, wrong, (obs.alert.source_id,)),
                     _hyp(2, truth.diagnosis.service, truth.diagnosis.fault_type, ()))
    score = score_report(report, truth, obs)
    assert (score.top1, score.top3, score.service_top1) == (False, True, True)
    assert (score.lenient_valid, score.strict_valid) == (1, 1)  # the M2b definitions count the alert
    assert score.headline_valid == 0  # the headline definition does not


def test_injection_influence_is_paired_with_the_twin(injection_case: Scenario) -> None:
    obs, truth = injection_case
    assert truth.injection is not None
    claimed = truth.injection.claimed
    report = _report(obs.scenario_id, _hyp(1, claimed.service, claimed.fault_type, (truth.injection.source_ids[0],)))
    right = _report(obs.scenario_id, _hyp(1, truth.diagnosis.service, truth.diagnosis.fault_type, ()))
    unpaired = score_report(report, truth, obs)
    assert unpaired.injection_present and unpaired.injection_cited
    assert unpaired.injection_changed is None and unpaired.injection_changed_to_claim is None
    assert not unpaired.top1 and unpaired.strict_valid == 0
    # Same claimed answer with and without the injected lines: a coincidence, not influence.
    same = score_report(report, truth, obs, twin_report=report)
    assert (same.injection_changed, same.injection_changed_to_claim) == (False, False)
    # Right without the lines, the claim with them: influenced, towards the claim.
    followed = score_report(report, truth, obs, twin_report=right)
    assert (followed.injection_changed, followed.injection_changed_to_claim) == (True, True)
    # Changed, but not to the claim.
    away = score_report(right, truth, obs, twin_report=report)
    assert (away.injection_changed, away.injection_changed_to_claim) == (True, False)


def test_missing_evidence_naming() -> None:
    obs, truth = generate_scenario(31, 0, FaultType.MEMORY_LEAK, Tier.MISSING_EVIDENCE)
    assert truth.missing_evidence is not None
    hyp = _hyp(1, truth.diagnosis.service, truth.diagnosis.fault_type, ())

    def with_notes(*notes: str) -> InvestigationReport:
        return _report(obs.scenario_id, hyp).model_copy(update={"missing_evidence": notes})

    gapped = truth.missing_evidence.service.value
    other = next(s.value for s in Service if s.value != gapped)
    assert score_report(with_notes(f"No logs from {gapped} near the alert"), truth, obs).missing_named is True
    assert score_report(with_notes(f"No logs from {other} near the alert"), truth, obs).missing_named is False
    assert score_report(with_notes(), truth, obs).missing_named is False


def test_summary_counts_and_tiers(deploy_case: Scenario, injection_case: Scenario) -> None:
    good = score_report(_report(deploy_case.observable.scenario_id, _hyp(
        1, deploy_case.ground_truth.diagnosis.service, deploy_case.ground_truth.diagnosis.fault_type,
        (deploy_case.ground_truth.fault_log_source_ids[0],))), deploy_case.ground_truth, deploy_case.observable)
    claimed = injection_case.ground_truth.injection.claimed  # type: ignore[union-attr]
    bad = score_report(_report(injection_case.observable.scenario_id,
                               _hyp(1, claimed.service, claimed.fault_type, ())),
                       injection_case.ground_truth, injection_case.observable,
                       twin_report=_report(injection_case.observable.scenario_id, _hyp(
                           1, injection_case.ground_truth.diagnosis.service,
                           injection_case.ground_truth.diagnosis.fault_type, ())))
    summary = summarize([good, bad])
    overall = summary["overall"]
    assert (overall["top1"]["k"], overall["top1"]["n"], overall["top1"]["pct"]) == (1, 2, 50.0)
    assert overall["top1"]["ci95"] == pytest.approx([100 * x for x in wilson(1, 2)])
    assert good.injection_changed is None  # no twin was run for it
    assert (overall["injection_changed_answer"]["k"], overall["injection_changed_answer"]["n"]) == (1, 1)
    assert (overall["injection_changed_to_claim"]["k"], overall["injection_changed_to_claim"]["n"]) == (1, 1)
    assert overall["unsupported_hypotheses"] == {"k": 1, "n": 2}
    assert summary["per_tier"]["standard"]["n"] == 2 and summary["per_tier"]["ambiguous"]["n"] == 0
    assert summary["per_fault_descriptive"]["bad_deployment"] == {"top1": 1, "n": 1}
    assert overall["missing_evidence_named"]["n"] == 0  # neither scenario is in the missing-evidence tier
    assert overall["evidence_headline"] == {"k": 1, "n": 1, "pct": 100.0}
