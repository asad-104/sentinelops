# SentinelOps progress

## Current milestone
**M3 stage A: complete** (approved and merged into `main` on 2026-10-23). **Stage B** (the first real local run) is in progress on `m3-stage-b`. The plan is in `docs/M3_PLAN.md`, on branch `m3-plan`.
- **What stage A added:** an LLM client interface, a scripted mock, the Ollama client (never run against a server), tool schemas, the tool loop, JSONL traces, crash-catching in the harness, the pilot CLI, the network guard and the M3 viewer page.
- **What has not happened:** no model has been pulled or called, nothing was installed, and nothing touched the network except the two D1 page fetches.
- **Mock traces:** the committed traces in `eval/pilot/generator-v5/mock-scripted/` come from a scripted policy, not a model.
- **Stage B** (first real local run) needs approval.

**M2 is complete (2026-10-22).** All of it is merged into `main`: tiers, split, baseline, harness, generator v5 with paired twins and ablation, and the M2 viewer page. **M3 planning is approved but not started**; no M3 code exists. No held-out run has happened.

**M2 findings (dev only, synthetic, author-built data):**
1. Baseline v1 was too easy for generator v3: `rule_based` 34/40, and even `keyword_only` 33/40.
2. Generators v4 and v5 added headroom. Both baselines scored ≤ 7/10 on each hard tier, against the pre-registered criterion, met on the first attempt with 0 of 1 revisions used.
3. The differences between `keyword_only` and `rule_based` are within the Wilson intervals on every version. v5 overall: 21/40 (37–67) vs 25/40 (47–76).
4. In the paired ablation, overlap hurts keyword matching (`keyword_only` 5 of 10 hurt, `rule_based` 0), and the gap hurts both log readers (3 of 10 each).
5. Injection had no effect on any baseline: 0 of 12 paired answers changed for all four investigators.

## Completed milestones
- **M1: simulator, read-only tools, tests.** Verified 2026-10-22, 73 tests passing.
  - The first pass diverged from the decided design (6 services including a database service, 4 fault types, no prompt injection, tools raised exceptions). It was aligned within the same milestone.
- **M2a: tiers and split.** Verified 2026-10-22, 93 tests passing. Merged into `main` (6ef60fc) and pushed.
- **Viewer page 1: M1 scenario explorer.** Verified 2026-10-22, 113 tests passing (20 viewer tests). Merged into `main`.
- **M2b: baseline and evaluation.** Verified 2026-10-22, 141 tests passing. First dev numbers below. Merged into `main`.
- **M2 follow-ups:** `get_window`, headline evidence, generator v4, M2 viewer page. Verified 2026-10-22, 176 tests passing. Merged into `main` (6d9a943) and pushed.
- **M3 stage A: LLM adapter, tool loop, pilot CLI, network guard, M3 viewer page.** Verified 2026-10-23: 277 tests passing, and the viewer renders against real data. Merged into `main`.
- **M2 complete: generator v5, paired twins, tier ablation, viewer fix.** Verified 2026-10-22, 201 tests passing, and the viewer renders against real data (`scripts/check_viewer_real_data.py`). Merged into `main` and pushed.

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
| **M3:** LLM clients return `LLMResponse \| LLMError` and never raise | The loop handles model failures the way it handles tool failures (`ok=False`), with no try/except around calls |
| **M3:** Tool specs are generated from `TOOL_INPUT_MODELS` (now a module constant in `toolset.py`, used by the registry) | What the model is told and what `ToolSet.call` validates cannot drift apart. Investigators only get a `ToolCaller`, so schemas must not need a scenario |
| **M3:** A run with no valid report raises `InvestigationFailed(stop_reason)`, and the harness records an error row (scored as wrong, never dropped). Only `HarnessAbort` stops a whole run | No report is ever invented. A crash or a stuck model can't stop or silently shrink an evaluation |
| **M3:** The loop fetches the alert itself (1 of the 30 calls) and puts it in the first user message as data | It saves the small model a turn. The fetch is counted and traced, and excluded from the valid-call share, which is about the model's own calls |
| **M3:** `submit_report` doesn't consume the 30-call read budget, but it counts toward the valid-call share | The budget bounds evidence gathering. A valid report is part of using tools correctly |
| **M3:** Text-only model replies count toward the 3-in-a-row malformed streak | Otherwise a model that only chats would run until the turn cap |
| **M3:** Frozen prompt sha256 `0f97fb44c2549794f7ba1be577d8d01392422e30b8752f4fd2ba640a88c2d2ea`, pinned by `test_prompt_is_frozen` | Change 3. Any revision changes the hash, fails the test, and must be logged here first |
| **M3:** Memory signals come from `sysctl kern.memorystatus_vm_pressure_level` (1 normal, 2 warn, 4 critical) and `vm.swapusage` | The `memory_pressure` command named in the plan *applies* memory pressure (`man memory_pressure`), so it is never run. A test asserts only `sysctl` is called |
| **M3:** Free disk is checked in decimal GB (`shutil.disk_usage`), not the GiB that `df -h` shows | 10 GB decimal is about 9.3 GiB, so the guard is slightly looser than `df` would suggest. Recorded so the two aren't confused |
| **M3:** The mock backend's verdict is "not applicable" | A scripted policy can't pass or fail model thresholds. The rule's raw value is kept under `mechanics_check_only` |
| **M3 stage B:** progress display added in commit `517df7a`: plain text on stderr, one line per model turn (run k/N and scenario, turn, tool calls of 30, elapsed, swap, free disk) and one per run (stop reason, wall time); `--quiet` turns it off | Long local runs need visible progress. It is display only: `test_progress_display_changes_no_output_file` shows the traces, summary and run log are byte-identical with it on and off, and the prompt hash is unchanged. Added before the 7 runs started |
| **M3:** The network guard patches `socket` at conftest import and raises a non-`OSError` `NetworkBlocked`; Unix-domain sockets are allowed | Covers session fixtures too, and HTTP clients can't turn it into an ordinary connection error. Local IPC (event loops) still works |
| **v5:** One seeded stream per mechanism (injection, overlap, decoy, gap) plus a base stream; every log line rendered from a sub-stream seeded by one 64-bit draw | Turning one mechanism off must not shift any other draw. Without per-line sub-streams, `rng.choice` over service-dependent lists consumes a variable number of draws |
| **v5:** Gap applied after rendering; alert's random choice drawn unconditionally | Same reason: the base stream's position must not depend on which records a mechanism removes or which services breach |
| **v5:** Injection twins written with each split under `twins/`, covered by the content hash | Final held-out runs need twins without regenerating held-out in the harness; the hash freezes them with the split |
| **v5:** Twins keep the original scenario ID; ground truth records `mechanisms_off` | Pairing is by ID; the twin's own answer key states what was removed |
| **v5:** Twin runs get their own call budget and are excluded from tool-call and latency metrics | Those metrics describe one investigation; twin cost is reported separately in M3 cost estimates |
| **Viewer fix:** `dev_results` loads only files shaped like investigator results and names every skipped file; the ablation file gets its own panel; malformed ground-truth files raise `ViewerDataError`. A real-data render (`scripts/check_viewer_real_data.py`) is a standing check before any milestone is done | The M2 page crashed with `KeyError: 'summary'` on the real v5 folder, because `dev-ablation.json` matches `dev-*.json`. Its tests used fixtures without that file, and the page was never rendered on real data |
| **v5:** Tier ablation generated in memory, dev only, after checking every regenerated original equals the frozen file on disk | The ablation is analysis, not a benchmark split; no ablated data is stored or frozen, and held-out can't be ablated (no split argument) |

## Held-out freeze rule
- The held-out split may be regenerated, and its manifest refrozen, **until the first `--final` evaluation run**. Each refreeze must be noted here with a date and reason.
- After the first `--final` run, any generator change that alters held-out data creates a **new held-out version** (`eval/manifests/heldout-v<N>.json`). Earlier results stay labelled with the version they ran on and are never silently compared with newer ones.
- Held-out contents are never printed or inspected during development. Generating the split prints only a count and hash, and tests compare only counts, booleans and hashes.

Freeze log:
- 2026-10-22: dev and held-out first frozen at generator version 3 (M2a).
- 2026-10-22: dev and held-out refrozen at generator version 4 (harder benchmark, user decision). No `--final` run had happened, so this is allowed under the freeze rule. v3 dev results are kept in `eval/results/generator-v3/`.
- 2026-10-22: dev and held-out refrozen at generator version 5 (independent mechanism streams and injection twins, user decision). No `--final` run had happened. The tier mechanisms are unchanged in intent, but every draw is new. v4 dev results are kept in `eval/results/generator-v4/`. Dev sha256 `5a35c45a…`, held-out `29bab634…`. The held-out freeze printed only count and hash.

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

## Paired twins and tier ablation: goal and criterion (recorded 2026-10-22, before any generator change)
Context: v4's `injection_followed` turned out to be coincidence (see reading 5 above), and v4's tier effects can't be separated from resampling (reading 3). User decision: make the generator change now, and only now.

**Goal**
1. **Injection twins.** For every scenario with injected lines, a twin that is the same scenario with only those lines removed. No other random draw shifts.
2. **Paired tier ablation (dev only).** The same scenarios with each tier mechanism turned off, compared with the original where it is on:
   - ambiguity overlap symptoms
   - the decoy change
   - the missing-evidence gap

**Implementation, fixed now**
- **Separate streams.** Each mechanism (injection, overlap, decoy, gap) gets its own random-number stream, seeded from (version, seed, index, mechanism name). Everything else stays on the base stream.
- **Per-event rendering.** Every log line is rendered with its own sub-stream, seeded by one fixed-size draw from its mechanism's stream. A different service or template then can't change how many base draws are consumed.
- **Gap applied after rendering.** Events are rendered first, then the gap filter removes the root's logs.
- **Alert choice pre-drawn.** The alert's random choice is drawn unconditionally.
- **Test.** For each mechanism, generate on and off for many seeds, faults and tiers. The two must be identical apart from that mechanism's own records (source IDs renumber). Where the mechanism changes derived values, such as overlap deltas changing which alert fires, the test exempts exactly those values and documents why.
- **Versioning.** Bump `GENERATOR_VERSION` to 5 and refreeze both manifests. Injection twins are written with each split under `twins/` and are covered by the content hash.
- **Baselines unchanged.** Baseline v1 and the floors are rerun unchanged on v5 dev.

**Metrics**
- **Injection.** `injection_followed` is replaced by two paired metrics over scenarios with an injection:
  - *answer changed*: the top-1 differs between original and twin
  - *changed to claim*: it changed, and the original's top-1 is the injection's claimed diagnosis
- **Ablation.** For each mechanism and investigator, report:
  - n affected
  - unchanged answers
  - both correct and both wrong
  - correct only without the mechanism
  - correct only with it

**Criterion, fixed now**
- Paired flips are reported as counts, together with the unchanged scenarios. No pass or fail threshold is set for them; they are descriptive.
- The v4 headroom criterion is re-checked on v5 dev: `rule_based` and `keyword_only` each ≤ 7/10 top-1 on the ambiguous tier and ≤ 7/10 on the missing-evidence tier. The result is reported as is. **If it fails, nothing is tuned.** The one difficulty revision is not spent (user decision: no further revisions).
- v5 is a fresh draw of every scenario, so v4 and v5 aggregate numbers differ partly by resampling. Only the paired numbers within v5 isolate a mechanism.
- Time-box: 4 h. If it will be exceeded, drop the tier ablation and keep only the injection twins.

## Paired twins and tier ablation: results (2026-10-22, generator v5, baseline v1 unchanged)
Code e8c9279, dev only, no `--final` run. Full tables:
- `eval/results/generator-v5/dev-summary.md`
- `eval/results/generator-v5/dev-ablation.md`

**v4 vs v5 top-1, by version.** Each version is a fresh draw, so these are separate samples, not paired measurements.

| Investigator | Slice | Generator v4 | Generator v5 |
|---|---|---|---|
| rule_based | overall | 20/40 (50%, 35–65) | 25/40 (62%, 47–76) |
| rule_based | standard | 12/20 (60%, 39–78) | 15/20 (75%, 53–89) |
| rule_based | ambiguous | 6/10 (60%, 31–83) | 6/10 (60%, 31–83) |
| rule_based | missing evidence | 2/10 (20%, 6–51) | 4/10 (40%, 17–69) |
| keyword_only | overall | 19/40 (48%, 33–63) | 21/40 (52%, 37–67) |
| keyword_only | standard | 12/20 (60%, 39–78) | 14/20 (70%, 48–85) |
| keyword_only | ambiguous | 3/10 (30%, 11–60) | 3/10 (30%, 11–60) |
| keyword_only | missing evidence | 4/10 (40%, 17–69) | 4/10 (40%, 17–69) |
| latest_change | overall | 8/40 (20%, 10–35) | 10/40 (25%, 14–40) |
| alert_service | overall | 3/40 (8%, 3–20) | 5/40 (12%, 5–26) |

| rule_based (overall) | Generator v4 | Generator v5 |
|---|---|---|
| Top-3 | 38/40 (95%, 83–99) | 37/40 (92%, 80–97) |
| Missing evidence named (missing tier) | 5/10 (50%, 24–76) | 5/10 (50%, 24–76) |
| Evidence, headline | 69/116 (59%) | 66/119 (55%) |
| Injection: v4 unpaired "followed" / v5 paired "changed answer" | 2/15 (not a measure of influence) | 0/12 (0%, 0–24) |

**Headroom criterion re-checked on v5: met.** It is reported as is, and nothing was tuned:
- `rule_based`: ambiguous 6/10, missing evidence 4/10
- `keyword_only`: ambiguous 3/10, missing evidence 4/10

**Paired results on v5 dev.** For each mechanism, the scenarios where it is on are compared with the same scenarios with only that mechanism off. "Hurt" = correct without the mechanism, wrong with it. Across all 16 rows, no answer went from wrong to correct.

| Mechanism | n | rule_based (unchanged / hurt) | keyword_only | latest_change | alert_service |
|---|---|---|---|---|---|
| injection | 12 | 12 / 0 | 12 / 0 | 12 / 0 | 12 / 0 |
| overlap | 10 | 10 / 0 | 5 / 5 | 10 / 0 | 10 / 0 |
| decoy | 10 | 8 / 1 | 10 / 0 | 4 / 2 | 10 / 0 |
| gap | 10 | 7 / 3 | 7 / 3 | 10 / 0 | 10 / 0 |

**Honest reading:**
1. **Injection never changes a baseline's answer** (0/12 for all four). That is expected for keyword rules, and it confirms that v4's 2/15 "followed" was coincidence. The paired metric is built for the M4/M5 agent; on these baselines it has nothing to detect.
2. **Overlap isolates keyword matching exactly.** It costs `keyword_only` 5 of 10 and changes none of `rule_based`'s answers. The metric and change bonuses make `rule_based` immune to the overlap logs, so the ambiguous tier's difficulty for `rule_based` (6/10) comes from the decoy (1 hurt) and from mechanisms that are also present in the standard tier.
3. **The gap costs both log-using baselines 3 of 10.** The floors that don't read logs are unaffected.
4. **The decoy mainly fools `latest_change`.** It changed 6 of 10 of its answers, with 2 hurt; the other 4 changed from one wrong answer to another. It hurt `rule_based` once.
5. **These are counts on n = 10–12.** They show which mechanism acts on which investigator; they are not effect sizes.
6. **Certificate expiry is 0/8 for `rule_based` on both v4 and v5 dev,** across all tiers. I missed this in the v4 write-up. Callers log the TLS errors, so the rules blame the caller. It is a baseline v1 weakness, recorded and not tuned.

## M3 pilot: questions and decision rule (recorded 2026-10-23, before any M3 code)
The full plan is in `docs/M3_PLAN.md`. Dev only; held-out data is never used.

**Fixed pilot set:**
- Runs 1–5 are the first dev scenario of each fault type in manifest order (generator v5, sha256 `5a35c45a…`): `sc-06b280fbed`, `sc-1499febf6f`, `sc-203fe8a4ca`, `sc-2d438d4575`, `sc-32aaf79bfd`.
- Runs 6–7 are an injection probe pair: `sc-4141664f86` and its twin.
- No pilot scenario is ambiguous, so the pilot says nothing about that tier.

**Fixed bounds:**
- 30 tool calls
- 40 model turns
- 180 s per model call (2 consecutive timeouts end the run)
- 20 min per scenario
- a 4,000-character cap on each tool result shown to the model
- `num_ctx` 8192

The pilot's 30-call budget is not the rule baseline's 52 calls. The M4/M5 budget will be pre-registered separately, and any comparison states both budgets.

**Questions, reported as counts:**
1. **Valid tool calls:** valid / all tool calls, pooled over runs. Valid means the call parses, names a known tool, and passes the schema.
2. **Inside budget:** runs ending in `sufficient_evidence`.
3. **Valid reports:** runs whose report validates against `InvestigationReport`, directly or after one repair turn (counted separately).
4. **Real citations:** cited IDs that exist in the scenario / all cited IDs. The 4,000-character cap can hide source IDs from the model.
5. **Top-1:** k/5, descriptive only. Five scenarios cannot support an accuracy claim.

**Also recorded:**
- wall time, tokens, swap growth and memory pressure per run
- whether the model has a thinking mode, how it is configured, and its effect on time and tokens
- the probe pair's answer change
- the SHA-256 of the frozen system prompt and tool descriptions

**Decision rule** (over runs 1–5; top-1 is not part of it):
- **Local is feasible for M4** if all of these hold:
  - valid tool calls ≥ 80%
  - ≥ 4 of 5 runs end in `sufficient_evidence` with a valid report (repair allowed)
  - real citations ≥ 90%
  - median wall time ≤ 10 min per scenario
- **Propose a hosted pilot** if any of these hold:
  - valid tool calls < 60%
  - ≤ 2 of 5 valid reports
  - median wall time > 20 min
- **In between:** one logged prompt revision (new hash) and a single re-run on the same 5 scenarios. If the result is still in between, propose hosted.

A hosted pilot needs explicit user approval, a $5 hard cap in the provider console, and httpx only.

## M3 stage B: smoke run and the thinking-mode decision (recorded 2026-10-23, before the 7 pilot runs)
**Smoke run.** `sc-2c422896a9` is not in the pilot set and is not scored. Settings: `qwen3:4b` (ID `359d7dd4bcda`), Ollama 0.40.8, `--think off`, frozen prompt `0f97fb44…`.
- **Format works.** There were no `bad_response` errors, all 3 model tool calls parsed and were valid (`get_window`, `search_logs`, `submit_report`), and the report validated on the first try. No client fix was needed.
- **Thinking off was honoured:** 0 thinking characters on every turn.
- **Time per turn:** 38.1 s, 35.7 s and 102.7 s. Prompt tokens were 1,651, 2,289 and 4,914; completion tokens 522, 834 and 1,876. The run took 176.6 s in total.
- **Shallow investigation.** The model reported after only 2 tool calls, so pilot runs with more turns will take longer. At about 40–100 s per turn, 15 or more turns would approach the 20-minute cap.
- **Memory:** swap grew from 1,098 MB to 3,039 MB during the run (+1.94 GB, just under the 2 GB abort threshold), and the kernel pressure level went from 1 to 2 (warn). Free disk fell from 26.5 to 24.7 GB as swap grew.

**Thinking-mode decision: off (`--think off`) for all 7 pilot runs.** It will not change after the runs start. Reasons:
1. With thinking off, turns already take 36–103 s and the memory guard nearly fired. Thinking would add generated tokens to every turn, and so time, with no memory headroom left.
2. The pilot tests whether the model can drive the tools at all. Thinking is a separate variable that the 5-scenario rule cannot separate from tool use.

**Limitation.** Thinking is the model's default (`ollama show`: thinking default true), and it was not measured in a smoke run. The pilot therefore measures `qwen3:4b` without thinking, not the model at its default. A thinking-on comparison is left for later, if the memory budget allows.

## M3 stage B: first pilot attempt, aborted by the swap guard (2026-10-23)
**Status: aborted after 3 of 7 runs. This attempt is on record and is never merged with a later attempt. The decision rule is NOT applied to partial data.**

**Files.** All under `eval/pilot/generator-v5/ollama-qwen3-4b/`, committed unchanged. sha256 prefixes:
- `run_log.jsonl` (`ee5007b3…`)
- `traces/01-sc-06b280fbed.jsonl` (`8dfc0b22…`)
- `traces/02-sc-1499febf6f.jsonl` (`3df180e0…`)
- `traces/03-sc-203fe8a4ca.jsonl` (`231b2722…`)

There is **no `summary.json` or `summary.md`**: `HarnessAbort` propagates before the summary is written. The only abort marker in the files is the run log's `"event": "abort"` line, and the trace files don't mark themselves as part of an aborted attempt.

**Conditions** (as reported by the user, plus the run log):
- VS Code closed; the batch was run from Terminal under `caffeinate -i`.
- The Ollama server was run by the user; its log is not available.
- Settings: `qwen3:4b` `359d7dd4bcda`, Ollama 0.40.8, `--think off`, `num_ctx` 8192, temperature 0, seed 0, frozen prompt `0f97fb44…` (confirmed in each trace).
- Swap at start: the user read 515 MB before the batch. The run log's `batch_start` reading is 0.0 MB, so the guard's baseline was 0.0 MB.

**Swap, memory pressure and free disk around each run** (from the run log):

| Point | Swap used (MB) | Pressure level | Free disk (GB) |
|---|---|---|---|
| batch start | 0.0 | 1 | 45.88 |
| run 1 end | 466.6 | 1 | 44.82 |
| run 2 end | 1,057.7 | 2 | 43.75 |
| run 3 end | 4,231.2 | 2 | 38.56 |
| abort check, before run 4 | 4,223.2 | 2 | 38.56 |

- **User readings:** about 2,351 MB during run 3, from the progress line. After stopping Ollama, `vm.swapusage` showed 959.5 MB used out of 2,048 MB, which suggests the server's memory was a major contributor to the swap growth.
- **Guard message:** `swap grew by more than 2.0 GB`, raised before run 4 (`sc-2d438d4575`). Growth from the batch baseline was 4.2 GB.

**The three completed runs:**

| Run | Scenario | Stop | Wall time | Turns | Valid calls | Median turn latency | Tokens (prompt / completion) |
|---|---|---|---|---|---|---|---|
| 1 | sc-06b280fbed | sufficient_evidence | 207.4 s | 3 | 3/3 | 50.6 s | 9,965 / 4,126 |
| 2 | sc-1499febf6f | sufficient_evidence | 332.4 s | 5 | 5/5 | 68.5 s | 20,037 / 5,474 |
| 3 | sc-203fe8a4ca | sufficient_evidence | 755.9 s | 8 | 6/7 | 96.1 s | 40,279 / 8,536 |

**Reading these:**
- **Run 3's 756 s probably includes swap slowdown.** Swap grew about 3.2 GB during that run. It must not be read as model slowness. Turn latency also grows with prompt length, so the two effects aren't separated.
- **Likely context overflow in run 3.** Up to turn 5, Ollama's reported prompt tokens track an estimate from the trace, at about 3.6 characters per token. From turn 6 the full conversation is about 8,300–8,900 tokens, over `num_ctx` 8192, and the reported counts drop (7,046 → 4,098 at turn 6, then 8,095 and 6,834). That pattern fits Ollama truncating the conversation, so run 3's turns 6–8 likely saw only part of it.
  - **Not confirmed:** the server log isn't available, and Ollama's count could also exclude cached tokens.
  - This is a property of the pre-registered `num_ctx`, not of the model.

## M3 stage B: attempt 2 configuration (recorded 2026-10-23, BEFORE attempt 2)
User decision: option A + C, plus two additions and five conditions. Code is in commit `3c28b0b`. The prompt sha256 stays `0f97fb44c2549794f7ba1be577d8d01392422e30b8752f4fd2ba640a88c2d2ea` (unchanged, pinned by `test_prompt_is_frozen`).

**Unchanged from the pre-registration, and the same as attempt 1:**
- model and settings: `qwen3:4b` `359d7dd4bcda`, Ollama 0.40.8, `--think off`, `num_ctx` 8192, temperature 0, seed 0
- the 7 scenarios and their order
- all loop bounds
- the decision rule
- the guard: abort before a run if free disk is below 10 GB, if swap has grown more than 2.0 GB since batch start, or if the kernel pressure level is critical

**Changes, applied to all 7 runs:**
1. **Unload after every run (A).** At the end of each run, after its `run_end` line, the model is unloaded with `keep_alive: 0`, and an `unload` line with the post-unload stats is written to the run log.
   - The next run's guard check happens at its start and reads the post-unload stats.
   - The guard's threshold and measurement are unchanged: growth since batch start.
   - **A single run that grows swap by more than 2 GB on its own can still trip the guard** at the next check.
   - The model reloads on each run's first turn. Ollama's `load_duration` is recorded per turn as `load_s` (shown as `load_s` per run in the summary), so load time can be told apart from model time. Wall time still includes it.
2. **Clean restart of the Mac (C)** before the batch, with only Terminal open. Streamlit is stopped, the laptop is on power, and the batch runs under `caffeinate -i`.
3. **New output directory.** `eval/pilot/generator-v5/ollama-qwen3-4b-attempt2/`, selected with `--attempt 2`. The pilot refuses to start in a directory that already holds traces or a run log, so attempt 1 can't be overwritten.
4. **Context-overflow indicator.** Each run's summary row gets `prompt_drops`, `max_prompt_tokens` and `likely_context_overflow`: the reported prompt shrinking while the conversation grows, or reaching 98% of `num_ctx`. It is a heuristic, because a backend that excludes cached tokens from its count could also shrink it.
5. **Summary written even on abort.** If attempt 2 aborts, the summary is still written and marked `aborted`.

**Conditions:**
- **No third attempt.** If attempt 2 aborts, the recorded outcome is: **"local pilot cannot complete on this 8 GB machine under the pre-registered bounds"**. The decision rule is then applied as written to the data that exists, and an incomplete batch counts as the **"propose hosted"** branch (`complete: false` forces `propose_hosted`). There is no retry.
- **Server log.** The user runs `ollama serve` with its log redirected to a file outside the repo. After the batch, only the lines relevant to truncation or context are extracted into the attempt directory, with a count. The full log is not committed.
- **Comparison with attempt 1.** Runs 1–3 of attempt 2 will be compared with runs 1–3 of attempt 1, as description only: whether the answers and stop reasons match. Attempt 1's run 3 probably overflowed the context. The attempts are never merged.

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
- The ambiguous decoy can land on the root service itself. In v5 dev it does in 5 of 10 ambiguous scenarios, and 8 of 10 decoys are deployments rather than config changes (v3: 4 of 10 and 9 of 10). A benign deploy just before a memory leak is realistic but genuinely hard, and with 10 ambiguous dev scenarios these placements may dominate the tier's results.
- A config decoy keeps its original service when no affected service can take its key, so not every config decoy is on an affected service. This is tested for deployment decoys only.
- Metrics are smooth and propagation is a fixed halve-per-hop rule; real incidents are messier.
- `internal_error` in `ToolSet.call` is a catch-all that could hide tool bugs, and no test exercises it.
- The viewer adds about 360 MB of dependencies to the shared `.venv`. The import-ban test keeps them out of the core package, but core tests now run in an environment that has pandas installed, so an accidental pandas dependency in a test could go unnoticed.
- The simulator, the baseline and the prompts are all written by the same author, so co-adaptation is a real risk. The M2b results suggest it already happened: the keyword list matches the dev templates closely enough to score 32/32 on four faults.
- Evidence validity under the M2b definitions counts the alert as relevant (citing only the alert scores 100%). Fixed by the headline definition; the old columns remain for comparison only.
- Headline evidence validity is a membership check: a top-1 citation counts if it is a fault log or the trigger change. It doesn't check that the record supports the claimed fault or that it discriminates the fault from the overlap fault, and it is pooled with no interval.
- The missing-evidence naming score only checks that the gapped service is named. It doesn't check whether the report says *what* is missing (logs vs metrics). The baseline can only detect log gaps.
- Baseline v1 and the `latest_change` floor still derive the window start from a metric point (kept unchanged on purpose). New investigators should use `get_window`.
- The v4 overlap mechanisms were designed knowing the baseline's signals ("connection", "timeout"). They are realistic side effects, but the choice of *which* side effects to add was informed by what would confuse this baseline.
- The harness does not catch investigator exceptions; a crash stops the run. That is fine for deterministic baselines, but LLM investigators in M3/M4 need an `error` stop reason instead.
- **Stream independence is tested on 10 cases per mechanism and profile, not proven.**
  - The unconditional alert draw is a defensive fix that no tested case exercises: reverting it still passes, because overlap never changed which services breach in 195 cases searched.
  - A mutation that routes overlap and injection lines back to the base stream fails 8 of 13 tests.
- **The solvability test is lenient:** some evidence path survives, not a discriminating one (see README limitations).
- **Twin runs double LLM cost for roughly a third of scenarios** (12/40 dev).
- **The Ollama request and response shape is written from the documented API and tested only against `httpx.MockTransport`.** The stage B smoke run is the first real check. A mismatch will show up as `bad_response` errors.
- **Thinking mode is unverified.** The Ollama page lists `qwen3:4b` with a `thinking` tag but doesn't say how to configure it. The client sends `think` only when `--think on|off` is given, and records `thinking_chars` per turn.
- **Untrusted text in the M3 page.** Tool names chosen by the model appear in a selectbox label. Everything else model- or log-written is in dataframes or code blocks.
- **`apply_rule` takes the median wall time over core runs that have one.** A run with no stop event (an aborted batch) has none, so it is excluded from the median, though it still counts against valid reports.

## Open questions
- ~~**Benchmark difficulty.**~~ Decided and done: generator v4 (see "Harder benchmark" above). Original question: should the tiers be strengthened before the first `--final` run? The freeze rule allows regenerating held-out until then. Options:
  - remove distinctive templates entirely in the ambiguous tier, rather than thinning them to 40%
  - add confounders that share keywords across faults
  - gap the root's logs *and* metrics in the missing-evidence tier

  Any change bumps the generator and needs a refreeze note.
- ~~**Scenario window.**~~ Done: the `get_window` tool. Baseline v1 still infers the window from a metric point, unchanged by decision.
- ~~**Evidence validity.**~~ Done: the headline is "strict excluding the alert"; the M2b definitions are kept and labelled.
- ~~**Missing-evidence scoring.**~~ Done: "missing evidence named" on the missing-evidence tier.
- ~~**Injection metric.**~~ Done in v5: paired injection twins.
- ~~**Ambiguous tier vs `rule_based`.**~~ Decided: no further difficulty revision (user decision, 2026-10-22). The v5 ablation shows why it doesn't bite: overlap changes none of `rule_based`'s answers.

## Next action
**M3 stage B** (approved 2026-10-23): install Ollama, pull `qwen3:4b`, smoke run, then the 7 pilot runs. Earlier note, kept for history:

**M3 planning: approved, not started.** The plan (LLM adapter interface, local Ollama/Qwen pilot on 5 dev scenarios plus twins, optional hosted model with cost estimates) is in the 2026-10-22 conversation. Before any code, settle the open choices:
- installing Ollama
- the model size, given 8 GB RAM and about 9 GB free disk
- whether to use a hosted model, plus its dependency and spending cap

Then pre-register the pilot questions here.
