"""M1 page: one dev scenario as an investigator sees it, through the real tools.

Widgets map to ``ToolSet.call`` arguments and results are rendered as returned.
Log text is untrusted: it is only ever shown inside dataframes or code blocks,
never as markdown or HTML.
"""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.dev_data import (  # noqa: E402
    ViewerDataError,
    dev_ground_truth,
    dev_scenario_ids,
    dev_scenarios_root,
    open_toolset,
)
from sentinelops.models import LogLevel, Metric, Service  # noqa: E402
from sentinelops.tools import ToolResult, ToolSet  # noqa: E402

ANY = "(any)"


@st.cache_resource
def _toolset(root: str, scenario_id: str) -> ToolSet:
    return open_toolset(Path(root), scenario_id)


def _show_error(result: ToolResult) -> None:
    assert result.error is not None
    st.error("Tool returned an error")
    st.code(f"{result.error.code}: {result.error.message}", language=None)


def _rows(result: ToolResult) -> list[dict]:
    return [item.model_dump(mode="json") for item in result.items]


def _counts(result: ToolResult) -> None:
    a, b, c = st.columns(3)
    a.metric("Total matches", result.total_matches)
    b.metric("Returned", len(result.items))
    c.metric("Truncated", "yes" if result.truncated else "no")


st.title("Scenario explorer")
st.caption("Dev data only. Every panel below is a real read-only tool call.")

try:
    root = dev_scenarios_root()
    scenario_ids = dev_scenario_ids(root)
except (ViewerDataError, FileNotFoundError) as exc:
    st.error("Dev data is not available")
    st.code(f"{exc}\n\nGenerate it with: .venv/bin/python -m sentinelops.simulator --split dev", language=None)
    st.stop()
if not scenario_ids:
    st.warning("No dev scenarios found. Run: .venv/bin/python -m sentinelops.simulator --split dev")
    st.stop()

scenario_id = st.sidebar.selectbox("Scenario", scenario_ids, key="scenario")
tools = _toolset(str(root), scenario_id)

# Alert
alert = tools.call("get_alert").items[0]
st.subheader("Alert")
cols = st.columns(5)
cols[0].metric("Service", alert.service.value)
cols[1].metric("Metric", alert.metric.value)
cols[2].metric("Observed", alert.observed_value)
cols[3].metric("Threshold", alert.threshold)
cols[4].metric("Severity", alert.severity.value)
st.text(alert.summary)

with st.expander("Reveal answer (dev only)", expanded=False):
    try:
        st.json(dev_ground_truth(root, scenario_id))
    except (ViewerDataError, FileNotFoundError) as exc:
        st.code(str(exc), language=None)

# Timeline and dependencies
left, right = st.columns([3, 1])
with left:
    st.subheader("Timeline")
    st.dataframe(_rows(tools.call("get_timeline", {"limit": 200})), hide_index=True, width="stretch")
with right:
    st.subheader("Dependencies")
    deps = tools.call("get_dependencies", {"limit": 50})
    st.dataframe([{"caller": d["caller"], "callee": d["callee"]} for d in _rows(deps)], hide_index=True)

# Metrics
st.subheader("Metrics")
m1, m2, m3, m4 = st.columns([2, 2, 1, 1])
service = m1.selectbox("Service", [s.value for s in Service], key="metric_service")
metric = m2.selectbox("Metric", [m.value for m in Metric], key="metric_name")
limit = m3.number_input("Points limit", min_value=1, max_value=500, value=500, key="metric_limit")
compare = m4.toggle("Compare all services", key="metric_compare")

services = [s.value for s in Service] if compare else [service]
results = {svc: tools.call("get_metrics", {"service": svc, "metric": metric, "limit": int(limit)}) for svc in services}
ok = {svc: r for svc, r in results.items() if r.ok}
failed = {svc: r for svc, r in results.items() if not r.ok}

if any(r.truncated for r in ok.values()):
    st.warning(f"Results truncated: showing at most {int(limit)} points per service. Raise the points limit to see all.")
if ok:
    points = [{"timestamp": p.timestamp, "service": svc, "value": p.value} for svc, r in ok.items() for p in r.items]
    st.line_chart(pd.DataFrame(points), x="timestamp", y="value", color="service")
    st.caption(" · ".join(f"{svc}: {r.total_matches} points, truncated={r.truncated}" for svc, r in ok.items()))
if compare and failed:
    st.caption("Not reported by: " + ", ".join(f"{svc} ({r.error.code})" for svc, r in failed.items() if r.error))
elif not compare and failed:
    _show_error(failed[service])

# Log search
st.subheader("Log search")
with st.form("log_search"):
    f1, f2, f3, f4 = st.columns([1, 1, 2, 1])
    log_service = f1.selectbox("Service", [ANY] + [s.value for s in Service], key="log_service")
    min_level = f2.selectbox("Min level", [ANY] + [lv.value for lv in LogLevel], key="log_level")
    contains = f3.text_input("Contains", key="log_contains")
    log_limit = f4.number_input("Limit", min_value=1, max_value=200, value=50, key="log_limit")
    minutes = st.slider("Minutes from window start", 0, 120, (0, 120), key="log_minutes")
    st.form_submit_button("Search")

args: dict = {"limit": int(log_limit)}
if log_service != ANY:
    args["service"] = log_service
if min_level != ANY:
    args["min_level"] = min_level
if contains:
    args["contains"] = contains
if minutes != (0, 120):
    origin = tools.call("get_window").items[0].window_start
    args["start"] = (origin + timedelta(minutes=minutes[0])).isoformat()
    args["end"] = (origin + timedelta(minutes=minutes[1])).isoformat()

logs = tools.call("search_logs", args)
if logs.ok:
    _counts(logs)
    if logs.truncated:
        st.warning("Truncated: only the earliest matches are shown. Narrow the time range or raise the limit.")
    st.dataframe(
        [{k: row[k] for k in ("source_id", "timestamp", "service", "level", "message")} for row in _rows(logs)],
        hide_index=True, width="stretch",
    )
else:
    _show_error(logs)

# Record lookup
st.subheader("Record lookup")
source_id = st.text_input("Source ID (e.g. LOG-00042, MET-00001, DPL-001, ALR-001)", key="record_id")
if source_id:
    record = tools.call("get_record", {"source_id": source_id})
    if record.ok:
        st.json(_rows(record)[0])
    else:
        _show_error(record)
