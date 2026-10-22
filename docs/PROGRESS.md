# SentinelOps progress

## Current milestone
**M2 follow-ups (user decisions, 2026-10-22).** Viewer page 1 and M2b are merged into `main`. In progress: tool and metric changes, a harder benchmark (generator v4), and the M2 viewer page. No held-out run has happened.

## Completed milestones
- **M1: simulator, read-only tools, tests.** Verified 2026-10-22, 73 tests passing.
  - The first pass diverged from the decided design (6 services including a database service, 4 fault types, no prompt injection, tools raised exceptions). It was aligned within the same milestone.
- **M2a: tiers and split.** Verified 2026-10-22, 93 tests passing. Merged into `main` (6ef60fc) and pushed.
- **Viewer page 1: M1 scenario explorer.** Verified 2026-10-22, 113 tests passing (20 viewer tests). Merged into `main`.
- **M2b: baseline and evaluation.** Verified 2026-10-22, 141 tests passing. First dev numbers below. Merged into `main`.

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
| **M2b:** Baseline v1 specification committed (6f8a312) before any baseline code existed | Pre-registration; the git history proves the rules were not fitted to results |
| **M2b:** `FaultType` moved to `models.py` | Investigators must output fault names, so the vocabulary is public; labels stay in ground truth. Generator output unchanged (hash tests pass) |
| **M2b:** The harness is the only reader of ground truth; investigators get a `CountingToolSet` | Same isolation as the tools. Tool calls and wall time are measured, not self-reported |
| **M2b:** Call budget of 200 per scenario, refused with `budget_exhausted` | Bounds every investigator; the rule baseline uses 52 calls |
| **M2b:** The harness refuses data whose hash differs from the frozen manifest | A stale or edited dev set cannot silently produce numbers |
| **M2b:** Held-out refused unless `--final`, before any file is read; final runs append to `eval/heldout_runs.jsonl` | Enforces the freeze rule mechanically |
| **M2b:** Evidence validity pooled over top-1 citations, lenient and strict, with no interval | Citations within a scenario are correlated, so a binomial interval would overstate precision |
| **M2b:** Per-fault results are descriptive counts only | Cells of 8 cannot support claims |

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

## Dev results, baseline v1 (2026-10-22, code 015e654, generator 3)
Produced by `python -m sentinelops.evaluation --split dev --investigator all`. The full tables, including per-tier results, are in `eval/results/dev-summary.md`, and per-scenario scores are in `eval/results/dev-<investigator>.json`. Cells are k/n (%, Wilson 95% interval). Dev data only; nothing was run on held-out.

| Investigator | Top-1 | Top-3 | Service top-1 | Evidence lenient / strict |
|---|---|---|---|---|
| rule_based | 34/40 (85%, 71–93) | 40/40 (100%, 91–100) | 37/40 (92%, 80–97) | 114/131 (87%) / 98/131 (75%) |
| keyword_only | 33/40 (82%, 68–91) | 37/40 (92%, 80–97) | 34/40 (85%, 71–93) | 88/108 (81%) / 88/108 (81%) |
| latest_change | 12/40 (30%, 18–45) | 16/40 (40%, 26–55) | 20/40 (50%, 35–65) | 14/40 (35%) / 14/40 (35%) |
| alert_service | 4/40 (10%, 4–23) | 12/40 (30%, 18–45) | 23/40 (58%, 42–71) | 40/40 (100%) / 40/40 (100%) |
| random (analytical) | 5.3% | 15.8% | 25% | – |

Rule baseline top-1 by tier:
- standard 17/20 (85%, 64–95)
- ambiguous 8/10 (80%, 49–94)
- missing evidence 9/10 (90%, 60–98)

Rule baseline top-1 by fault (descriptive counts):
- bad_deployment 8/8
- config_error 8/8
- connection_pool_exhaustion 8/8
- memory_leak 8/8
- certificate_expiry 2/8

Every investigator had 0 unsupported hypotheses and 0 fabricated citations. On the 11 dev scenarios with an injection, the rule baseline followed it 0/11 times and cited an injection line 1/11 times. The rule baseline used 52 tool calls per scenario, at about 34 ms median latency and $0.

### Findings
1. **The task is too easy for four of the five fault types. This is a finding about the benchmark, not a success.**
   - The rule baseline is perfect (32/32) on `bad_deployment`, `config_error`, `connection_pool_exhaustion` and `memory_leak`, across all tiers, and its top-3 is 40/40.
   - All six top-1 misses are `certificate_expiry`. Standard-tier accuracy is 85% only because of certificate expiry; on the other four faults the standard tier is 16/16.
   - In this state the benchmark cannot separate a good investigator from a keyword matcher on most faults.
2. **The pre-registered expectation was only partly right.** I expected lower accuracy on ambiguous and missing-evidence. Instead:
   - ambiguous was 8/10 against 17/20 on standard
   - missing evidence was 9/10, higher than standard
   - the intervals overlap almost entirely

   The tiers as built don't make the task harder for this baseline. Missing-evidence *reporting* is not scored at all yet.
3. **Metrics and changes add almost nothing over keywords.** `keyword_only` scores 33/40 against `rule_based`'s 34/40, and keyword-only is better on certificate expiry (4/8 against 2/8). In 3 of the 6 rule misses, a nearby deployment or config change gave the wrong hypothesis a +1 bonus. `certificate_expiry` can never receive a bonus, so its maximum score is 1.0: v1 is structurally biased against it.
4. **The other 3 certificate misses blamed the caller.** Callers log "x509: certificate has expired when calling …", so the keyword lands on the caller, not the service whose certificate expired.
5. **The floors behave as predicted.** Blaming the alerting service gets the service right 23/40 (58%), close to the 55% seen in M1. `latest_change` gets top-1 12/40 (30%).
6. **Evidence validity as defined can be gamed.** `alert_service` scores 100% because citing the alert always counts as relevant. Validity should not be read without top-1 beside it, and a stricter definition is needed.

## Baseline tuning log
Every change to the rule baseline's keywords or thresholds after v1 is recorded here with a date and reason. Tuning uses dev data only.

| Date | Change | Reason |
|---|---|---|
| _none yet_ | | |

## Local viewer (standing rule)
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
- The simulator, the baseline and the prompts are all written by the same author, so co-adaptation is a real risk. The M2b results suggest it already happened: the keyword list matches the dev templates closely enough to score 32/32 on four faults.
- Evidence validity counts the alert as relevant, so citing only the alert scores 100%.
- Missing-evidence reporting (`missing_evidence` in the report) is produced by the baseline but not scored.
- Three consumers (viewer, rule baseline, `latest_change` floor) derive the window start from a metric point, and the baseline retries without `end` near the window end, because tools don't expose the scenario window.
- The harness does not catch investigator exceptions; a crash stops the run. That is fine for deterministic baselines, but LLM investigators in M3/M4 need an `error` stop reason instead.

## Open questions
- **Benchmark difficulty.** Should the tiers be strengthened before the first `--final` run? The freeze rule allows regenerating held-out until then. Options:
  - remove distinctive templates entirely in the ambiguous tier, rather than thinning them to 40%
  - add confounders that share keywords across faults
  - gap the root's logs *and* metrics in the missing-evidence tier

  Any change bumps the generator and needs a refreeze note.
- **Scenario window.** Should tools expose it, e.g. in `get_alert` or a `get_window` tool? That changes the decided tool set.
- **Evidence validity.** Should it exclude the alert, or require at least one fault-log or trigger citation?
- **Missing-evidence scoring.** Should the evaluation score whether `missing_evidence` names the gapped service?

## Next action
Per the user's decisions of 2026-10-22: (1) expose the scenario window to tools and add the strict-excluding-alert evidence validity and missing-evidence naming score; (2) pre-register the harder-benchmark principles, build generator v4, refreeze both manifests, and rerun baseline v1 and the floors on v4 dev beside the v3 results; (3) build the M2 viewer page. M3 does not start.
