"""Observable data contracts for one simulated incident scenario.

Everything here is what an investigator (rule-based baseline, single-pass LLM or
agent) is allowed to see. Ground truth lives in ``sentinelops.simulator`` and
must never be imported by the tools.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1"

SOURCE_ID_PATTERN = r"^(LOG|MET|DPL|CFG|DEP|ALR)-\d{3,6}$"
SCENARIO_ID_PATTERN = r"^sc-[0-9a-f]{10}$"

SourceId = Annotated[str, Field(pattern=SOURCE_ID_PATTERN)]
ScenarioId = Annotated[str, Field(pattern=SCENARIO_ID_PATTERN)]


class Service(StrEnum):
    GATEWAY = "api-gateway"
    AUTH = "auth"
    ORDERS = "orders"
    PAYMENTS = "payments"


class LogLevel(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


LEVEL_RANK: dict[LogLevel, int] = {LogLevel.INFO: 0, LogLevel.WARN: 1, LogLevel.ERROR: 2}


class Metric(StrEnum):
    LATENCY_P95_MS = "latency_p95_ms"
    ERROR_RATE = "error_rate"
    CPU_PCT = "cpu_pct"
    MEMORY_PCT = "memory_pct"
    REQUEST_RATE = "request_rate"
    DB_POOL_UTILIZATION = "db_pool_utilization_pct"


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LogRecord(_Record):
    source_id: SourceId
    timestamp: AwareDatetime
    service: Service
    level: LogLevel
    message: str


class MetricPoint(_Record):
    source_id: SourceId
    timestamp: AwareDatetime
    service: Service
    metric: Metric
    value: float


class Deployment(_Record):
    source_id: SourceId
    timestamp: AwareDatetime
    service: Service
    version: str
    previous_version: str
    author: str
    summary: str


class ConfigChange(_Record):
    source_id: SourceId
    timestamp: AwareDatetime
    service: Service
    key: str
    old_value: str
    new_value: str
    author: str


class Dependency(_Record):
    source_id: SourceId
    caller: Service
    callee: Service


class Alert(_Record):
    source_id: SourceId
    timestamp: AwareDatetime
    service: Service
    metric: Metric
    severity: AlertSeverity
    observed_value: float
    threshold: float
    summary: str


class ScenarioObservable(_Record):
    schema_version: str = SCHEMA_VERSION
    scenario_id: ScenarioId
    window_start: AwareDatetime
    window_end: AwareDatetime
    alert: Alert
    logs: tuple[LogRecord, ...]
    metrics: tuple[MetricPoint, ...]
    deployments: tuple[Deployment, ...]
    config_changes: tuple[ConfigChange, ...]
    dependencies: tuple[Dependency, ...]
