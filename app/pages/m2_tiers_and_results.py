"""M2 page: dev tier counts and dev results, with the floors drawn as reference lines.

Reads only dev ground-truth summaries and dev result files (eval/results/
generator-v<N>/dev-*.json). No scoring happens here: numbers are shown exactly
as the evaluation harness wrote them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import altair as alt  # noqa: E402  (ships with Streamlit)
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.dev_data import (  # noqa: E402
    ViewerDataError,
    dev_result_versions,
    dev_results,
    dev_scenario_ids,
    dev_scenarios_root,
    dev_tier_counts,
    results_root,
)

BASELINE = "rule_based"
FLOORS = ("keyword_only", "latest_change", "alert_service")
TIERS = ("standard", "ambiguous", "missing_evidence")
METRICS = {"Top-1": "top1", "Top-3": "top3", "Service top-1": "service_top1"}

st.title("Tiers and dev results")
st.caption("Dev data only. Numbers are read from the evaluation harness's result files, not recomputed.")

# Tier counts
st.subheader("Dev tier counts")
try:
    root = dev_scenarios_root()
    counts = dev_tier_counts(root, dev_scenario_ids(root))
except (ViewerDataError, FileNotFoundError) as exc:
    st.error("Dev data is not available")
    st.code(f"{exc}\n\nGenerate it with: .venv/bin/python -m sentinelops.simulator --split dev", language=None)
    counts = []
if counts:
    table = pd.DataFrame(counts).pivot(index="fault_type", columns="tier", values="scenarios").fillna(0).astype(int)
    table = table.reindex(columns=[t for t in TIERS if t in table.columns])
    table.loc["total"] = table.sum()
    st.dataframe(table, width="stretch")
    st.caption("Counts come from the dev data currently on disk, which is always the current generator version.")

# Results
st.subheader("Dev results")
versions = dev_result_versions(results_root())
if not versions:
    st.warning("No dev results yet. Run: .venv/bin/python -m sentinelops.evaluation --split dev --investigator all")
    st.stop()
version = st.selectbox("Results for", versions, key="results_version")
metric_label = st.radio("Metric", list(METRICS), horizontal=True, key="results_metric")
metric = METRICS[metric_label]
results = dev_results(results_root(), version)
if BASELINE not in results:
    st.warning(f"{version} has no {BASELINE} results")
    st.stop()

rows = []
for name, summary in results.items():
    for tier in ("overall", *TIERS):
        block = summary["overall"] if tier == "overall" else summary["per_tier"][tier]
        rate = block[metric]
        rows.append({"investigator": name, "slice": tier, "pct": rate["pct"], "k": rate["k"], "n": rate["n"],
                     "ci_low": rate["ci95"][0], "ci_high": rate["ci95"][1]})
frame = pd.DataFrame(rows)
order = ["overall", *TIERS]
baseline = frame[frame["investigator"] == BASELINE]
floors = frame[frame["investigator"].isin(FLOORS)]

bars = alt.Chart(baseline).mark_bar(color="#4c78a8", opacity=0.85).encode(
    x=alt.X("slice:N", sort=order, title=None),
    y=alt.Y("pct:Q", title=f"{metric_label} (%)", scale=alt.Scale(domain=[0, 100])),
    tooltip=["slice", "k", "n", alt.Tooltip("pct:Q", format=".0f"),
             alt.Tooltip("ci_low:Q", format=".0f"), alt.Tooltip("ci_high:Q", format=".0f")],
)
interval = alt.Chart(baseline).mark_rule(color="#1f2d3d").encode(
    x=alt.X("slice:N", sort=order), y="ci_low:Q", y2="ci_high:Q")
floor_lines = alt.Chart(floors).mark_tick(thickness=3, size=46).encode(
    x=alt.X("slice:N", sort=order),
    y="pct:Q",
    color=alt.Color("investigator:N", title="Floors", scale=alt.Scale(scheme="set2")),
    tooltip=["investigator", "slice", "k", "n", alt.Tooltip("pct:Q", format=".0f")],
)
layers = [bars, interval, floor_lines]
random_floor = {"top1": 100 / 19, "top3": 300 / 19, "service_top1": 25.0}[metric]
layers.append(alt.Chart(pd.DataFrame({"pct": [random_floor]})).mark_rule(strokeDash=[4, 4], color="gray")
              .encode(y="pct:Q"))
st.altair_chart(alt.layer(*layers).properties(height=360), width="stretch")
st.caption(f"Bars: {BASELINE} with Wilson 95% intervals. Ticks: floors. Dashed line: random "
           f"({random_floor:.1f}%). Tier cells are small (10–20 scenarios); read the intervals, not the bars.")

def _cell(row: pd.Series) -> str:
    if not row["n"]:
        return "n/a"
    return f"{row['k']}/{row['n']} ({row['pct']:.0f}%, {row['ci_low']:.0f}–{row['ci_high']:.0f})"


table = frame.assign(result=frame.apply(_cell, axis=1))
st.dataframe(table.pivot(index="investigator", columns="slice", values="result").reindex(columns=order),
             width="stretch")
