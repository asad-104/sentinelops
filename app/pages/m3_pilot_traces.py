"""M3 page: pilot runs and their traces, exactly as the pilot CLI wrote them (eval/pilot/ only).

Shows a chosen run's turns in order, each tool call with its valid / ok / error
status, the stop reason, and the final report or why there is none. Tool output,
model text and reports are untrusted: they are only ever shown inside dataframes
or code blocks, never as markdown or HTML. No scoring happens here.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.dev_data import ViewerDataError, pilot_root, pilot_runs, pilot_summary, pilot_trace, pilot_traces  # noqa: E402

STOP_REASONS = {"sufficient_evidence", "budget_exhausted", "timeout", "no_new_evidence", "error"}
RUN_COLUMNS = ["run", "scenario_id", "variant", "tier", "stop_reason", "report_valid", "repaired", "valid_calls",
               "model_calls", "turns", "elapsed_s", "prompt_tokens", "completion_tokens", "thinking_chars",
               "truncated_results", "cited_existing", "cited", "top1"]

st.title("Pilot traces")
st.caption("Dev pilot only. Read from eval/pilot/ as the pilot CLI wrote it; nothing is recomputed.")

try:
    root = pilot_root()
    runs = pilot_runs(root)
except ViewerDataError as exc:
    st.error("Pilot results are not available")
    st.code(str(exc), language=None)
    st.stop()
if not runs:
    st.warning("No pilot runs yet. Run: .venv/bin/python -m sentinelops.evaluation.pilot --backend mock")
    st.stop()

run = st.selectbox("Pilot run", runs, key="pilot_run")
summary = pilot_summary(root, run)
if summary is None:
    st.error("This run's summary.json is missing or not valid JSON")
    st.stop()

meta = summary.get("metadata", {})
if meta.get("backend") == "mock":
    st.warning("Mock backend: a scripted policy, not a model. These traces show the mechanics only.")
st.subheader("Runs")
st.dataframe(pd.DataFrame([{"field": k, "value": str(meta.get(k))} for k in
                           ("backend", "model", "prompt_sha256", "generator_version", "manifest_sha256",
                            "git_commit")]), hide_index=True, width="stretch")
rows = [r for r in summary.get("runs", []) if isinstance(r, dict)]
if rows:
    st.dataframe(pd.DataFrame(rows).reindex(columns=RUN_COLUMNS), hide_index=True, width="stretch")
rule = summary.get("rule", {})
st.caption("Decision rule (pre-registered 2026-10-23, core runs only). No pilot scenario is in the ambiguous "
           "tier. The 4,000-character cap on tool results can hide source IDs.")
st.dataframe(pd.DataFrame([{"item": k, "value": str(v)} for k, v in rule.items()]), hide_index=True,
             width="stretch")

st.subheader("Trace")
names = pilot_traces(root, run)
if not names:
    st.warning("This run has no trace files")
    st.stop()
name = st.selectbox("Trace", names, key="pilot_trace")
events, skipped = pilot_trace(root, run, name)
if skipped:
    st.info(f"Skipped {len(skipped)} malformed line(s): {', '.join(map(str, skipped))}")

stop = next((e for e in events if e["event"] == "stop"), None)
reason = stop.get("stop_reason") if stop else None
left, middle, right = st.columns(3)
left.metric("Stop reason", reason if reason in STOP_REASONS else "missing")
middle.metric("Tool calls", stop.get("tool_calls", "–") if stop else "–")
right.metric("Model turns", stop.get("turns", "–") if stop else "–")

steps = []
for i, e in enumerate(events):
    if e["event"] == "model":
        steps.append({"step": i, "turn": e.get("turn"), "event": "model", "name": ", ".join(e.get("tool_calls") or []),
                      "valid": None, "ok": e.get("error") is None, "error_code": e.get("error"),
                      "duplicate": None, "truncated": None, "latency_s": e.get("latency_s"),
                      "tokens": f"{e.get('prompt_tokens')} / {e.get('completion_tokens')}",
                      "text": (e.get("text") or e.get("message") or "")[:300]})
    elif e["event"] == "tool":
        steps.append({"step": i, "turn": e.get("turn"), "event": "tool (loop)" if e.get("by_loop") else "tool",
                      "name": e.get("name"), "valid": e.get("valid"), "ok": e.get("ok"),
                      "error_code": e.get("error_code"), "duplicate": e.get("duplicate"),
                      "truncated": e.get("truncated_for_context"), "latency_s": None, "tokens": None,
                      "text": (e.get("arguments") or "")[:300]})
st.dataframe(pd.DataFrame(steps), hide_index=True, width="stretch")
st.caption("Turns in order. For tool steps, 'text' is the arguments the model sent; for model steps, its text.")

tool_events = [e for e in events if e["event"] == "tool"]
if tool_events:
    labels = [f"{i + 1}. turn {e.get('turn')} · {e.get('name')}" for i, e in enumerate(tool_events)]
    pick = st.selectbox("Tool call", range(len(tool_events)), format_func=lambda i: labels[i], key="pilot_call")
    chosen = tool_events[pick]
    st.text("Arguments")
    st.code(chosen.get("arguments") or "", language=None)
    st.text("Shown to the model" + (" (truncated for context)" if chosen.get("truncated_for_context") else ""))
    st.code(chosen.get("shown") or "", language=None)

st.subheader("Final report")
if stop and stop.get("report"):
    st.code(json.dumps(stop["report"], indent=2, sort_keys=True), language=None)
else:
    st.error("No valid report")
    st.code((stop or {}).get("message") or "the trace has no stop event", language=None)
    invalid = [e for e in tool_events if e.get("error_code") == "invalid_report"]
    for e in invalid:
        st.text(f"Report validation error (turn {e.get('turn')})")
        st.code(e.get("shown") or "", language=None)
