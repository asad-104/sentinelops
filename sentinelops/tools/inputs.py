"""Validated tool inputs. Unknown fields are rejected and every result size is bounded."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from sentinelops.models import LogLevel, Metric, Service, SourceId

MAX_LOG_RESULTS = 200
MAX_METRIC_RESULTS = 500
MAX_CHANGE_RESULTS = 100
MAX_TIMELINE_RESULTS = 200


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TimeWindowInput(ToolInput):
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None

    @model_validator(mode="after")
    def _start_before_end(self) -> TimeWindowInput:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must not be after end")
        return self


class GetAlertInput(ToolInput):
    pass


class SearchLogsInput(TimeWindowInput):
    service: Service | None = None
    min_level: LogLevel | None = None
    contains: str | None = Field(default=None, min_length=1, max_length=200)
    limit: int = Field(default=50, ge=1, le=MAX_LOG_RESULTS)


class GetMetricsInput(TimeWindowInput):
    service: Service
    metric: Metric
    limit: int = Field(default=120, ge=1, le=MAX_METRIC_RESULTS)


class ListChangesInput(TimeWindowInput):
    service: Service | None = None
    limit: int = Field(default=50, ge=1, le=MAX_CHANGE_RESULTS)


class GetDependenciesInput(ToolInput):
    service: Service | None = None


class GetTimelineInput(TimeWindowInput):
    limit: int = Field(default=50, ge=1, le=MAX_TIMELINE_RESULTS)


class GetRecordInput(ToolInput):
    source_id: SourceId
