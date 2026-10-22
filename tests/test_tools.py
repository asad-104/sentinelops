from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from sentinelops.models import LogLevel, Metric, Service
from sentinelops.scenario_files import load_observable
from sentinelops.simulator import Scenario
from sentinelops.tools import ToolResult, ToolSet
from sentinelops.tools.inputs import MAX_LOG_RESULTS


def _ok(result: ToolResult) -> ToolResult:
    assert result.ok, result.error
    return result


def test_files_round_trip(scenarios_root: Path, small_dataset: list[Scenario]) -> None:
    for obs, _ in small_dataset:
        assert load_observable(scenarios_root / obs.scenario_id) == obs


def test_exposes_only_read_tools(toolset: ToolSet) -> None:
    assert set(toolset.tool_names) == {
        "get_alert", "get_window", "search_logs", "get_metrics", "list_deployments", "list_config_changes",
        "get_dependencies", "get_timeline", "get_record",
    }


def test_returned_records_are_immutable(toolset: ToolSet) -> None:
    record = _ok(toolset.call("search_logs", {"limit": 1})).items[0]
    with pytest.raises(ValidationError):
        record.message = "tampered"  # type: ignore[misc]
    assert toolset.call("search_logs", {"limit": 1}).items[0] == record


def test_get_window_reveals_only_the_window(toolset: ToolSet, small_dataset: list[Scenario]) -> None:
    obs, truth = small_dataset[0]
    window = _ok(toolset.call("get_window")).items[0]
    assert window.model_dump() == {"scenario_id": obs.scenario_id, "window_start": obs.window_start,
                                   "window_end": obs.window_end}
    text = window.model_dump_json().lower()
    leaked = [v for v in (truth.diagnosis.fault_type.value, truth.tier.value, "onset", "fault", "trigger", "tier")
              if v in text]
    assert not leaked
    assert window.window_start != truth.onset and window.window_end > truth.onset


def test_get_alert(toolset: ToolSet, small_dataset: list[Scenario]) -> None:
    assert _ok(toolset.call("get_alert")).items == (small_dataset[0].observable.alert,)


def test_search_logs_filters(toolset: ToolSet) -> None:
    result = _ok(toolset.call("search_logs", {"service": "payments", "min_level": "WARN", "limit": MAX_LOG_RESULTS}))
    assert result.items
    assert all(r.service is Service.PAYMENTS and r.level in (LogLevel.WARN, LogLevel.ERROR) for r in result.items)

    some_message = result.items[0].message
    found = _ok(toolset.call("search_logs", {"contains": some_message.upper(), "limit": MAX_LOG_RESULTS}))
    assert any(r.message == some_message for r in found.items)


def test_time_window_filter(toolset: ToolSet, small_dataset: list[Scenario]) -> None:
    obs = small_dataset[0].observable
    start, end = obs.window_start + timedelta(minutes=30), obs.window_start + timedelta(minutes=31)
    result = _ok(toolset.call("search_logs", {"start": start.isoformat(), "end": end.isoformat()}))
    assert result.items and all(start <= r.timestamp <= end for r in result.items)


def test_search_logs_truncates_and_reports_it(toolset: ToolSet) -> None:
    result = _ok(toolset.call("search_logs", {"limit": 5}))
    assert len(result.items) == 5
    assert result.truncated is True
    assert result.total_matches > 5
    first_five = toolset.call("search_logs", {"limit": MAX_LOG_RESULTS}).items[:5]
    assert result.items == first_five, "truncation keeps the earliest matches"


def test_untruncated_result_says_so(toolset: ToolSet) -> None:
    result = _ok(toolset.call("get_metrics", {"service": "orders", "metric": "error_rate", "limit": 500}))
    assert result.truncated is False
    assert len(result.items) == result.total_matches == 120


def test_metric_truncation(toolset: ToolSet) -> None:
    result = _ok(toolset.call("get_metrics", {"service": "orders", "metric": "error_rate", "limit": 10}))
    assert (len(result.items), result.total_matches, result.truncated) == (10, 120, True)


def test_changes_and_timeline(toolset: ToolSet, small_dataset: list[Scenario]) -> None:
    obs = small_dataset[0].observable
    assert _ok(toolset.call("list_deployments")).items == obs.deployments
    assert _ok(toolset.call("list_config_changes")).items == obs.config_changes
    timeline = _ok(toolset.call("get_timeline")).items
    assert len(timeline) == 1 + len(obs.deployments) + len(obs.config_changes)
    assert [e.timestamp for e in timeline] == sorted(e.timestamp for e in timeline)


SINGLE_ITEM_TOOLS = {"get_alert", "get_window", "get_record"}


def test_every_tool_bounds_its_results(toolset: ToolSet, small_dataset: list[Scenario]) -> None:
    """No span cap per call is acceptable only because every tool enforces limit and truncated."""
    for name, model in toolset.tool_input_models.items():
        if name in SINGLE_ITEM_TOOLS:
            assert "limit" not in model.model_fields, name
            continue
        limit_field = model.model_fields.get("limit")
        assert limit_field is not None, f"{name} has no limit"
        caps = [m.le for m in limit_field.metadata if getattr(m, "le", None) is not None]
        assert caps and caps[0] <= 500, f"{name} limit is not capped"
        required = {"get_metrics": {"service": "orders", "metric": "error_rate"}}.get(name, {})
        result = _ok(toolset.call(name, {**required, "limit": 1}))
        assert len(result.items) <= 1
        assert result.truncated == (result.total_matches > 1), name
    record_id = small_dataset[0].observable.logs[0].source_id
    for name, args in (("get_alert", {}), ("get_window", {}), ("get_record", {"source_id": record_id})):
        result = _ok(toolset.call(name, args))
        assert len(result.items) == 1 and result.truncated is False


def test_dependencies_truncate(toolset: ToolSet) -> None:
    result = _ok(toolset.call("get_dependencies", {"limit": 2}))
    assert (len(result.items), result.total_matches, result.truncated) == (2, 4, True)


def test_dependencies(toolset: ToolSet) -> None:
    edges = _ok(toolset.call("get_dependencies", {"service": "payments"})).items
    assert {(e.caller, e.callee) for e in edges} == {(Service.ORDERS, Service.PAYMENTS)}


def test_get_record(toolset: ToolSet, small_dataset: list[Scenario]) -> None:
    log = small_dataset[0].observable.logs[42]
    assert _ok(toolset.call("get_record", {"source_id": log.source_id})).items == (log,)


@pytest.mark.parametrize("name, arguments, code, message", [
    ("delete_logs", {}, "unknown_tool", "unknown tool"),
    ("search_logs", {"path": "/etc/passwd"}, "invalid_arguments", "Extra inputs"),
    ("search_logs", {"service": "database"}, "invalid_arguments", "service"),
    ("search_logs", {"limit": 0}, "invalid_arguments", "limit"),
    ("search_logs", {"limit": MAX_LOG_RESULTS + 1}, "invalid_arguments", "limit"),
    ("search_logs", {"contains": ""}, "invalid_arguments", "contains"),
    ("search_logs", {"contains": "x" * 201}, "invalid_arguments", "contains"),
    ("search_logs", {"start": "2026-01-01T00:00:00"}, "invalid_arguments", "timezone"),
    ("search_logs", {"start": "2026-01-02T00:00:00Z", "end": "2026-01-01T00:00:00Z"}, "invalid_arguments",
     "start must not be after end"),
    ("search_logs", {"start": "2020-01-01T00:00:00Z"}, "out_of_window", "outside the scenario window"),
    ("search_logs", ["limit", 5], "invalid_arguments", "must be an object"),
    ("search_logs", "limit=5", "invalid_arguments", "must be an object"),
    ("get_metrics", {"service": "orders"}, "invalid_arguments", "metric"),
    ("get_metrics", {"service": "api-gateway", "metric": Metric.DB_POOL_UTILIZATION.value}, "unsupported_metric",
     "does not report"),
    ("get_record", {"source_id": "../../ground_truth"}, "invalid_arguments", "source_id"),
    ("get_record", {"source_id": "LOG-99999"}, "not_found", "no record"),
])
def test_invalid_calls_return_structured_errors(toolset: ToolSet, name: str, arguments: object, code: str,
                                                message: str) -> None:
    result = toolset.call(name, arguments)
    assert result.ok is False and result.items == () and result.error is not None
    assert result.error.code == code
    assert message in result.error.message


@pytest.mark.parametrize("arguments", [None, {}, {"limit": None}, {"limit": "5"}, {"limit": 1.5},
                                       {"service": ["auth"]}, {"contains": "\x00{}%s"}, {"start": 12345}])
def test_tool_calls_never_raise(toolset: ToolSet, arguments: object) -> None:
    for name in (*toolset.tool_names, "", "rm -rf /"):
        result = toolset.call(name, arguments)
        assert isinstance(result, ToolResult)
        assert result.ok or result.error is not None
