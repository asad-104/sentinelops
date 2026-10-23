"""M4 page: agent runs, exactly as the agent CLI wrote them (eval/agent/ by default; the trace directory is
a parameter, SENTINELOPS_VIEWER_AGENT).

Shows a chosen run's states in order, each tool call with the evidence it returned (raw and as compacted),
the hypotheses re-ranking across snapshots, every claim linked to its source record (resolved through
ToolSet.get_record on dev data), and the context budget per turn. Tool output, model text and reports are
untrusted: they appear only in dataframes or code blocks, never as markdown or HTML. No scoring here.
"""

import json
import sys
from pathlib import Path
from typing import get_args

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.dev_data import (  # noqa: E402
    ViewerDataError,
    agent_root,
    dev_scenarios_root,
    open_toolset,
    pilot_runs,
    pilot_summary,
    pilot_trace,
    pilot_traces,
)
from sentinelops.report import StopReason  # noqa: E402

STOP_REASONS = set(get_args(StopReason))

st.title("Agent runs")
st.caption("Dev only. Read from the M4 trace directory as the agent CLI wrote it; nothing is recomputed.")

try:
    root = agent_root()
    runs = pilot_runs(root)
except ViewerDataError as exc:
    st.error("Agent results are not available")
    st.code(str(exc), language=None)
    st.stop()
if not runs:
    st.info("No M4 agent runs yet. The trace directory stays empty until stage B; stage A mock runs are written "
            "to a temporary directory only.")
    st.stop()

run = st.selectbox("Run", runs, key="agent_run")
summary = pilot_summary(root, run)
if summary is None:
    st.error("This run's summary.json is missing or not valid JSON")
    st.stop()
meta = summary.get("metadata", {})
if meta.get("backend") == "mock":
    st.warning("Mock backend: a scripted policy on generated scenarios, not a model. Mechanics only.")
st.caption("Budgets: agent 40 read-tool calls, rule baseline about 52. \"Investigated\" measures process, not insight.")
st.dataframe(pd.DataFrame([{"item": k, "value": str(v)} for k, v in summary.get("rule", {}).items()]),
             hide_index=True, width="stretch")

names = pilot_traces(root, run)
if not names:
    st.warning("This run has no trace files")
    st.stop()
name = st.selectbox("Trace", names, key="agent_trace")
events, skipped = pilot_trace(root, run, name)
if skipped:
    st.info(f"Skipped {len(skipped)} malformed line(s): {', '.join(map(str, skipped))}")
start = next((e for e in events if e["event"] == "start"), {})
stop = next((e for e in events if e["event"] == "stop"), None)
reason = stop.get("stop_reason") if stop else None
a, b, c = st.columns(3)
a.metric("Stop reason", reason if reason in STOP_REASONS else "missing")
b.metric("Read-tool calls", stop.get("tool_calls", "–") if stop else "–")
c.metric("Model turns", stop.get("turns", "–") if stop else "–")

st.subheader("States in order")
st.dataframe(pd.DataFrame([{"order": i, "state": e.get("state"), "turn": e.get("turn"), "reason": e.get("reason")}
                           for i, e in enumerate(e for e in events if e["event"] == "state_enter")]),
             hide_index=True, width="stretch")

st.subheader("Tool calls and evidence")
tools = [e for e in events if e["event"] == "tool"]
st.dataframe(pd.DataFrame([{"step": i, "turn": e.get("turn"), "state": e.get("state"), "tool": e.get("name"),
                            "by": "loop" if e.get("by_loop") else "model", "valid": e.get("valid"), "ok": e.get("ok"),
                            "error": e.get("error_code"), "new IDs": len(e.get("new_ids") or []),
                            "kind": e.get("data_kind"), "evidence": e.get("evidence"),
                            "duplicate": e.get("duplicate")} for i, e in enumerate(tools)]),
             hide_index=True, width="stretch")
if tools:
    labels = [f"{i}. turn {e.get('turn')} · {e.get('state')} · {e.get('name')}" for i, e in enumerate(tools)]
    pick = st.selectbox("Tool call", range(len(tools)), format_func=lambda i: labels[i], key="agent_call")
    chosen = tools[pick]
    st.text("Arguments")
    st.code(chosen.get("arguments") or "", language=None)
    st.text("Evidence returned (as shown to the model)")
    st.code(chosen.get("shown") or "", language=None)
    st.text("As compacted in later requests")
    st.code(chosen.get("compacted") or "", language=None)

st.subheader("Hypotheses re-ranking")
snapshots = [e for e in events if e["event"] == "hypotheses"]
if snapshots:
    st.dataframe(pd.DataFrame([{"snapshot": i, "turn": e.get("turn"), "state": e.get("state"),
                                **{f"rank {h['rank']}": f"{h['service']} / {h['fault_type']}"
                                   for h in e.get("ranking", [])}} for i, e in enumerate(snapshots)]),
                 hide_index=True, width="stretch")
else:
    st.caption("No ranking was submitted in this run.")

st.subheader("Claims and their source records")
check = next((e for e in events if e["event"] == "claim_check"), None)
report = stop.get("report") if stop else None
if report and check:
    claims = check.get("claims", [])
    st.dataframe(pd.DataFrame(claims), hide_index=True, width="stretch")
    try:
        toolset = open_toolset(dev_scenarios_root(), start.get("scenario_id", ""))
    except Exception:  # scenario not in dev data (e.g. a generated mock set)
        toolset = None
    ids = [c["id"] for c in claims]
    if ids:
        sid = st.selectbox("Cited source ID", ids, key="agent_claim")
        record = toolset.call("get_record", {"source_id": sid}) if toolset else None
        if record is not None and record.ok:
            st.code(json.dumps(record.items[0].model_dump(mode="json"), indent=2, sort_keys=True), language=None)
        else:
            st.code("record not available (the scenario is not in the dev data this viewer reads)", language=None)
    st.text("Final report")
    st.code(json.dumps(report, indent=2, sort_keys=True), language=None)
else:
    st.error("No valid report")
    st.code((stop or {}).get("message") or "the trace has no stop event", language=None)

st.subheader("Context per turn")
models = {e.get("turn"): e for e in events if e["event"] == "model"}
rows = []
for e in (e for e in events if e["event"] == "context"):
    m = models.get(e.get("turn"), {})
    rows.append({"turn": e.get("turn"), "state": e.get("state"), "estimated": e.get("estimated_tokens"),
                 "budget": e.get("budget"), "level": e.get("level"), "min level": e.get("min_level"),
                 "ledger IDs": e.get("ledger_size"), "rendered IDs": e.get("rendered_ids"),
                 "reported prompt": m.get("prompt_tokens"), "prompt eval s": m.get("prompt_eval_s"),
                 "guard fired": m.get("guard_fired")})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
st.caption("Cache reuse is inferred from prompt-evaluation time, not measured; no threshold depends on it.")
