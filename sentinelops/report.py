"""Investigation report contract shared by every investigator (baselines now, the agent later).

Investigator-side: never imports ``sentinelops.simulator``. Remediation is only
ever recommended; ``executed_actions`` must stay empty.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sentinelops.models import FaultType, ScenarioId, Service, SourceId
from sentinelops.tools import ToolResult

# A qualitative label, not a calibrated probability.
Confidence = Literal["high", "medium", "low"]
StopReason = Literal["sufficient_evidence", "budget_exhausted", "timeout", "no_new_evidence", "error"]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Hypothesis(_Model):
    rank: int = Field(ge=1, le=5)
    service: Service
    fault_type: FaultType
    confidence: Confidence
    supporting_evidence: tuple[SourceId, ...] = ()
    contradicting_evidence: tuple[SourceId, ...] = ()
    rationale: str = Field(max_length=2000)


class InvestigationReport(_Model):
    scenario_id: ScenarioId
    investigator: str
    summary: str
    affected_services: tuple[Service, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = Field(min_length=1, max_length=5)
    missing_evidence: tuple[str, ...] = ()
    uncertainty: str = ""
    next_checks: tuple[str, ...] = ()
    recommended_remediation: tuple[str, ...] = ()
    executed_actions: tuple[str, ...] = ()
    tool_calls: int = Field(ge=0)
    duration_s: float = Field(ge=0)
    stop_reason: StopReason

    @field_validator("executed_actions")
    @classmethod
    def _nothing_executed(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value:
            raise ValueError("investigators may only recommend remediation; executed_actions must be empty")
        return value

    @model_validator(mode="after")
    def _ranked_and_unique(self) -> InvestigationReport:
        if [h.rank for h in self.hypotheses] != list(range(1, len(self.hypotheses) + 1)):
            raise ValueError("hypotheses must be ranked 1..n in order")
        pairs = [(h.service, h.fault_type) for h in self.hypotheses]
        if len(pairs) != len(set(pairs)):
            raise ValueError("each (service, fault_type) pair may appear only once")
        return self

    @property
    def top(self) -> Hypothesis:
        return self.hypotheses[0]


class ToolCaller(Protocol):
    def call(self, name: str, arguments: Any = None) -> ToolResult: ...


class Investigator(Protocol):
    name: str

    def investigate(self, tools: ToolCaller, scenario_id: str) -> InvestigationReport: ...
