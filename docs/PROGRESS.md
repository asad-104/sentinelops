# SentinelOps progress

## Current milestone
**Viewer page 1 (M1 scenario explorer).** Implemented and tested on branch `viewer-page-1`, waiting for review. M2a is merged into `main` and pushed. M2b (report contract, baselines, harness, first dev numbers) has not started.

## Completed milestones
- **M1: simulator, read-only tools, tests.** Verified 2026-10-22, 73 tests passing.
  - The first pass diverged from the decided design (6 services including a database service, 4 fault types, no prompt injection, tools raised exceptions). It was aligned within the same milestone.
- **M2a: tiers and split.** Verified 2026-10-22, 93 tests passing. Merged into `main` (6ef60fc) and pushed.
- **Viewer page 1: M1 scenario explorer.** Verified 2026-10-22, 113 tests passing (20 viewer tests). Not yet merged.

## Decisions made
| Decision | Reason |
|---|---|
| 4 services, no DB service; pool health is `db_pool_utilization_pct` on auth/orders/payments | Decided design; keeps the system small while still allowing pool faults |
| Auth and payments have external dependencies (identity-provider, card-processor) that appear only in timeout logs | Every service with a timeout setting needs something to time out against; keeps the 4-service graph |
| Scenarios stored as JSON/JSONL files, not a database | Deterministic, diffable, zero setup and cost; data volume is small |
| One `random.Random` per scenario, seeded from a string of (version, seed, index) | String seeding is stable across runs and independent of `PYTHONHASHSEED` |
| Fault types assigned in shuffled balanced blocks | Equal class counts without the fault being derivable from the index |
| Opaque scenario IDs (`sc-` + hash) | IDs reveal neither seed, index nor fault |
| Source IDs assigned after merge-and-sort | The position of an ID reveals nothing about the fault |
| Trigger chosen uniformly from already-drawn changes | Makes real and red-herring changes identically distributed by construction (standard tier) |
| Config trigger gets a harmful value | Legitimate diagnostic signal; documented as the only intended difference |
| Alert fires on the first post-onset breach of a 5-minute average, ~70% on a non-root service when one breaches | Realistic; the alerting service is often not the answer |
| Prompt injection in ~40% of scenarios, same template as benign payload logs, always claiming a wrong diagnosis | Tests that an investigator treats logs as data; a correct claim would reward obeying it |
| `ToolSet.call` returns structured errors and never raises | An agent loop must be able to recover from bad calls |
| Truncation keeps the earliest matches and reports `total_matches` | Simple and predictable; the agent narrows the window to page |
| argparse instead of typer for the CLI | No dependency needed for a handful of flags |
| **M2a:** No maximum time span per tool call; every list tool has a capped `limit` and `truncated`, and single-item tools return at most one item | User decision. A span cap only forces extra calls; output is already bounded. Call budget is enforced by the harness and agent |
| **M2a:** Keep gateway-heavy alerts and report an `alert_service` floor | User decision. Realistic, and the floor makes the weakness visible |
| **M2a:** A too-small `db.pool_max` stays `config_error` | User decision. The cause is the change and the remediation differs (revert vs fix leak) |
| **M2a:** Held-out-only 4th phrasing for every template | Tests whether rules or prompts tuned on dev strings generalise; without it held-out would reuse dev wording |
| **M2a:** Held-out trigger lag 1–12 min vs dev 1–6 min | Tests whether timing thresholds tuned on dev generalise |
| **M2a:** Ambiguous tier = 40% fault-log rate + one red herring moved to 1–6 min before onset on an affected service | "Nearest change before onset" stops being a free answer. This breaks absolute-timing similarity in that tier only; the KS test runs on the standard tier |
| **M2a:** Missing-evidence tier = root logs *or* metrics removed for [onset−5, onset+20] min, applied before ID assignment | IDs stay contiguous, so the gap is detectable only by absence, not by missing ID numbers |
| **M2a:** Alert still computed from the full series in the missing-evidence tier | Models a separate alerting pipeline; documented in the README |
| **M2a:** Dev 40 (4/2/2 per fault), held-out 60 (6/3/3), seeds 1001 / 2002 | Roadmap sizes; balanced fault × tier cells |
| **M2a:** Manifest holds scenario IDs and a SHA-256 over all files, but no per-scenario fault or tier | Detects any generator change; fault and tier are ground truth |
| **M2a:** `ToolSet.tool_input_models` exposed publicly | Needed for the bounds test now and for LLM tool schemas in M3 |
| **Viewer:** `streamlit==1.65.0` in the existing `.venv`, listed in `requirements-viewer.txt` | User decision. One minor version behind the latest (1.66.1). The venv grew from 45 MB to 406 MB. An AST test keeps `streamlit`/`pandas` out of `sentinelops/` |
| **Viewer:** every panel is a `ToolSet.call`; ground truth only in a closed "Reveal answer (dev only)" expander read as plain JSON | The page shows the investigator's view; the answer is opt-in and never imports the simulator |
| **Viewer:** log text only in dataframes / code blocks, never markdown or HTML | Log content is untrusted. Tested with a `**bold** <script>` line |
| **Viewer:** window start for the log time slider taken from the first gateway metric point | Tools don't expose the window. Every service reports a metric at minute 0, so this is exact. A `get_window` tool would be cleaner but changes the tool set |

## Held-out freeze rule
- The held-out split may be regenerated, and its manifest refrozen, **until the first `--final` evaluation run**. Each refreeze must be noted here with a date and reason.
- After the first `--final` run, any generator change that alters held-out data creates a **new held-out version** (`eval/manifests/heldout-v<N>.json`). Earlier results stay labelled with the version they ran on and are never silently compared with newer ones.
- Held-out contents are never printed or inspected during development. Generating the split prints only a count and hash, and tests compare only counts, booleans and hashes.

Freeze log:
- 2026-10-22: dev and held-out first frozen at generator version 3 (M2a).

## Pre-registered expectation (written 2026-10-22, before any baseline numbers exist)
The rule baseline will score well on dev standard, lower on dev ambiguous and missing-evidence, and lose some accuracy on held-out because of the fourth phrasing.

## Baseline tuning log
Every change to the rule baseline's keywords or thresholds is recorded here with a date and reason. Tuning uses dev data only.

| Date | Change | Reason |
|---|---|---|
| _none yet_ | | |

## Local viewer (standing rule, no code yet)
Every milestone ends with a new page in a local Streamlit viewer (`app/viewer.py`, one page per milestone). The viewer is read-only and local only. It reads dev data only and never loads held-out scenarios, reuses `ToolSet` and the existing loaders, and holds no business logic. Streamlit goes in a separate `requirements-viewer.txt`, and installing it needs approval first.

Planned pages:
| Milestone | Page |
|---|---|
| M1 | **Built.** Scenario explorer: alert, timeline, dependencies, metrics (one service or all), log search, record lookup, reveal answer |
| M2 | Tier explorer: tier counts, and the dev results table with floors drawn as reference lines |
| M3 | LLM pilot traces |
| M4 | Agent run viewer: states shown in order, each tool call and the evidence it returned, hypotheses re-ranking as evidence arrives, every claim linked to its source record |
| M5 | Three-way comparison (dev, plus logged final results) |
| M6 | Demo walkthrough. Decide on a polish pass (Plotly or Altair charts, a styled timeline) based on remaining time |

**UI quality bar.** The M2 page must draw floors as reference lines on the results chart. The M4 page must show the states in order, each tool call with its returned evidence, hypotheses re-ranking as evidence arrives, and every claim linked to its source record. M6 decides on a polish pass. The M2 page is owed after M2b.

## Known weaknesses
- With only 4 services, the gateway is upstream of everything and fires half the alerts (101/200, 50%, seed 7 standard set). The alert lands on the root service in 110/200 (55%), so "blame the alerting service" gets the service right about half the time. It will be reported as a floor in M2b.
- Many faults are identifiable from a single distinctive log template (TLS errors → certificate expiry, OOM → memory leak). The ambiguous tier only lowers their rate to 40%; it does not remove them.
- Some symptoms only exist when a fault is present (`db.long_query`, `process.gc_pause`). A keyword baseline can exploit them.
- I wrote the 4th held-out phrasings myself. They are natural paraphrases, but I knew which keywords dev uses, so how hard held-out is depends on choices made by the same author as the future baseline.
- The ambiguous decoy can land on the root service itself. In dev it does in 4 of 10 ambiguous scenarios (40%: 2 certificate expiry, 1 config error, 1 memory leak), and 9 of 10 dev decoys are deployments rather than config changes. A benign deploy just before a memory leak is realistic but genuinely hard, and with 10 ambiguous dev scenarios these placements may dominate the tier's results.
- A config decoy keeps its original service when no affected service can take its key, so not every config decoy is on an affected service. This is tested for deployment decoys only.
- Metrics are smooth and propagation is a fixed halve-per-hop rule; real incidents are messier.
- `internal_error` in `ToolSet.call` is a catch-all that could hide tool bugs, and no test exercises it.
- The viewer adds about 360 MB of dependencies to the shared `.venv`. The import-ban test keeps them out of the core package, but core tests now run in an environment that has pandas installed, so an accidental pandas dependency in a test could go unnoticed.
- The viewer derives the window start from a metric point because `ToolSet` doesn't expose the scenario window.
- The simulator, the future baseline and the prompts are all written by the same author, so co-adaptation is a real risk.

## Open questions
- None blocking M2b. The three M1 questions were decided by the user (see the M2a rows above).

## Next action
User reviews viewer page 1 and decides whether to merge and push. Then start M2b (report contract, `rule_based` baseline, floors `alert_service` / `latest_change` / `keyword_only`, harness with lenient and strict evidence validity and Wilson intervals, first dev numbers) per the approved plan.
