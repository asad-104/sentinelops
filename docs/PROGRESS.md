# SentinelOps progress

## Current milestone
**M2a: difficulty tiers, dev/held-out split, frozen manifests.** Implemented and tested on branch `m2a-tiers-split`, waiting for review. M2b (report contract, baselines, harness, first dev numbers) has not started.

## Completed milestones
- **M1: simulator, read-only tools, tests.** Verified 2026-10-22, 73 tests passing.
  - The first pass diverged from the decided design (6 services including a database service, 4 fault types, no prompt injection, tools raised exceptions). It was aligned within the same milestone.
- **M2a: tiers and split.** Verified 2026-10-22, 93 tests passing. Not yet merged.

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

## Held-out freeze rule
- The held-out split may be regenerated, and its manifest refrozen, **until the first `--final` evaluation run**. Each refreeze must be noted here with a date and reason.
- After the first `--final` run, any generator change that alters held-out data creates a **new held-out version** (`eval/manifests/heldout-v<N>.json`). Earlier results stay labelled with the version they ran on and are never silently compared with newer ones.
- Held-out contents are never printed or inspected during development. Generating the split prints only a count and hash, and tests compare only counts, booleans and hashes.

Freeze log:
- 2026-10-22: dev and held-out first frozen at generator version 3 (M2a).

## Pre-registered expectation (written 2026-10-22, before any baseline numbers exist)
The rule baseline will score well on dev standard, lower on dev ambiguous and missing-evidence, and lose some accuracy on held-out because of the fourth phrasing.

## Baseline specification v1 (recorded 2026-10-22, before any baseline code was run)
The signatures and thresholds below are exactly as planned in the approved M2 plan. Where the plan left something unspecified, I fixed it here before seeing any results, so it cannot be adjusted silently afterwards.

**Inputs.** The baseline uses `ToolSet.call` only.
- `t_a` is the alert timestamp.
- The lookback start is `max(window start, t_a − 30 min)`. The window start is taken from the first gateway metric point, because tools don't expose the window.

**Keyword signatures** (case-insensitive `contains`, per service, from the lookback start to the window end). Each keyword's count is the tool's `total_matches`, so truncation does not matter.

| Fault | Keywords |
|---|---|
| `bad_deployment` | `exception` |
| `connection_pool_exhaustion` | `connection` |
| `certificate_expiry` | `certificate`, `x509` |
| `memory_leak` | `gc pause`, `memory` |
| `config_error` | `timeout`, `rate limit`, `cache miss` |

**Metric thresholds** (maximum value from the lookback start to the window end):
- `db_pool_utilization_pct` > 95 supports `connection_pool_exhaustion` on that service.
- `memory_pct` > 85 supports `memory_leak` on that service.

**Changes** in [lookback start, `t_a`]:
- A deployment on a service supports `bad_deployment` on that service.
- A config change on a service supports `config_error` on that service, if the keyword matching its key has more than zero matches on that service. The key-to-keyword mapping:
  - `http_client.timeout_ms` → `timeout`
  - `rate_limit.rps` → `rate limit`
  - `cache.ttl_seconds` → `cache miss`
  - `db.pool_max` → `connection`

**Score per (service, fault):**
- Start with keyword evidence: `min(sum of keyword matches, 20) / 20`, so between 0 and 1.
- Add **+1** if the fault's metric threshold is breached on that service.
- Add **+1** if a supporting change exists on that service.
- Pairs scoring 0 are dropped. The rest are ranked by score, ties broken by service order (gateway, auth, orders, payments) then fault order (as listed in `FaultType`), and the top 3 are reported.
- If nothing scores above 0, the baseline reports one hypothesis: (alert service, `bad_deployment`), with low confidence.

**Confidence** is a qualitative label, not a probability:
- Top hypothesis: `high` if its score is ≥ 1.5 and it leads the second by ≥ 0.5.
- Any hypothesis: `medium` if its score is ≥ 0.75, otherwise `low`.

**Stop reason:** `sufficient_evidence` if the top score is ≥ 1, otherwise `no_new_evidence`.

**Citations:**
- up to 2 matching log IDs per keyword
- the breaching metric point
- the supporting change

**Missing evidence:** a service with zero logs in [`t_a` − 5 min, `t_a` + 5 min] while another service has logs in that window.

**Injection lines are not special-cased.**

**Floors** are reported beside the rule baseline:
- `alert_service`: (alert service, faults in alphabetical order), top 3.
- `latest_change`: the most recent deployments and config changes before `t_a`, newest first, each mapped to `bad_deployment` or `config_error`, top 3.
- `keyword_only`: the keyword evidence above, with no metric or change bonuses.
- Random guessing, reported analytically: 1/19 top-1, 3/19 top-3, 1/4 service.

## Baseline tuning log
Every change to the rule baseline's keywords or thresholds after v1 is recorded here with a date and reason. Tuning uses dev data only.

| Date | Change | Reason |
|---|---|---|
| _none yet_ | | |

## Local viewer (standing rule, no code yet)
Every milestone ends with a new page in a local Streamlit viewer (`app/viewer.py`, one page per milestone). The viewer is read-only and local only. It reads dev data only and never loads held-out scenarios, reuses `ToolSet` and the existing loaders, and holds no business logic. Streamlit goes in a separate `requirements-viewer.txt`, and installing it needs approval first.

Planned pages:
| Milestone | Page |
|---|---|
| M1 | Scenario browser: alert, timeline, log search through `ToolSet` |
| M2 | Tier explorer and dev results table (floors beside the rule baseline) |
| M3 | LLM pilot traces |
| M4 | Agent run trace |
| M5 | Three-way comparison (dev, plus logged final results) |
| M6 | Demo walkthrough |

The M1 and M2 pages are owed. Streamlit is not installed, and no viewer code was written in M2a.

## Known weaknesses
- With only 4 services, the gateway is upstream of everything and fires half the alerts (101/200, 50%, seed 7 standard set). The alert lands on the root service in 110/200 (55%), so "blame the alerting service" gets the service right about half the time. It will be reported as a floor in M2b.
- Many faults are identifiable from a single distinctive log template (TLS errors → certificate expiry, OOM → memory leak). The ambiguous tier only lowers their rate to 40%; it does not remove them.
- Some symptoms only exist when a fault is present (`db.long_query`, `process.gc_pause`). A keyword baseline can exploit them.
- I wrote the 4th held-out phrasings myself. They are natural paraphrases, but I knew which keywords dev uses, so how hard held-out is depends on choices made by the same author as the future baseline.
- The ambiguous decoy can land on the root service itself. In dev it does in 4 of 10 ambiguous scenarios (40%: 2 certificate expiry, 1 config error, 1 memory leak), and 9 of 10 dev decoys are deployments rather than config changes. A benign deploy just before a memory leak is realistic but genuinely hard, and with 10 ambiguous dev scenarios these placements may dominate the tier's results.
- A config decoy keeps its original service when no affected service can take its key, so not every config decoy is on an affected service. This is tested for deployment decoys only.
- Metrics are smooth and propagation is a fixed halve-per-hop rule; real incidents are messier.
- `internal_error` in `ToolSet.call` is a catch-all that could hide tool bugs, and no test exercises it.
- The simulator, the future baseline and the prompts are all written by the same author, so co-adaptation is a real risk.

## Open questions
- None blocking M2b. The three M1 questions were decided by the user (see the M2a rows above).

## Next action
User reviews M2a and decides whether to merge and push. Then start M2b (report contract, `rule_based` baseline, floors `alert_service` / `latest_change` / `keyword_only`, harness with lenient and strict evidence validity and Wilson intervals, first dev numbers) per the approved plan.
