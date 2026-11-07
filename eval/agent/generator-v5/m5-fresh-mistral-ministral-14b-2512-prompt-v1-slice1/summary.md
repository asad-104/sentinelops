# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `cdc6ea2`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-05c57ba12f | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 8 | logs, metrics | 65.4 | 6141 / 5813 | 4 | False |
| 2 | sc-065074775d | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 8 | logs, metrics | 67.3 | 6135 / 5836 | 4 | False |
| 3 | sc-0aa14e8087 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 24 | 9 | logs, metrics | 72.0 | 6140 / 5984 | 4 | True |
| 4 | sc-0d1bfba9dc | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 65.3 | 6040 / 5747 | 4 | True |
| 5 | sc-112b0c8f69 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 24 | 8 | logs, metrics | 75.9 | 6090 / 5895 | 4 | True |
| 6 | sc-11a73721f7 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 71.4 | 6054 / 5956 | 4 | False |
| 7 | sc-1200cd7f9f | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 20 | 6 | logs, metrics | 64.8 | 5926 / 5660 | 4 | False |
| 8 | sc-14d713e967 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 10 | logs, metrics | 76.3 | 6138 / 5929 | 4 | True |
| 9 | sc-161173fd11 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 19 | 5 | logs, metrics | 65.6 | 6132 / 5888 | 4 | True |
| 10 | sc-1d8e8a8caa | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 25 | 11 | logs, metrics | 78.6 | 6053 / 5842 | 4 | True |

Provider rate-limit waits (counted in wall time): run 1 7.2 s over 0 retries, wall excluding waits 58.3 s; run 2 7.3 s over 0 retries, wall excluding waits 60.0 s; run 3 7.5 s over 0 retries, wall excluding waits 64.5 s; run 4 7.4 s over 0 retries, wall excluding waits 57.9 s; run 5 5.9 s over 0 retries, wall excluding waits 70.0 s; run 6 4.7 s over 0 retries, wall excluding waits 66.7 s; run 7 9.6 s over 0 retries, wall excluding waits 55.2 s; run 8 5.7 s over 0 retries, wall excluding waits 70.6 s; run 9 5.8 s over 0 retries, wall excluding waits 59.8 s; run 10 10.4 s over 0 retries, wall excluding waits 68.2 s

Rule: investigated 10/10, valid reports 10/10, trace overflow runs 0, median wall 69.34202747898962, median active 62.24352414649329 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: not applicable (M5 reports the comparison only)**
