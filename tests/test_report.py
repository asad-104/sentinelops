from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentinelops.models import FaultType, Service
from sentinelops.report import Hypothesis, InvestigationReport


def _hyp(rank: int, service: Service = Service.ORDERS, fault: FaultType = FaultType.BAD_DEPLOYMENT) -> dict:
    return {"rank": rank, "service": service, "fault_type": fault, "confidence": "low", "rationale": "x"}


def _report(**overrides: object) -> dict:
    base = {"scenario_id": "sc-0123456789", "investigator": "t", "summary": "s",
            "hypotheses": [_hyp(1)], "tool_calls": 0, "duration_s": 0.0, "stop_reason": "sufficient_evidence"}
    return base | overrides


def test_valid_report() -> None:
    report = InvestigationReport.model_validate(_report(
        hypotheses=[_hyp(1), _hyp(2, Service.AUTH), _hyp(3, fault=FaultType.MEMORY_LEAK)]))
    assert report.top.rank == 1 and report.executed_actions == ()


@pytest.mark.parametrize("overrides, message", [
    ({"hypotheses": [_hyp(1), _hyp(1, Service.AUTH)]}, "ranked 1..n"),
    ({"hypotheses": [_hyp(2)]}, "ranked 1..n"),
    ({"hypotheses": [_hyp(1), _hyp(2)]}, "only once"),
    ({"hypotheses": []}, "at least 1"),
    ({"hypotheses": [_hyp(i, list(Service)[i % 4], list(FaultType)[i % 5]) for i in range(1, 7)]}, "rank"),
    ({"executed_actions": ["rollback DPL-001"]}, "only recommend"),
    ({"stop_reason": "gave_up"}, "stop_reason"),
    ({"tool_calls": -1}, "tool_calls"),
    ({"scenario_id": "../x"}, "scenario_id"),
    ({"surprise": 1}, "Extra inputs"),
])
def test_invalid_reports_are_rejected(overrides: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        InvestigationReport.model_validate(_report(**overrides))


@pytest.mark.parametrize("field, value", [("fault_type", "network_partition"), ("service", "database"),
                                          ("confidence", "certain"), ("supporting_evidence", ["../etc"])])
def test_invalid_hypotheses_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Hypothesis.model_validate(_hyp(1) | {field: value})
