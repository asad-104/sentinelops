# M5 headline analysis (fresh split)

Manifest `574908adb8ec…`, model `ministral-14b-2512`, agent prompt `d269d28d9581…`, run commits cdc6ea2. Synthetic, author-built data; the simulator, the baselines and the prompts share an author (A5). Counts with intervals, not rates. No pass/fail verdict.

## Primary (D1)

Top-1, agent v1 against single-pass full, over 60 paired originals: agent right and single-pass wrong **5**, the reverse **16**; exact two-sided sign test on n = 21 discordant pairs, p = 0.0266.

## Every arm (secondary)

| Arm | Top-1 [Wilson 95%] | Top-3 [Wilson 95%] | Valid reports |
|---|---|---|---|
| agent_v1 | 33/60 [0.42, 0.67] | 42/60 [0.57, 0.80] | 56/60 |
| single_pass_full | 44/60 [0.61, 0.83] | 53/60 [0.78, 0.94] | 55/60 |
| single_pass_no_timeline | 35/60 [0.46, 0.70] | 40/60 [0.54, 0.77] | 54/60 |
| rule_based | 38/60 [0.51, 0.74] | 52/60 [0.76, 0.93] | 60/60 |
| alert_service | 6/60 [0.05, 0.20] | 20/60 [0.23, 0.46] | 60/60 |
| latest_change | 12/60 [0.12, 0.32] | 24/60 [0.29, 0.53] | 60/60 |
| keyword_only | 34/60 [0.44, 0.68] | 47/60 [0.66, 0.87] | 60/60 |

## By tier (top-1, k/n with Wilson 95%)

| Arm | ambiguous | missing_evidence | standard |
|---|---|---|---|
| agent_v1 | 10/15 [0.42, 0.85] | 8/15 [0.30, 0.75] | 15/30 [0.33, 0.67] |
| single_pass_full | 10/15 [0.42, 0.85] | 10/15 [0.42, 0.85] | 24/30 [0.63, 0.91] |
| single_pass_no_timeline | 8/15 [0.30, 0.75] | 6/15 [0.20, 0.64] | 21/30 [0.52, 0.83] |
| rule_based | 11/15 [0.48, 0.89] | 6/15 [0.20, 0.64] | 21/30 [0.52, 0.83] |
| alert_service | 0/15 [0.00, 0.20] | 3/15 [0.07, 0.45] | 3/30 [0.03, 0.26] |
| latest_change | 1/15 [0.01, 0.30] | 3/15 [0.07, 0.45] | 8/30 [0.14, 0.44] |
| keyword_only | 8/15 [0.30, 0.75] | 5/15 [0.15, 0.58] | 21/30 [0.52, 0.83] |

## By fault type (top-1 / top-3 / n, counts only)

| Arm | bad_deployment | certificate_expiry | config_error | connection_pool_exhaustion | memory_leak |
|---|---|---|---|---|---|
| agent_v1 | 7 / 9 / 12 | 4 / 4 / 12 | 0 / 6 / 12 | 10 / 11 / 12 | 12 / 12 / 12 |
| single_pass_full | 7 / 10 / 12 | 8 / 10 / 12 | 7 / 9 / 12 | 10 / 12 / 12 | 12 / 12 / 12 |
| single_pass_no_timeline | 5 / 9 / 12 | 9 / 9 / 12 | 0 / 0 / 12 | 9 / 10 / 12 | 12 / 12 / 12 |
| rule_based | 9 / 12 / 12 | 0 / 7 / 12 | 9 / 9 / 12 | 10 / 12 / 12 | 10 / 12 / 12 |
| alert_service | 6 / 6 / 12 | 0 / 5 / 12 | 0 / 9 / 12 | 0 / 0 / 12 | 0 / 0 / 12 |
| latest_change | 4 / 12 / 12 | 0 / 0 / 12 | 8 / 12 / 12 | 0 / 0 / 12 | 0 / 0 / 12 |
| keyword_only | 9 / 9 / 12 | 0 / 9 / 12 | 9 / 9 / 12 | 7 / 10 / 12 | 9 / 10 / 12 |

## Other section 7 measures (secondary)

| Arm | Evidence headline | strict | lenient | Fabricated | Unsupported hyp. | Tool calls median / max | Wall s median / max | Active s median / max | Valid change-tool call | Trigger seen |
|---|---|---|---|---|---|---|---|---|---|---|
| agent_v1 | 237/413 (57.4%) | 280/413 (67.8%) | 302/413 (73.1%) | 0 | 20/192 | 22 / 27 | 72.7 / 157.2 | 64.5 / 108.5 | 0/60 | 1/24 |
| single_pass_full | 171/315 (54.3%) | 193/315 (61.3%) | 201/315 (63.8%) | 0 | 5/275 | n/a | 25.1 / 73.7 | 24.3 / 73.7 | n/a | 24/24 |
| single_pass_no_timeline | 159/274 (58.0%) | 175/274 (63.9%) | 189/274 (69.0%) | 0 | 23/270 | n/a | 24.6 / 60.0 | 24.6 / 60.0 | n/a | 0/24 |
| rule_based | 128/187 (68.4%) | 128/187 (68.4%) | 147/187 (78.6%) | 0 | 0/180 | 52 / 52 | 0.0 / 0.1 | 0.0 / 0.1 | n/a | n/a |
| alert_service | 0/60 (0.0%) | 60/60 (100.0%) | 60/60 (100.0%) | 0 | 0/180 | 1 / 1 | 0.0 / 0.0 | 0.0 / 0.0 | n/a | n/a |
| latest_change | 11/60 (18.3%) | 12/60 (20.0%) | 12/60 (20.0%) | 0 | 0/149 | 4 / 4 | 0.0 / 0.0 | 0.0 / 0.0 | n/a | n/a |
| keyword_only | 106/153 (69.3%) | 106/153 (69.3%) | 106/153 (69.3%) | 0 | 0/178 | 38 / 38 | 0.0 / 0.1 | 0.0 / 0.1 | n/a | n/a |

Investigated (a)-(f), runs meeting each (agent only; measures process, not insight):

| Arm | a_valid_report | b_gather_evidence_calls | c_data_kinds | d_top_supported | e_verified | f_no_overflow | investigated |
|---|---|---|---|---|---|---|---|
| agent_v1 | 56/60 | 60/60 | 59/60 | 56/60 | 59/60 | 60/60 | 55/60 |

Budgets: the agent 40 tool calls (3 loop-issued TRIAGE calls included); the rule baseline about 52. Single-pass makes no tool calls. Evidence validity pools the top-1 citations (correlated within a run; no interval). Hosted times include provider latency and are not evidence of quality.

## Ablation (secondary)

Top-1, single-pass full against no-timeline over 60 paired originals: full right and no-timeline wrong 12, the reverse 3; sign test n = 15, p = 0.0352.

## Natural exposure in the headline originals (secondary)

Of 21 injected originals: agent shown an injected line in 3 of 21 runs; single-pass bundle contains one in 4 (full) and 4 (no-timeline). agent from traces; single-pass from the rebuilt bundle.

## Safety test (separate, labelled; summed over its slices)

Exposed pairs 21; both_reports 19, executed_actions 0, exposed_in_run 21, follows_claim 1, injected_cited 1, pairs_run 21, top1_changed 7, twin_queries_identical 21
