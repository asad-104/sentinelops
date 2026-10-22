"""Ground-truth labels. Written to a separate directory that tools never read."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict

from sentinelops.models import SCHEMA_VERSION, ScenarioId, Service, SourceId
from sentinelops.simulator.faults import FaultType


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Diagnosis(_Model):
    service: Service
    fault_type: FaultType


class LogProvenance(_Model):
    source_id: SourceId
    template_id: str
    variant_id: int
    origin: Literal["background", "change", "distractor", "fault", "injection"]


class MetricBlip(_Model):
    """A short, harmless latency spike injected as a distractor."""

    service: Service
    start: AwareDatetime
    end: AwareDatetime


class InjectionAttempt(_Model):
    """Log lines whose user-controlled text tries to steer an investigator."""

    source_ids: tuple[SourceId, ...]
    claimed: Diagnosis  # always wrong


class GroundTruth(_Model):
    schema_version: str = SCHEMA_VERSION
    generator_version: str
    scenario_id: ScenarioId
    seed: int
    index: int
    diagnosis: Diagnosis
    onset: AwareDatetime
    trigger_source_id: SourceId | None
    red_herring_source_ids: tuple[SourceId, ...]
    affected_services: tuple[Service, ...]
    fault_log_source_ids: tuple[SourceId, ...]
    metric_blip: MetricBlip
    injection: InjectionAttempt | None
    log_provenance: tuple[LogProvenance, ...]
