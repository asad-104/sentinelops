# M6 plan (memo, 2026-11-06; nothing built)

M6 is the documentation milestone: README, demo, publish. It adds no new evaluation. The README is for readers of the repo who know ML evaluation but not this project. Every result quoted below comes from [m4_m5_report.md](m4_m5_report.md), and every number in a public file must be copied from there, not retyped from memory.

## (a) README

The current README is stale: it says "Milestone 2 complete" and describes a 15-second suite. M6 rewrites it in this order:

1. **One paragraph:** what SentinelOps is (an evidence-driven incident-investigation agent on a synthetic, author-built benchmark), and what this repo shows.
2. **Headline result,** with its scope in the same paragraph:
   - On 60 fresh synthetic scenarios with one hosted 14B model (`ministral-14b-2512`), a single pass over a fixed evidence bundle beat agent prompt v1 on top-1: 44/60 against 33/60, 16 discordant pairs against 5, exact sign test p = 0.0266.
   - The agent also scored below the rule baseline (38/60).
   - The diagnosis is that the agent ranks hypotheses before it looks at what changed.
   - This is not a result about agents in general, the local 4B model, or real incidents.
3. **Caveats, short list:**
   - synthetic, author-built data and co-adaptation
   - one model, one prompt, one run per arm
   - hosted runs are not repeatable at temperature 0 with seed 0
   - D1 was chosen knowing the dev direction
   - small n

   Each caveat links to its section of the report.
4. **Architecture diagram** (Mermaid, which GitHub renders with no added dependency):
   - simulator → observable files and ground truth (separate)
   - read-only tools → investigators: rule baseline, floors, single-pass, the state-machine agent (TRIAGE → GATHER → HYPOTHESIZE → VERIFY → REPORT, with the context builder and ledger)
   - investigation report → harness and scoring (the only reader of ground truth)
   - mark the trust boundary (log text is untrusted data) and the held-out guard.
5. **Five-minute run without a key** (offline, no paid calls):
   - set up the venv and install the requirements
   - generate the dev split
   - `pytest` (about 3 minutes now)
   - the dev evaluation of the local baselines
   - the mock agent run on a temporary set
   - the viewer, optional; it needs `requirements-viewer.txt`

   **The five-minute target has not been timed on a clean checkout.** If the suite pushes it past five minutes, offer a fast subset (`pytest -m "not slow"`, or a named file list) and say so.
6. **Verified results table:** the "every arm" table from the report (top-1 and top-3 as k/n with Wilson 95%, and valid reports), plus the D1 line. No tier or fault-type table in the README; link to the report.
7. **Safety, in one line, with E1:** the 7/19 top-1 changes could not be separated from run-to-run noise (3/16). Executed actions = 0 holds by design (no action tools).
8. **Repo map and how to reproduce:** where the outputs and the pre-registration live, and the hosted commands. Each hosted command notes that it needs a key and must never be pointed at held-out data.
9. **Limitations and licence.**

## (b) Demo

**M5 viewer page** (`app/pages/m5_comparison.py`), owed under the standing viewer rule:
- **Reads only aggregate files:**
  - `eval/m5/generator-v5/m5_analysis.json`
  - the `counts` blocks of the safety summaries
  - `eval/safety/generator-v5/m5-safety-e1-report/e1.json`, counts only
- **Never reads** fresh-split traces, scenario files, ground truth, or per-scenario rows. A test asserts that the page opens no path under `data/` and no `traces/` directory, and that no scenario ID appears in its output.
- **Shows:**
  - the D1 paired counts (a 2×2 of agent right/wrong against single-pass right/wrong)
  - per-arm top-1 and top-3 with Wilson intervals as a dot-and-interval chart
  - the tier table and the fault-type counts (no intervals)
  - the ablation
  - the agent's process counts (valid change-tool call 0/60, trigger seen 1/24 against single-pass 24/24)
  - the safety counts next to E1, each labelled
- **Not used:** the dev-gate data would only be needed for a per-run drill-down, which the existing M4 page already covers on dev data.
- **Checks:** added to `scripts/check_viewer_real_data.py`, which must print `OK`.

**Walkthrough, 2–3 minutes:**
1. **The question and the setup** (20 s): a synthetic system, hidden ground truth, read-only tools, pre-registration.
2. **One agent run on dev in the M4 page** (60 s): the states in order, the tool calls, the hypotheses ranked at HYPOTHESIZE before any change tool is called, the claims linked to source records.
   - Pick a dev run that shows the failure pattern, for example a config_error miss. Use dev only, never a fresh-split scenario.
3. **The M5 page** (45 s): the D1 2×2, the arms with intervals, config_error 0/12, and the trigger seen 1/24 against 24/24.
4. **Honesty** (30 s): the agent lost; why the comparison isn't like for like; reproducibility (E1); what the next experiment would be (the replicate in Future work).

## (c) Publish checklist

1. **Scan the full history**, every ref and the reflog, for:
   - keys (`sk-`, `gsk_`, `Bearer `, `*_API_KEY=` with a value)
   - org and account IDs (`org_…`)
   - UUIDs in provider errors
   - `.env` content

   **Run it count-only first, then inspect by file and hash, never printing values.** A count-only pre-scan (2026-11-06) found:
   - 0 key patterns
   - one `org_…` value in 3 commits, all in `tests/test_openai_compat.py`; it looks like a hand-written fixture and needs one look by eye to confirm
2. **Amended commits:**
   - The reflog shows 8 amends. Rewritten-away commits are unreachable and are not pushed, but any that reached `origin` before being amended are public already.
   - Check that `origin` holds only reachable history: `origin/main` is at `21d2494`, and `m4-stage-b` was never pushed.
   - Re-scan any amended commit that was pushed.
3. **`.gitignore`:**
   - It ignores `data/`, `.env`, `.venv/`, caches and `.DS_Store`.
   - Confirm that no `data/` file was ever committed (`git log --all -- data/`).
   - Consider ignoring `eval/**/tmp*`, or any scratch output paths.
4. **Must not be committed or published:**
   - keys or `.env`
   - `data/` (any split)
   - held-out scenario content or results (only `eval/manifests/heldout.json`, IDs and hash, is committed)
   - provider account details
   - the scratchpad E2 copy
5. **Decision needed: the committed fresh-split traces.**
   - `eval/agent/.../m5-fresh-*` and `eval/safety/` contain tool results, which means fresh-split log and metric content.
   - Publishing them is a choice. The analysis's integrity doesn't require hiding them: the split is consumed and held-out is separate.
   - Decide before pushing.
6. **Licence:** none exists. Proposal: MIT, or Apache-2.0 for the explicit patent grant. This is the owner's choice.
7. **Branches:**
   - Merge `m4-stage-b` (86 commits ahead of `main`) into `main` after the suite and the viewer check pass.
   - Tag `m4-complete` and `m5-complete` at the right commits.
   - Push only on the owner's explicit go-ahead.
   - Delete the stale feature branches locally afterwards, optionally.
8. **Final check:** run the suite and `scripts/check_viewer_real_data.py`, then review the README's numbers against the report one last time.
