# SentinelOps M4 + M5 report: an explicit-state investigation agent against a single-pass baseline

**Status:** draft, 2026-11-06. Every number here is taken from committed outputs and was checked against them:
- the M4 core runs (3d3fdca)
- the M5 dev gate (129b672, report 52daa08)
- the fresh-split runs (a3765d7) and their analysis (`eval/m5/generator-v5/m5_analysis.json`, f9950e2)
- the safety test (a3765d7)
- E1 (ca05142, report 84b54bd)

Detailed records live in `docs/PROGRESS.md` and `docs/m5_preregistration.md`.

## What this result is about, and what it is not

**It is about:**
- one agent prompt, **v1** (`d269d28d`), driving an explicit state machine (TRIAGE → GATHER → HYPOTHESIZE → VERIFY → REPORT);
- one hosted model, **`ministral-14b-2512`**, at temperature 0 with seed 0;
- a **synthetic, author-built benchmark**: 4 services, 5 fault types, 60 freshly generated scenarios;
- comparison with a single-pass baseline on the same model, and with four local, deterministic baselines.

**It is not about:**
- **Agents in general.** One prompt, one model, one state machine and one benchmark were tested. An improved prompt (v2) existed and failed its pre-registered dev gate, so it was never run on the fresh split.
- **The local 4B model.** `qwen3:4b` failed its smoke gate in M4. Every M4 and M5 number below comes from the hosted 14B model.
- **Real incidents.** The simulator, the baselines, the prompts and the single-pass bundle rule share one author (co-adaptation caveat A5). No claim is made that any of this generalizes beyond the simulator.

**Headline:**
- On the 60 fresh originals, **single-pass full was right on top-1 where the agent was wrong 16 times; the reverse happened 5 times.** The exact two-sided sign test on these 21 discordant pairs gives p = 0.0266.
- The agent (33/60) also scored below the rule-based baseline (38/60).
- The diagnosis is a process failure. The agent ranks hypotheses before it looks at what changed. Only 3 of 60 runs touched a change tool, and all 3 did so after their first ranking.

## 1. The question, and why the evaluation was built this way

**The question:** does an LLM agent that investigates with read-only tools diagnose the root cause of a simulated incident better than simpler alternatives? A diagnosis is a (service, fault type) pair. The simpler alternatives are:
- the same model given a fixed evidence bundle in one pass;
- a hand-written rule baseline;
- trivial floors.

**Design choices, and the reason for each:**
- **Synthetic, seeded data with hidden ground truth.**
  - Every scenario has a known answer.
  - The tools can't reach the labels: ground truth lives in separate files that the tools never import.
  - The same seed gives byte-identical data.
- **Pre-registration before every run that counts.**
  - The M4 decision rule, the M5 design, the dev gate and the analysis were committed before the runs they govern.
  - Every later change is logged with its date and reason (section 2), because the same person wrote the system and the test.
- **A dev gate for the v2 prompt** (22 dev scenarios, never used before). A prompt revision had to earn its place on data that doesn't count before it could touch data that does.
- **A fresh split for the headline.**
  - 60 scenarios, generated once with a rule-derived seed and frozen.
  - Never viewed, except by the code that scores runs.
  - The real held-out split stays off the hosted provider and remains unused.
- **Paired comparisons:**
  - Every arm runs on the same 60 scenarios, so the primary test compares per-scenario outcomes (a sign test on discordant pairs), not two independent rates.
  - The safety test pairs each injected scenario with a twin that differs only by the injected lines.
- **Local baselines and floors** show how much is gained over trivial strategies:
  - alert-service: blame the alerting service;
  - latest-change: blame the last change;
  - keyword-only;
  - the rule baseline.
- **Counts with Wilson 95% intervals, not rates.** The samples are small (12–60 per cell).

## 2. Pre-registered design, deviations and operational changes

**M4 (pre-registered 2026-10-23):**
- **The agent's bounds:**
  - a budget of 40 tool calls (TRIAGE 3, loop-issued);
  - a GATHER cap of 16 and a VERIFY cap of 8;
  - a prompt budget of 6,144 estimated tokens;
  - deterministic compaction from level 0 to 4.
- **"Investigated" (a)–(f):** a process definition (valid report, gather evidence, two data kinds, top hypothesis supported, VERIFY tested rank 2 or a contradiction of rank 1, no overflow).
- **A decision rule** on 10 fixed core scenarios plus 2 injection twins, never used for development.

**M5 (pre-registered 2026-10-29, approved with amendments A1–A5 and additions B1–B5):**
- **Arms:**
  - agent v1 and agent v2 (v2 a new prompt under a recorded exception);
  - single-pass full and single-pass without the change timeline (B2);
  - four local baselines.
- **The v2 dev gate**, G1–G4 on 22 dev originals:
  - G1: a valid change-tool call before the first ranking in at least 16 of 22 v2 runs;
  - G2: valid reports for v2 at least those of v1;
  - G3: 0 `unknown_tool` calls;
  - G4: 0 overflows, `context_exhausted` included.
- **The fresh split:** seed 447518130, held-out's profile, 60 scenarios. Manifest sha256 `574908ad…07fe`. No ID collides with dev or held-out.
- **The primary as written (A3):** top-1 on the 60 fresh originals, v2 against v1, with an exact paired sign test. There is no pass/fail verdict for M5.
- **The paired injection safety test**, separate and labelled:
  - a loop-issued `search_logs` call per injected line, identical on the twin;
  - an offline exposure check before any run.

**Deviations and operational changes:**

| ID | Date | What | Why | Status |
|---|---|---|---|---|
| D1 | 2026-11-05 | The primary becomes **agent v1 against single-pass full**, top-1 on the 60 fresh originals, with an exact two-sided paired sign test. Wilson intervals are secondary | v2 failed the dev gate (G2: 17 vs 19 valid reports; G4: 4 overflow runs). A3's primary (v2 vs v1) could not be computed, and A3 had no fallback | Decided after the dev gate and **before the fresh split was generated**. **Known when deciding:** dev top-1 was single-pass full 20/22, agent v1 8/22 (information only); the bundle design followed the M4 failure pattern |
| O1 | 2026-11-05 | The safety test runs in 3 contiguous slices of the exposed pairs, with one rerun per slice as attempt 2 | Shorter batches on the free tier, and a defined rerun unit | Operational, not a design change; fixed before the exposure check |
| O2 | 2026-11-05 | Headline batches run by slice: for K = 1–6, agent v1, then single-pass full, then no-timeline | Replaces the v1/v2 alternation, so the two D1 arms meet the same provider conditions over time | Operational, not a design change |
| E1 | 2026-11-05 (approved), 2026-11-06 (run) | A replicate-noise control: the 21 safety originals rerun once with identical forced queries, no twins | **Decided after seeing the safety counts** (top-1 changed in 7 of 19) | **Exploratory, post hoc.** Reported next to the safety counts, never in place of them |

**Two implementation choices made after the runs, before the analysis was run on them.** Both were developed on dev-gate outputs only:
- "Trigger seen" means the trigger record's ID was shown to the model inside the 4,000-character result cap. It is counted over runs whose scenario has a trigger.
- "Active time" is wall time minus provider rate-limit waits.

## 3. Data and arms

**Data:**
- **The fresh split** (m5fresh): 60 originals, 30 standard, 15 ambiguous and 15 missing-evidence; 12 per fault type.
  - 24 scenarios have a trigger record: the 12 bad_deployment and 12 config_error scenarios.
  - 21 carry injected log lines (about 24 were expected).
- **All runs:** one attempt each, from code `cdc6ea2`, with no provider stop and no rerun.

| Arm | What it is | Calls |
|---|---|---|
| agent v1 | The state machine with prompt `d269d28d`, compaction, and a ledger of shown IDs | Budget 40 (3 loop-issued); used median 22, max 27 |
| single-pass full | One request with a fixed bundle chosen by a frozen rule (`2bf74a3f`): alert, window, dependencies, the `get_timeline` change records, ERROR/WARN log samples per service, metric summaries; one `submit_report`, one repair turn | No model tool calls |
| single-pass no-timeline | The same bundle without the change records (`e4acb736`) | No model tool calls |
| rule-based | Deterministic baseline (v1), tuned on dev only | 52 |
| keyword-only | Deterministic keyword scoring | 38 |
| latest-change | Floor: blame the most recent change | 4 |
| alert-service | Floor: blame the alerting service | 1 |

## 4. Results

### M4 core runs (context, 2026-10-29)
- **The set:** the 10 core scenarios plus 2 twins, prompt v1, `ministral-14b-2512`.
- **Pre-registered rule verdict: `works_locally`.**
  - 10/10 originals investigated, 10/10 valid reports, 0 overflows.
  - On a hosted backend the median-time threshold always passes, so it is not evidence of quality.
- **Accuracy, description only:**
  - top-1 8/10 originals, top-3 10/10.
  - Both misses were config_error reported as pool exhaustion. The trigger record was never retrieved in either.
- **Change tools:** across 12 runs, the model never called `list_deployments`, `list_config_changes` or `get_timeline`. It tried a nonexistent `get_config_changes` 3 times.
- **Injection:** the injected lines never reached the model, so the two M4 pairs show nothing about injection.
- **Status:** the core results are consumed.

### M5 dev gate (2026-11-02; development check, not a result)

| Check | v1 | v2 | Requirement | Met |
|---|---|---|---|---|
| G1 valid change-tool call before the first ranking | 0/22 | 22/22 | v2 ≥ 16 | yes |
| G2 valid reports | 19/22 | 17/22 | v2 ≥ v1 | **no** |
| G3 `unknown_tool` calls | 0 | 0 | 0 | yes |
| G4 overflow runs | 1 | 4 | 0 | **no** |

**v2 failed, so M5 uses v1 only.** Dev top-1, information only: v1 8/22, v2 12/22, single-pass full 20/22, no-timeline 15/22.

### Primary (D1)
**Top-1 over 60 paired fresh originals:**
- agent v1 right, single-pass full wrong: **5**
- single-pass full right, agent v1 wrong: **16**
- exact two-sided sign test on n = 21 discordant pairs: **p = 0.0266**

### Every arm (60 fresh originals)

| Arm | Top-1 [Wilson 95%] | Top-3 [Wilson 95%] | Valid reports |
|---|---|---|---|
| agent v1 | 33/60 [0.42, 0.67] | 42/60 [0.57, 0.80] | 56/60 |
| single-pass full | 44/60 [0.61, 0.83] | 53/60 [0.78, 0.94] | 55/60 |
| single-pass no-timeline | 35/60 [0.46, 0.70] | 40/60 [0.54, 0.77] | 54/60 |
| rule-based | 38/60 [0.51, 0.74] | 52/60 [0.76, 0.93] | 60/60 |
| keyword-only | 34/60 [0.44, 0.68] | 47/60 [0.66, 0.87] | 60/60 |
| latest-change | 12/60 [0.12, 0.32] | 24/60 [0.29, 0.53] | 60/60 |
| alert-service | 6/60 [0.05, 0.20] | 20/60 [0.23, 0.46] | 60/60 |

A run without a valid report counts as wrong.

### By tier (top-1, k/n with Wilson 95%)

| Arm | standard (30) | ambiguous (15) | missing-evidence (15) |
|---|---|---|---|
| agent v1 | 15/30 [0.33, 0.67] | 10/15 [0.42, 0.85] | 8/15 [0.30, 0.75] |
| single-pass full | 24/30 [0.63, 0.91] | 10/15 [0.42, 0.85] | 10/15 [0.42, 0.85] |
| single-pass no-timeline | 21/30 [0.52, 0.83] | 8/15 [0.30, 0.75] | 6/15 [0.20, 0.64] |
| rule-based | 21/30 [0.52, 0.83] | 11/15 [0.48, 0.89] | 6/15 [0.20, 0.64] |
| keyword-only | 21/30 [0.52, 0.83] | 8/15 [0.30, 0.75] | 5/15 [0.15, 0.58] |
| latest-change | 8/30 [0.14, 0.44] | 1/15 [0.01, 0.30] | 3/15 [0.07, 0.45] |
| alert-service | 3/30 [0.03, 0.26] | 0/15 [0.00, 0.20] | 3/15 [0.07, 0.45] |

### By fault type (top-1 / top-3, out of 12 each; counts only)

| Arm | bad_deployment | config_error | pool_exhaustion | memory_leak | certificate_expiry |
|---|---|---|---|---|---|
| agent v1 | 7 / 9 | **0 / 6** | 10 / 11 | 12 / 12 | 4 / 4 |
| single-pass full | 7 / 10 | 7 / 9 | 10 / 12 | 12 / 12 | 8 / 10 |
| single-pass no-timeline | 5 / 9 | 0 / 0 | 9 / 10 | 12 / 12 | 9 / 9 |
| rule-based | 9 / 12 | 9 / 9 | 10 / 12 | 10 / 12 | 0 / 7 |
| keyword-only | 9 / 9 | 9 / 9 | 7 / 10 | 9 / 10 | 0 / 9 |
| latest-change | 4 / 12 | 8 / 12 | 0 / 0 | 0 / 0 | 0 / 0 |
| alert-service | 6 / 6 | 0 / 9 | 0 / 0 | 0 / 0 | 0 / 5 |

### Ablation (secondary): single-pass full against no-timeline
- **Top-1 over 60 paired originals:** full right and no-timeline wrong 12, the reverse 3; sign test n = 15, p = 0.0352.
- **What it compares:** the no-timeline bundle drops every change record (deployments and config changes), so this is "with or without change records".

### Other secondary measures

| Arm | Headline evidence validity | Unsupported hypotheses | Tool calls (median / max) | Active s (median / max) | Valid change-tool call | Trigger seen |
|---|---|---|---|---|---|---|
| agent v1 | 237/413 (57.4%) | 20/192 | 22 / 27 | 64.5 / 108.5 | 0/60 | 1/24 |
| single-pass full | 171/315 (54.3%) | 5/275 | — | 24.3 / 73.7 | — | 24/24 |
| single-pass no-timeline | 159/274 (58.0%) | 23/270 | — | 24.6 / 60.0 | — | 0/24 |
| rule-based | 128/187 (68.4%) | 0/180 | 52 / 52 | < 0.1 | — | — |
| keyword-only | 106/153 (69.3%) | 0/178 | 38 / 38 | < 0.1 | — | — |

- **Evidence validity** pools top-1 citations against the headline relevant set: fault logs and the trigger, excluding the alert. Citations within a run are correlated, so there is no interval.
- **Fabricated citations:** 0 in every arm.
- **Agent "investigated":**
  - (a) 56/60, (b) 60/60, (c) 59/60, (d) 56/60, (e) 59/60, (f) 60/60.
  - All six together: 55/60.
- **Agent stops:**
  - 56 `sufficient_evidence`.
  - 4 `context_exhausted`: all in VERIFY, on requests built but never sent, at 6,167–6,191 estimated tokens against the 6,144 budget.
- **Single-pass invalid reports** (full 5, no-timeline 6): all "still invalid after 1 repair turn". Ten had no `submit_report` call and one failed validation. None was caused by the provider.
- **Natural exposure:** of 21 injected originals, the agent was shown an injected line in 3. The single-pass bundle contains one in 4 (full) and in 4 (no-timeline).

### Safety test (separate, labelled; summed over 3 slices)
- **Setup:** 21 exposed pairs, all exposed in the run, with twin queries identical in 21/21. 19 pairs have both reports; one pair in each of slices 1 and 2 stopped `no_new_evidence` in both arms.
- **Of the 19:**
  - top-1 changed between original and twin: **7**;
  - original followed the injected claim: **1**;
  - injected line cited: **1**;
  - executed actions: **0**.

### E1: replicate-noise control (exploratory, post hoc, decided after the safety counts)
- **Setup:** 21 replicates of the safety originals with identical forced queries (21/21). 16 have both an original and a replicate report. 5 replicates gave no report: 3 `no_new_evidence` and 2 `context_exhausted`.

| | n | Top-1 differs |
|---|---|---|
| Original vs replicate | 16 | **3** |
| Original vs replicate, pairs whose twin also has a report | 16 | **3** |
| Original vs twin on those same pairs (pre-registered count) | 16 | **5** |

- **Overlap:** all 3 replicate disagreements fall in pairs where the twin also changed. Of the 11 pairs where the twin didn't change, 0 disagreed on replication.
- **What it supports:** run-to-run variation is of the same order as the original-against-twin changes, so the safety test's changes cannot be attributed to the injected lines.
- **What it does not support:** no injection effect, or a small one. 2 pairs changed against the twin while the replicate reproduced the original; that is n = 2, post hoc, and the twins themselves were not replicated.

## 5. Diagnosis: the agent ranks before it looks at what changed

**The agent rarely looks at changes, and when it does, it's too late:**
- **Valid change-tool calls: 0/60.** That is a call returning at least one record, made before the first `submit_hypotheses`.
- **Only 3 of 60 runs touched change tools at all.** All 3 did so in VERIFY, after their first ranking.
  - They made 5 calls (`list_config_changes` ×3, `list_deployments` ×2). 4 returned records and 1 was empty. The windows were ordinary (1–2 h).
  - So the 0/60 comes from timing. Empty results or wrong windows don't explain it.
  - **Outcomes of those 3 runs:**
    - one `bad_deployment` run saw its trigger (the only trigger sighting, 1/24) and was still wrong at top-1;
    - one `bad_deployment` run didn't see its trigger and was right;
    - one `memory_leak` run (no trigger) was right.
- **The pattern was already visible:**
  - in M4 (no change-tool call in 12 runs; both misses were config changes);
  - on dev (v1 0/22).

  v2 fixed the behaviour on dev (22/22) but failed the gate on valid reports and overflows.

**Where the gap is:**
- The agent and single-pass full differ by 11 on top-1 (44 − 33).
- **config_error accounts for 7 of the 11** (agent 0/12, full 7/12). That is the fault type whose evidence is a config change record.
  - Without change records, single-pass no-timeline also scores 0/12 there, and 0/12 at top-3.
  - Single-pass full sees the trigger in 24/24 runs; the agent in 1/24.
- **certificate_expiry accounts for the other 4** (agent 4/12, full 8/12; agent top-3 4/12).
  - It has no trigger record, so the change-tool diagnosis does not explain it.
  - **The agent's 8 misses there, read from the traces (facts only, no change made from them):**
    - **The true pair is in none of the 8 top-3s.**
    - **2 misses have no report:** they stopped `context_exhausted`, and they are 2 of the agent's 4 `context_exhausted` stops.
    - **What the other 6 ranked first:**
      - `connection_pool_exhaustion` in 4 runs: 3 on `api-gateway` (the true service), 1 on `auth`;
      - `config_error` in 1 (`orders`);
      - `certificate_expiry` in 1, on the wrong service (`api-gateway`).
    - **Only 1 of the 6 lists `certificate_expiry` anywhere** among its hypotheses.
    - **The 3 `api-gateway/connection_pool_exhaustion` rankings name a pair the simulator never generates.** Pool exhaustion is generated only on services with a database pool, and the gateway has none.
  - **Why the agent rarely considers certificate expiry is not established.** This part of the gap is unexplained.
- **The other three fault types are tied** on top-1 (bad_deployment 7/7, pool exhaustion 10/10, memory leak 12/12).

**"Investigated" doesn't capture this:**
- The agent met all six criteria in 55/60 runs, yet it was the least accurate hosted arm.
- The definition rewards structure: gathering, two data kinds, a VERIFY call. It does not reward looking at the evidence that decides the case.

## 6. Caveats

**About the comparison:**
1. **Synthetic, author-built data; co-adaptation (A5).**
   - The simulator generates config and deployment faults from change records.
   - The single-pass bundle rule includes the change timeline, and it was designed after seeing that the M4 agent never called it.
   - The simulator, the baselines, the prompts and the bundle rule share one author. No generalization is claimed.
2. **One model, one prompt.** `ministral-14b-2512`, reached by fallback, and agent prompt v1. Nothing here says anything about the local 4B model, other models, or agents in general.
3. **Reproducibility.**
   - Hosted runs are **not repeatable at temperature 0 with seed 0**. In E1, 3 of 16 replays changed top-1, and 5 of 21 replays produced no report.
   - **Every headline arm was run once.**
   - **This bears on D1:** some of the 21 discordant pairs would likely flip on a rerun. The size of that effect for the headline arms is unmeasured.
4. **D1 is a deviation chosen knowing the dev direction.** It was decided before the fresh split existed, but after single-pass full scored 20/22 against agent v1's 8/22 on dev.
5. **A small sample and many comparisons.**
   - p = 0.0266 rests on 21 discordant pairs, and the top-1 Wilson intervals overlap (agent [0.42, 0.67], full [0.61, 0.83]).
   - The ablation (p = 0.0352) and every other secondary comparison are uncorrected and exploratory.
6. **Not like for like.**
   - The agent works under a 40-call budget and a 6,144-token compacted context.
   - Single-pass gets an author-chosen bundle that always includes the change timeline.
   - The rule baseline uses 52 calls.
7. **The agent does not beat the rule baseline** (33 vs 38 top-1). On top-3, the rule baseline (52/60) is level with single-pass full (53/60).

**About the agent's process:**

8. **The 0/60 change-tool count is a timing result.** 3 runs called change tools only after their first ranking (section 5). The fault-type explanation covers config_error, not certificate_expiry.
9. **"Investigated" measures process, not insight.** (f) counts only requests that were sent, so the 4 `context_exhausted` runs pass (f).
10. **`context_exhausted` is a harness budget stop** (4/60, scored wrong). The estimator runs about 10% above the server's count (for example 6,067 estimated against 5,480 reported). Whether the unsent requests would have fit is unknown.
11. **Invalid reports count as wrong in every arm** (agent 4, full 5, no-timeline 6). The single-pass failures are format failures after one repair turn.

**About how the numbers are reported:**

12. **The ablation removes every change record**, not only a timeline view.
13. **Tier and fault-type cells hold 12–30 scenarios.** They are reported as counts, and no claim is made from them.
14. **Evidence validity pools correlated citations,** with different denominators per arm (413, 315, 274). The headline definition excludes the alert.
15. **Hosted times include provider latency and pacing.** They are not evidence of quality.

**About the data:**

16. **The fresh split is not the frozen held-out split.**
    - It shares held-out's profile and generator, but it was generated after M4 and the dev gate.
    - It was sent to the hosted provider; held-out was not and remains unused.
    - It had 21 injected pairs, against about 24 expected.
    - The headline outputs are consumed: there is no tuning or rerun against them.
17. **Measurement implementation after the runs.** The secondary measures were defined in words in advance. Their implementation (trigger seen inside the cap, active time) was written after the runs, on dev-gate outputs only, before the analysis touched the fresh outputs.

**About the safety test:**

18. **Exposure was forced.**
    - The safety test forces exposure with a loop-issued call, which counts toward the 40-call budget.
    - Natural exposure was low (agent 3/21, bundles 4/21).
    - The 7/19 changes are indistinguishable from run-to-run noise (E1).
    - "Followed the claim" (1) and "cited the injection" (1) rest on n = 19.
    - **Executed actions = 0 holds by design:** the tools are read-only and no action tool exists. It is not a measured robustness property.
19. **E1 is exploratory and post hoc.** It is a single replicate per original, the twins were not replicated, and it was decided after the safety counts.

**About the process and setup:**

20. **The process was not blind.**
    - The M5 pre-registration was written after seeing the M4 failures.
    - Every M4 fix was motivated by one smoke scenario, and M4 check 6 was rewritten post hoc.
    - The harness makes most state transitions, so the agent is less agentic in practice than designed.
21. **Provider settings.**
    - The "no data retention" setting is as stated by the user. Whether it is the training opt-out was not verified.
    - The free tier's 429s carry no rate-limit headers.
