"""M5 page: the fresh-split headline as aggregate counts only (eval/m5/generator-v5/m5_analysis.json and the E1
report's counts; parameters SENTINELOPS_VIEWER_M5 and SENTINELOPS_VIEWER_E1).

Never reads fresh-split traces, scenario files or ground truth, and shows no scenario ID: the loader keeps only
aggregate keys and refuses anything that still contains one. Nothing is recomputed except the D1 2x2's concordant
cells, derived from the per-arm counts and shown only when they agree.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.dev_data import ViewerDataError, m5_aggregates  # noqa: E402

AGENT, FULL, BARE = "agent_v1", "single_pass_full", "single_pass_no_timeline"

st.title("M5 · Headline comparison (fresh split, aggregates only)")
st.caption("Agent prompt v1 against a single-pass baseline and local baselines, one hosted model "
           "(ministral-14b-2512), 60 synthetic, author-built scenarios, one run per arm. Counts with Wilson 95% "
           "intervals; no pass/fail verdict. Not a result about agents in general, the local 4B model, or real "
           "incidents. No scenario content is shown.")

try:
    a = m5_aggregates()
except ViewerDataError as exc:
    st.error("M5 aggregates are not available")
    st.code(str(exc), language=None)
    st.stop()
if a is None:
    st.info("No M5 analysis yet. Run python -m sentinelops.evaluation.m5_analysis after the fresh-split runs.")
    st.stop()

meta = a["metadata"] or {}
if not meta.get("complete"):
    st.warning("INCOMPLETE: at least one slice is missing or stopped; counts cover the scenarios that ran.")


def ci(x: dict) -> str:
    return f"{x['k']}/{x['n']} [{x['wilson_95'][0]:.2f}, {x['wilson_95'][1]:.2f}]"


st.subheader("Primary (D1): top-1, agent v1 against single-pass full")
p, arms = a["primary"], a["arms"]
st.write(f"Exact two-sided sign test on n = {p['discordant']} discordant pairs: p = {p['p_two_sided']:.4f} "
         f"(over {p['n_pairs']} paired originals).")
both_right = arms[AGENT]["top1"]["k"] - p["a_right_b_wrong"]
if both_right == arms[FULL]["top1"]["k"] - p["b_right_a_wrong"]:
    both_wrong = p["n_pairs"] - both_right - p["discordant"]
    grid = pd.DataFrame({"single-pass right": [both_right, p["b_right_a_wrong"]],
                         "single-pass wrong": [p["a_right_b_wrong"], both_wrong]},
                        index=["agent right", "agent wrong"])
    st.dataframe(grid, width="content")
else:
    st.dataframe(pd.DataFrame([{"agent right, single-pass wrong": p["a_right_b_wrong"],
                                "single-pass right, agent wrong": p["b_right_a_wrong"]}]), hide_index=True)

st.subheader("Every arm (60 fresh originals)")
rows = [{"arm": name, "top-1": ci(r["top1"]), "top-3": ci(r["top3"]),
         "valid reports": f"{r['valid_reports']['k']}/{r['valid_reports']['n']}"} for name, r in arms.items()]
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
points = pd.DataFrame([{"arm": name, "top-1": r["top1"]["k"] / r["top1"]["n"], "low": r["top1"]["wilson_95"][0],
                        "high": r["top1"]["wilson_95"][1]} for name, r in arms.items() if r["top1"]["n"]])
base = alt.Chart(points).encode(y=alt.Y("arm:N", sort=None, title=None))
st.altair_chart(base.mark_rule().encode(x=alt.X("low:Q", scale=alt.Scale(domain=[0, 1]), title="top-1 (Wilson 95%)"),
                                        x2="high:Q") + base.mark_point(filled=True, size=60).encode(x="top-1:Q"),
                width="stretch")
st.caption("A run without a valid report counts as wrong. Budgets: agent 40 tool calls, rule baseline 52.")

st.subheader("By tier (top-1)")
tiers = list(next(iter(arms.values()))["by_tier"])
st.dataframe(pd.DataFrame([{"arm": name, **{t: ci(r["by_tier"][t]["top1"]) for t in tiers}}
                           for name, r in arms.items()]), hide_index=True, width="stretch")
st.subheader("By fault type (top-1 / top-3 / n, counts only)")
faults = list(next(iter(arms.values()))["by_fault_type"])
st.dataframe(pd.DataFrame([{"arm": name, **{f: "{top1} / {top3} / {n}".format(**r["by_fault_type"][f]) for f in faults}}
                           for name, r in arms.items()]), hide_index=True, width="stretch")

ab = a["ablation"]
st.subheader("Ablation: single-pass full against no-timeline (all change records removed)")
st.write(f"Full right and no-timeline wrong {ab['a_right_b_wrong']}, the reverse {ab['b_right_a_wrong']}; "
         f"sign test n = {ab['discordant']}, p = {ab['p_two_sided']:.4f}. Secondary and uncorrected.")

st.subheader("Process measures")
sec = a["secondary"] or {}


def kn(x: dict | None) -> str:
    return "n/a" if x is None else f"{x['k']}/{x['n']}"


st.dataframe(pd.DataFrame([{
    "arm": name, "valid change-tool call": kn(s.get("valid_change_call")), "trigger seen": kn(s.get("trigger_seen")),
    "investigated (a)-(f)": kn((s.get("investigated") or {}).get("investigated")),
    "tool calls median / max": "n/a" if not s.get("tool_calls") else
    f"{s['tool_calls']['median']:g} / {s['tool_calls']['max']:g}",
    "unsupported hypotheses": kn(s.get("unsupported_hypotheses")), "fabricated citations": s.get("fabricated_citations"),
} for name, s in sec.items()]), hide_index=True, width="stretch")
st.caption("A valid change-tool call returns a record before the first ranking. \"Investigated\" measures process, "
           "not insight.")

st.subheader("Injection (separate, labelled)")
ne, sa, e1 = a["natural_exposure"], a["safety"], a["e1"]
st.write(f"Natural exposure: of {ne['injected_originals']} injected originals, the agent was shown an injected line "
         f"in {ne['agent_exposed']}; the single-pass bundle contains one in {ne['single_pass_full_exposed']} (full) "
         f"and {ne['single_pass_no_timeline_exposed']} (no-timeline).")
c = sa["counts"] or {}
left, right = st.columns(2)
with left:
    st.markdown("**Safety test (pre-registered)**")
    st.dataframe(pd.DataFrame([{"count": k, "value": v} for k, v in c.items()]), hide_index=True, width="stretch")
    st.caption("Executed actions = 0 holds by design: no action tools exist.")
with right:
    st.markdown("**E1 (exploratory, post hoc)**")
    if e1 is None:
        st.info("No E1 report.")
    else:
        ec, tw = e1["counts"], e1["counts"]["among_twin_pairs"]
        st.dataframe(pd.DataFrame([
            {"count": "replicates", "value": ec["replicates"]},
            {"count": "both reports (original and replicate)", "value": ec["both_reports"]},
            {"count": "top-1 differs, original vs replicate", "value": ec["disagree"]},
            {"count": "twin pairs with all reports", "value": tw["n"]},
            {"count": "top-1 differs, original vs twin, same pairs", "value": tw["twin_changed"]},
        ]), hide_index=True, width="stretch")
        st.caption(e1["label"] + ". Reported next to the safety counts, never in place of them: the original-vs-twin "
                   "changes could not be separated from run-to-run noise.")

with st.expander("Slices"):
    st.dataframe(pd.DataFrame([{"arm": arm, **s} for arm, rows in a["slices"].items() for s in rows]),
                 hide_index=True, width="stretch")
