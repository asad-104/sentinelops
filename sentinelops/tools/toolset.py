"""Read-only investigation tools over one scenario's observable data.

The toolset is built from a ``ScenarioObservable`` only. It has no path to
ground truth: it loads from a scenarios root by validated scenario ID, and this
package never imports ``sentinelops.simulator``. All records are frozen, so a
caller cannot mutate the data behind a tool.

``ToolSet.call`` never raises: every failure comes back as a ``ToolResult`` with
``ok=False`` and a machine-readable error code, so an agent can recover. Log
messages are returned verbatim; they are untrusted data, never instructions.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, ValidationError

from sentinelops.models import (
    LEVEL_RANK,
    SCENARIO_ID_PATTERN,
    ScenarioId,
    Alert,
    ConfigChange,
    Dependency,
    Deployment,
    LogRecord,
    MetricPoint,
    ScenarioObservable,
    Service,
    SourceId,
)
from sentinelops.scenario_files import load_observable
from sentinelops.tools.inputs import (
    GetAlertInput,
    GetWindowInput,
    GetDependenciesInput,
    GetMetricsInput,
    GetRecordInput,
    GetTimelineInput,
    ListChangesInput,
    SearchLogsInput,
    TimeWindowInput,
    ToolInput,
)


class ToolError(Exception):
    """Raised when a scenario cannot be loaded. Tool calls never raise this."""


# budget_exhausted is returned by budget-enforcing wrappers (the evaluation harness, later the agent).
ErrorCode = Literal["unknown_tool", "invalid_arguments", "out_of_window", "unsupported_metric",
                    "not_found", "internal_error", "budget_exhausted"]


class _Failure(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class TimelineEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: SourceId
    timestamp: AwareDatetime
    kind: Literal["alert", "deployment", "config_change"]
    service: Service
    description: str


class ScenarioWindow(BaseModel):
    """The observation window. Contains only fields from the scenario manifest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: ScenarioId
    window_start: AwareDatetime
    window_end: AwareDatetime


ToolItem = LogRecord | MetricPoint | Deployment | ConfigChange | Dependency | Alert | TimelineEvent | ScenarioWindow


class ToolErrorInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: ErrorCode
    message: str


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str
    ok: bool = True
    items: tuple[ToolItem, ...] = ()
    total_matches: int = 0
    truncated: bool = False
    error: ToolErrorInfo | None = None


def _result(tool: str, matches: Sequence[ToolItem], limit: int) -> ToolResult:
    return ToolResult(tool=tool, items=tuple(matches[:limit]), total_matches=len(matches),
                      truncated=len(matches) > limit)


def _error(tool: str, code: ErrorCode, message: str) -> ToolResult:
    return ToolResult(tool=tool, ok=False, error=ToolErrorInfo(code=code, message=message))


def _describe(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in exc.errors())


# Tool name -> validated input model, in a fixed order. Shared by every ToolSet, and used to build
# LLM tool schemas without a scenario (e.g. sentinelops.llm.schemas).
TOOL_INPUT_MODELS: dict[str, type[ToolInput]] = {
    "get_alert": GetAlertInput,
    "get_window": GetWindowInput,
    "search_logs": SearchLogsInput,
    "get_metrics": GetMetricsInput,
    "list_deployments": ListChangesInput,
    "list_config_changes": ListChangesInput,
    "get_dependencies": GetDependenciesInput,
    "get_timeline": GetTimelineInput,
    "get_record": GetRecordInput,
}


class ToolSet:
    def __init__(self, observable: ScenarioObservable) -> None:
        self._obs = observable
        self._records: dict[str, ToolItem] = {
            r.source_id: r
            for r in chain((observable.alert,), observable.logs, observable.metrics, observable.deployments,
                           observable.config_changes, observable.dependencies)
        }
        self._metric_series = {(p.service, p.metric) for p in observable.metrics}
        self._registry: dict[str, tuple[type[ToolInput], Callable[[Any], ToolResult]]] = {
            name: (model, getattr(self, name)) for name, model in TOOL_INPUT_MODELS.items()
        }

    @classmethod
    def from_directory(cls, scenarios_root: Path, scenario_id: str) -> ToolSet:
        if not re.fullmatch(SCENARIO_ID_PATTERN, scenario_id):
            raise ToolError(f"invalid scenario id {scenario_id!r}")
        root = scenarios_root.resolve()
        scenario_dir = (root / scenario_id).resolve()
        if not scenario_dir.is_relative_to(root):
            raise ToolError(f"scenario id {scenario_id!r} escapes the scenarios directory")
        return cls(load_observable(scenario_dir))

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(self._registry)

    @property
    def tool_input_models(self) -> dict[str, type[ToolInput]]:
        """Input model per tool, e.g. for building an LLM's tool schemas."""
        return {name: model for name, (model, _) in self._registry.items()}

    def call(self, name: str, arguments: Any = None) -> ToolResult:
        """Validate untrusted arguments (e.g. from a model) and dispatch. Never raises."""
        tool = name if isinstance(name, str) else repr(name)
        if tool not in self._registry:
            return _error(tool, "unknown_tool", f"unknown tool {tool!r}; available tools: {', '.join(self._registry)}")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            return _error(tool, "invalid_arguments", f"arguments must be an object, got {type(arguments).__name__}")
        input_model, handler = self._registry[tool]
        try:
            return handler(input_model.model_validate(dict(arguments)))
        except ValidationError as exc:
            return _error(tool, "invalid_arguments", f"invalid arguments for {tool}: {_describe(exc)}")
        except _Failure as failure:
            return _error(tool, failure.code, failure.message)
        except Exception as exc:  # a tool bug must not crash the investigation loop
            return _error(tool, "internal_error", f"{tool} failed with {type(exc).__name__}")

    # Tools

    def get_window(self, params: GetWindowInput | None = None) -> ToolResult:
        window = ScenarioWindow(scenario_id=self._obs.scenario_id, window_start=self._obs.window_start,
                                window_end=self._obs.window_end)
        return _result("get_window", [window], 1)

    def get_alert(self, params: GetAlertInput | None = None) -> ToolResult:
        return _result("get_alert", [self._obs.alert], 1)

    def search_logs(self, params: SearchLogsInput) -> ToolResult:
        start, end = self._window(params)
        needle = params.contains.lower() if params.contains else None
        min_rank = LEVEL_RANK[params.min_level] if params.min_level else 0
        matches = [
            log for log in self._obs.logs
            if start <= log.timestamp <= end
            and (params.service is None or log.service is params.service)
            and LEVEL_RANK[log.level] >= min_rank
            and (needle is None or needle in log.message.lower())
        ]
        return _result("search_logs", matches, params.limit)

    def get_metrics(self, params: GetMetricsInput) -> ToolResult:
        if (params.service, params.metric) not in self._metric_series:
            raise _Failure("unsupported_metric", f"{params.service} does not report {params.metric}")
        start, end = self._window(params)
        matches = [
            p for p in self._obs.metrics
            if p.service is params.service and p.metric is params.metric and start <= p.timestamp <= end
        ]
        return _result("get_metrics", matches, params.limit)

    def list_deployments(self, params: ListChangesInput) -> ToolResult:
        return _result("list_deployments", self._changes(self._obs.deployments, params), params.limit)

    def list_config_changes(self, params: ListChangesInput) -> ToolResult:
        return _result("list_config_changes", self._changes(self._obs.config_changes, params), params.limit)

    def get_dependencies(self, params: GetDependenciesInput) -> ToolResult:
        matches = [
            d for d in self._obs.dependencies
            if params.service is None or params.service in (d.caller, d.callee)
        ]
        return _result("get_dependencies", matches, params.limit)

    def get_timeline(self, params: GetTimelineInput) -> ToolResult:
        start, end = self._window(params)
        alert = self._obs.alert
        events = [TimelineEvent(source_id=alert.source_id, timestamp=alert.timestamp, kind="alert",
                                service=alert.service, description=alert.summary)]
        events += [TimelineEvent(source_id=d.source_id, timestamp=d.timestamp, kind="deployment", service=d.service,
                                 description=f"{d.previous_version} -> {d.version} by {d.author}: {d.summary}")
                   for d in self._obs.deployments]
        events += [TimelineEvent(source_id=c.source_id, timestamp=c.timestamp, kind="config_change",
                                 service=c.service,
                                 description=f"{c.key}: {c.old_value} -> {c.new_value} by {c.author}")
                   for c in self._obs.config_changes]
        matches = sorted((e for e in events if start <= e.timestamp <= end), key=lambda e: (e.timestamp, e.source_id))
        return _result("get_timeline", matches, params.limit)

    def get_record(self, params: GetRecordInput) -> ToolResult:
        record = self._records.get(params.source_id)
        if record is None:
            raise _Failure("not_found", f"no record with source id {params.source_id}")
        return _result("get_record", [record], 1)

    # Helpers

    def _window(self, params: TimeWindowInput) -> tuple[datetime, datetime]:
        lo, hi = self._obs.window_start, self._obs.window_end
        for label, value in (("start", params.start), ("end", params.end)):
            if value is not None and not lo <= value <= hi:
                raise _Failure("out_of_window", f"{label} {value.isoformat()} is outside the scenario window "
                                                f"{lo.isoformat()} to {hi.isoformat()}")
        return params.start or lo, params.end or hi

    def _changes(self, records: Sequence[Deployment | ConfigChange], params: ListChangesInput) -> list[ToolItem]:
        start, end = self._window(params)
        return [
            r for r in records
            if start <= r.timestamp <= end and (params.service is None or r.service is params.service)
        ]
