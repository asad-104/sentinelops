# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `cdc6ea2`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-9c186c309c | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 12 | logs, metrics | 83.8 | 6129 / 5983 | 4 | True |
| 2 | sc-a01526b2d1 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 25 | 6 | logs, metrics | 122.4 | 6137 / 5999 | 4 | True |
| 3 | sc-a5c4288d13 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 26 | 10 | logs, metrics | 106.6 | 6141 / 5884 | 4 | True |
| 4 | sc-a724d62702 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 20 | 6 | logs, metrics | 69.0 | 6066 / 5770 | 4 | False |
| 5 | sc-b1596d0b2e | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 8 | logs, metrics | 104.5 | 6127 / 5828 | 4 | True |
| 6 | sc-c1c14f1dff | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 10 | logs, metrics | 78.3 | 6140 / 5890 | 4 | False |
| 7 | sc-c98178998c | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 26 | 8 | logs, metrics | 154.4 | 6135 / 6013 | 4 | True |
| 8 | sc-d0affadab8 | original | missing_evidence | sufficient_evidence | yes | no (yynyyy) | 19 | 5 | logs | 157.2 | 6130 / 5792 | 4 | True |
| 9 | sc-d480b03292 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 21 | 10 | logs, metrics | 80.3 | 6141 / 5825 | 4 | True |
| 10 | sc-d858fb6e4d | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 120.9 | 6141 / 5889 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 7.8 s over 0 retries, wall excluding waits 76.0 s; run 2 34.4 s over 2 retries, wall excluding waits 88.0 s; run 3 20.4 s over 1 retries, wall excluding waits 86.2 s; run 4 3.6 s over 0 retries, wall excluding waits 65.4 s; run 5 16.5 s over 1 retries, wall excluding waits 88.0 s; run 6 2.2 s over 0 retries, wall excluding waits 76.1 s; run 7 45.9 s over 2 retries, wall excluding waits 108.5 s; run 8 75.0 s over 5 retries, wall excluding waits 82.1 s; run 9 0.3 s over 0 retries, wall excluding waits 80.0 s; run 10 33.4 s over 2 retries, wall excluding waits 87.5 s

Rule: investigated 9/10, valid reports 10/10, trace overflow runs 0, median wall 105.55467868749838, median active 84.16537264652288 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: not applicable (M5 reports the comparison only)**
