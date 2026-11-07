# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `cdc6ea2`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-228de563cc | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 6 | logs, metrics | 66.5 | 6118 / 5838 | 4 | False |
| 2 | sc-2b384227b2 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 11 | logs, metrics | 85.1 | 6141 / 5914 | 4 | True |
| 3 | sc-2c5f30e96c | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 9 | logs, metrics | 68.7 | 6141 / 5887 | 4 | True |
| 4 | sc-2dbc378a2e | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 24 | 8 | logs, metrics | 72.8 | 6141 / 5883 | 4 | True |
| 5 | sc-2e574241de | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 25 | 10 | logs, metrics | 72.8 | 6141 / 5914 | 4 | True |
| 6 | sc-30ee0ad0f8 | original | ambiguous | context_exhausted | no | no (nyynyy) | 17 | 7 | logs, metrics | 47.0 | 6126 / 5893 | 4 | – |
| 7 | sc-360e8e4d66 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 21 | 8 | logs, metrics | 63.9 | 6091 / 5893 | 4 | True |
| 8 | sc-3e06d6193b | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | changes, logs, metrics | 73.3 | 6141 / 5785 | 4 | True |
| 9 | sc-439a222f06 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 8 | changes, logs, metrics | 72.0 | 6135 / 5763 | 4 | False |
| 10 | sc-47a1a72db2 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 25 | 7 | logs, metrics | 74.6 | 6119 / 5835 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 7.1 s over 0 retries, wall excluding waits 59.4 s; run 2 13.1 s over 0 retries, wall excluding waits 72.0 s; run 3 7.8 s over 0 retries, wall excluding waits 60.9 s; run 4 10.1 s over 0 retries, wall excluding waits 62.7 s; run 5 9.2 s over 0 retries, wall excluding waits 63.6 s; run 6 4.4 s over 0 retries, wall excluding waits 42.6 s; run 7 6.2 s over 0 retries, wall excluding waits 57.8 s; run 8 10.0 s over 0 retries, wall excluding waits 63.3 s; run 9 8.7 s over 0 retries, wall excluding waits 63.3 s; run 10 10.0 s over 0 retries, wall excluding waits 64.6 s

Rule: investigated 9/10, valid reports 9/10, trace overflow runs 0, median wall 72.41490833300486, median active 63.012051228528435 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: not applicable (M5 reports the comparison only)**
