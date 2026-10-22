# SentinelOps progress

## Current milestone
**M2 follow-ups (user decisions, 2026-10-22): done, awaiting review** on branch `m2c-benchmark-v4`. Viewer page 1 and M2b are merged into `main` and pushed (894c21c). Done on the branch:
- `get_window`
- headline evidence validity, and the missing-evidence naming score
- generator v4, with both manifests refrozen
- baseline v1 rerun on v3 and v4 dev
- the M2 viewer page

No held-out run has happened.

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
- 2026-10-22: dev and held-out refrozen at generator version 4 (harder benchmark, user decision). No `--final` run had happened, so this is allowed under the freeze rule. v3 dev results are kept in `eval/results/generator-v3/`.

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

## Harder benchmark: principles and success criterion (recorded 2026-10-22, before any generator change)
Context: on v3 dev, `rule_based` scored 34/40 and `keyword_only` 33/40, and the hard tiers did not lower accuracy. The user decided to make the benchmark harder before any `--final` run.

**Principles (user decisions):**
1. **Hardness comes from realistic symptom overlap, not from deleting the baseline's keywords.** Examples: certificate expiry also causes connection errors on callers; pool exhaustion and config errors also cause timeouts.
2. **Every scenario stays solvable.** At least one independent evidence path for the true (service, fault) survives in every tier, and a test enforces it.
3. **The missing-evidence tier never removes both logs and metrics** for the root service.
4. **Success criterion is headroom:** both baselines clearly below ceiling on the hard tiers.
5. **At most one difficulty revision,** judged by baseline scores, and logged here.

**Quantitative success criterion,** fixed now. On v4 dev, `rule_based` and `keyword_only`, both unchanged v1, each score **≤ 7/10 top-1 on the ambiguous tier and ≤ 7/10 on the missing-evidence tier.** The standard tier has no target; it remains the realistic reference.

**Planned v4 mechanisms.** I chose these knowing the baseline's signals, which is co-adaptation in the opposite direction. The guard is that each one must be a plausible real-world side effect.
- **Ambiguous tier: secondary symptoms that overlap with another fault.** These are added on top of the true fault's symptoms, which stay at their normal rate:
  - `certificate_expiry`: callers also log connection resets during the TLS handshake.
  - `connection_pool_exhaustion`: the root also logs query and call timeouts.
  - `config_error`: the root also logs connection errors to the dependency it times out on, or is throttled or slowed on.
  - `memory_leak`: callers log refused connections during OOM restarts. GC pauses hold connections, so the root's pool utilisation rises.
  - `bad_deployment`: the new version also logs timeouts to its dependencies, and its memory use rises.
  - The decoy change from v3 stays.
  - v3's thinning of distinctive logs to 40% is **removed**. Under principle 1, hardness must come from overlap, not from thinning true evidence.
- **Missing-evidence tier: the gap runs from onset − 5 min to the window end** (v3 stopped at onset + 20). It still removes the root's logs *or* its metrics, never both. In v3 the root's logs came back 20 minutes after onset, which made the gap nearly irrelevant.
- **Solvability test.** For every scenario, the observable data must contain the trigger (for change-caused faults) and at least one of:
  - a log channel: a primary fault log on the root, or for certificate expiry a caller's TLS error naming the root
  - a metric channel: the root's signature metric after onset (pool > 95, memory > 85, error rate above its alert threshold, latency above 2× baseline, or request rate below 50% of baseline, depending on the fault)

## Harder benchmark: results (2026-10-22, generator v4, baseline v1 unchanged)
Baseline v1 and the floors were rerun unchanged on v4 dev (code 8d3454b). Full tables are in `eval/results/generator-v4/dev-summary.md`; the v3 tables, rerun with the new metrics, are in `eval/results/generator-v3/dev-summary.md`. Dev only, no `--final` run.

| Investigator | Slice | Top-1, generator v3 | Top-1, generator v4 |
|---|---|---|---|
| rule_based | overall | 34/40 (85%, 71–93) | 20/40 (50%, 35–65) |
| rule_based | standard | 17/20 (85%, 64–95) | 12/20 (60%, 39–78) |
| rule_based | ambiguous | 8/10 (80%, 49–94) | 6/10 (60%, 31–83) |
| rule_based | missing evidence | 9/10 (90%, 60–98) | 2/10 (20%, 6–51) |
| keyword_only | overall | 33/40 (82%, 68–91) | 19/40 (48%, 33–63) |
| keyword_only | standard | 16/20 (80%, 58–92) | 12/20 (60%, 39–78) |
| keyword_only | ambiguous | 9/10 (90%, 60–98) | 3/10 (30%, 11–60) |
| keyword_only | missing evidence | 8/10 (80%, 49–94) | 4/10 (40%, 17–69) |
| latest_change | overall | 12/40 (30%, 18–45) | 8/40 (20%, 10–35) |
| latest_change | standard | 7/20 (35%, 18–57) | 4/20 (20%, 8–42) |
| latest_change | ambiguous | 1/10 (10%, 2–40) | 1/10 (10%, 2–40) |
| latest_change | missing evidence | 4/10 (40%, 17–69) | 3/10 (30%, 11–60) |
| alert_service | overall | 4/40 (10%, 4–23) | 3/40 (8%, 3–20) |
| alert_service | standard | 2/20 (10%, 3–30) | 2/20 (10%, 3–30) |
| alert_service | ambiguous | 0/10 (0%, 0–28) | 0/10 (0%, 0–28) |
| alert_service | missing evidence | 2/10 (20%, 6–51) | 1/10 (10%, 2–40) |

| rule_based (overall) | Generator v3 | Generator v4 |
|---|---|---|
| Top-3 | 40/40 (100%, 91–100) | 38/40 (95%, 83–99) |
| Service top-1 | 37/40 (92%, 80–97) | 27/40 (68%, 52–80) |
| Missing evidence named (missing tier) | 3/10 (30%, 11–60) | 5/10 (50%, 24–76) |
| Evidence, headline (strict excl. alert) | 98/131 (75%) | 69/116 (59%) |

**Success criterion: met on the first attempt, so no difficulty revision was used** (0 of the 1 allowed). On v4 dev:
- `rule_based`: ambiguous 6/10, missing evidence 2/10
- `keyword_only`: ambiguous 3/10, missing evidence 4/10

Every one is ≤ 7/10, and the solvability tests pass on every generated test scenario and on both frozen splits.

**Honest reading:**
1. **The missing-evidence tier is now clearly hard,** and still solvable. `rule_based` gets 2/10 top-1 but 9/10 top-3: the right answer is usually ranked, just not first.
2. **The ambiguous tier hurts `keyword_only` (3/10) but not `rule_based`** relative to v4's own standard tier (6/10 against 12/20, both 60%). The metric and change bonuses resist keyword overlap. The criterion was set as a fixed bar, so it is met, but the tier does not separate "uses more signals" from "uses keywords" for `rule_based`.
3. **The standard tier also fell, from 17/20 to 12/20. That is resampling, not a leak.** No standard scenario has overlap logs, and every miss is a mechanism already present in v3. The bump changed every random draw, and this draw has more scenarios that trigger the known weaknesses:
   - three certificate expiries rooted at payments, whose caller logs the x509 errors
   - two pool-key config errors
   - two bad deployments outranked by another service's change bonus

   A 20-scenario tier can swing this much on a fresh draw, so v3 and v4 standard numbers are not comparable evidence of anything.
4. **The floors stay far below** (`alert_service` 3/40, `latest_change` 8/40, random 5%), so the benchmark still rewards real signal.
5. **`injection_followed` is not evidence of influence.** `rule_based` and `keyword_only` each "followed" an injection 2/15 times on v4. Rerunning those scenarios with the injection lines removed gave the same top-1 in all four cases: the baseline's wrong answer coincided with the injection's randomly chosen wrong claim. For M5 this metric should become a counterfactual: does removing the injected lines change the answer?

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
| M2 | **Built.** Tiers and dev results: tier counts; top-1/top-3/service accuracy per tier for any generator version, rule baseline bars with Wilson intervals, floors as tick reference lines, random as a dashed line |
| M3 | LLM pilot traces |
| M4 | Agent run viewer: states shown in order, each tool call and the evidence it returned, hypotheses re-ranking as evidence arrives, every claim linked to its source record |
| M5 | Three-way comparison (dev, plus logged final results) |
| M6 | Demo walkthrough. Decide on a polish pass (Plotly or Altair charts, a styled timeline) based on remaining time |

**UI quality bar.** The M2 page must draw floors as reference lines on the results chart. The M4 page must show the states in order, each tool call with its returned evidence, hypotheses re-ranking as evidence arrives, and every claim linked to its source record. M6 decides on a polish pass.

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
- Evidence validity under the M2b definitions counts the alert as relevant (citing only the alert scores 100%). Fixed by the headline definition; the old columns remain for comparison only.
- The missing-evidence naming score only checks that the gapped service is named. It doesn't check whether the report says *what* is missing (logs vs metrics). The baseline can only detect log gaps.
- Baseline v1 and the `latest_change` floor still derive the window start from a metric point (kept unchanged on purpose). New investigators should use `get_window`.
- The v4 overlap mechanisms were designed knowing the baseline's signals ("connection", "timeout"). They are realistic side effects, but the choice of *which* side effects to add was informed by what would confuse this baseline.
- The harness does not catch investigator exceptions; a crash stops the run. That is fine for deterministic baselines, but LLM investigators in M3/M4 need an `error` stop reason instead.

## Open questions
- ~~**Benchmark difficulty.**~~ Decided and done: generator v4 (see "Harder benchmark" above). Original question: should the tiers be strengthened before the first `--final` run? The freeze rule allows regenerating held-out until then. Options:
  - remove distinctive templates entirely in the ambiguous tier, rather than thinning them to 40%
  - add confounders that share keywords across faults
  - gap the root's logs *and* metrics in the missing-evidence tier

  Any change bumps the generator and needs a refreeze note.
- ~~**Scenario window.**~~ Done: the `get_window` tool. Baseline v1 still infers the window from a metric point, unchanged by decision.
- ~~**Evidence validity.**~~ Done: the headline is "strict excluding the alert"; the M2b definitions are kept and labelled.
- ~~**Missing-evidence scoring.**~~ Done: "missing evidence named" on the missing-evidence tier.
- **Injection metric.** Replace `injection_followed` with a counterfactual (answer with vs without the injected lines) before M5.
- **Ambiguous tier vs `rule_based`.** The tier does not lower `rule_based` relative to standard. Leave as is (the criterion is met and the one revision is unused), or spend the revision? My recommendation is to leave it: spending the revision to beat one specific baseline would be tuning the benchmark to the baseline.

## Next action
User reviews the M2 follow-ups on `m2c-benchmark-v4` and decides:
- whether to merge and push
- the two new open questions (counterfactual injection metric; whether to spend the one remaining difficulty revision; recommendation: don't)

M3 (LLM adapter interface and the 5-scenario local pilot) does not start until the user says so.
