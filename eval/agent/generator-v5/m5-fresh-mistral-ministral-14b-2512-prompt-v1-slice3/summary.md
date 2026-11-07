# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `cdc6ea2`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-4c85022a2c | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 8 | logs, metrics | 78.3 | 6141 / 5892 | 4 | True |
| 2 | sc-52263b6770 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 6 | logs, metrics | 72.5 | 6141 / 5898 | 4 | False |
| 3 | sc-56bd812449 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 22 | 6 | logs, metrics | 68.4 | 6078 / 5814 | 4 | False |
| 4 | sc-584c55df9a | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 6 | logs, metrics | 68.1 | 6126 / 5874 | 4 | False |
| 5 | sc-5e481a8387 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 27 | 9 | logs, metrics | 81.9 | 6143 / 5941 | 4 | False |
| 6 | sc-5f87f3ce59 | original | standard | context_exhausted | no | no (nyynyy) | 24 | 13 | logs, metrics | 64.3 | 6127 / 5799 | 4 | – |
| 7 | sc-5fda7149c6 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 26 | 10 | logs, metrics | 79.1 | 6038 / 6026 | 4 | True |
| 8 | sc-65adda6d50 | original | standard | context_exhausted | no | no (nyynyy) | 17 | 8 | logs, metrics | 44.0 | 6089 / 5997 | 4 | – |
| 9 | sc-6a4f160b9b | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 26 | 9 | logs, metrics | 72.6 | 6070 / 5864 | 4 | True |
| 10 | sc-6c006fa3a3 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 5 | logs, metrics | 65.5 | 6095 / 5861 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 6.6 s over 0 retries, wall excluding waits 71.7 s; run 2 8.3 s over 0 retries, wall excluding waits 64.3 s; run 3 8.4 s over 0 retries, wall excluding waits 59.9 s; run 4 7.5 s over 0 retries, wall excluding waits 60.6 s; run 5 10.6 s over 0 retries, wall excluding waits 71.3 s; run 6 6.4 s over 0 retries, wall excluding waits 58.0 s; run 7 9.7 s over 0 retries, wall excluding waits 69.4 s; run 8 4.5 s over 0 retries, wall excluding waits 39.4 s; run 9 10.8 s over 0 retries, wall excluding waits 61.8 s; run 10 8.3 s over 0 retries, wall excluding waits 57.2 s

Rule: investigated 8/10, valid reports 8/10, trace overflow runs 0, median wall 70.4588142499997, median active 61.205916958508894 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: not applicable (M5 reports the comparison only)**
