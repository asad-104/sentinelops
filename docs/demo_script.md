# Demo walkthrough (60–90 seconds)

A script for a screen recording of the local viewer. It uses **dev runs only** for the two cases, and the M5 page, which shows fresh-split results as aggregate counts. About 200 spoken words.

**Before recording:**
1. `.venv/bin/streamlit run app/viewer.py` (it opens on `127.0.0.1:8501`).
2. On **M4 · Agent runs**, choose run `generator-v5/mistral-ministral-14b-2512` (the M4 core runs on dev).
3. Open the trace selector once, so the two traces below are a click away.

## Script

| Time | On screen | Say |
|---|---|---|
| 0:00–0:10 | README figure, or the viewer's sidebar | "SentinelOps is an LLM agent that investigates simulated incidents with read-only tools. I tested it against one LLM call over a fixed evidence bundle, and against a rule baseline." |
| 0:10–0:30 | **M4 · Agent runs**, trace `03-sc-3e3ceb314e`. Scroll the state timeline (TRIAGE → GATHER → HYPOTHESIZE → VERIFY → REPORT), then the report's claims table | "A success: payments is leaking memory. The agent gathers logs and metrics, ranks memory leak first, and every claim links to the record it cites." |
| 0:30–0:55 | Same page, trace `12-sc-91404ea5fc`. Show the ranking at HYPOTHESIZE (auth pool exhaustion first), then the tool-call list (only logs and metrics) | "A failure. The real cause is a config change that cut auth's database pool. The agent ranks pool exhaustion first, with high confidence, and never calls a change tool, so it never sees that config change." |
| 0:55–1:20 | **M5 · Headline comparison**: the D1 2×2, then the arms chart | "On sixty fresh scenarios, the single pass beat the agent: right where the agent was wrong sixteen times, against five. The agent also scored below the rule baseline. It's one model on synthetic data, but the failure is specific: it decides before it checks what changed." |
| 1:20–1:30 | The injection panel: the safety counts next to E1 | "In the injection test, answer changes couldn't be separated from run-to-run noise. And the agent can't execute anything: every tool is read-only." |

## Facts behind the script

All taken from committed outputs.

**Run 3, `sc-3e3ceb314e`** (dev, standard tier, M4 core runs):
- **Truth:** payments / memory_leak. **Report rank 1:** payments / memory_leak, confidence high.
- **Calls:** 22 in total (3 loop-issued TRIAGE calls, 14 `search_logs`, 5 `get_metrics`).

**Run 12, `sc-91404ea5fc`** (dev, ambiguous tier):
- **Truth:** auth / config_error, triggered by `CFG-001`.
- **Ranking at HYPOTHESIZE:** auth / connection_pool_exhaustion first. **Report:** rank 1 the same, confidence high; rank 2 auth / config_error, confidence medium.
- **Calls:** 23 in total (16 `search_logs`, 4 `get_metrics`). No change-tool call, so `CFG-001` was never retrieved.
- **PROGRESS records the change** as `db.pool_max` 40 → 3.

**M5:** `eval/m5/generator-v5/m5_analysis.json` and the E1 report (see the README figure and `docs/m4_m5_report.md`).

**Don't show:**
- any fresh-split run or scenario (the viewer doesn't list them);
- any held-out data;
- terminals with keys or environment variables.
