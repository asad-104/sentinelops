# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `cdc6ea2`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-7577f19d1b | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | logs, metrics | 65.7 | 6025 / 5961 | 4 | False |
| 2 | sc-76d4881991 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 10 | logs, metrics | 79.1 | 6141 / 5840 | 4 | False |
| 3 | sc-7e6b907afe | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 10 | logs, metrics | 83.0 | 6140 / 5956 | 4 | True |
| 4 | sc-83b8725d48 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 25 | 10 | logs, metrics | 80.3 | 6135 / 6060 | 4 | False |
| 5 | sc-8a2124d02a | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 27 | 10 | logs, metrics | 87.7 | 5971 / 5781 | 4 | True |
| 6 | sc-8e89b7f797 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 71.6 | 6131 / 5962 | 4 | True |
| 7 | sc-8f71122f15 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 9 | logs, metrics | 73.5 | 6142 / 5874 | 4 | True |
| 8 | sc-9025e811cc | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 26 | 13 | logs, metrics | 94.8 | 6120 / 5941 | 4 | True |
| 9 | sc-95cc2de814 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 13 | logs, metrics | 87.5 | 6143 / 5944 | 4 | False |
| 10 | sc-96ea8f008e | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 23 | 9 | logs, metrics | 93.2 | 5999 / 5735 | 4 | True |

Provider rate-limit waits (counted in wall time): run 1 3.7 s over 0 retries, wall excluding waits 62.0 s; run 2 5.9 s over 0 retries, wall excluding waits 73.3 s; run 3 3.2 s over 0 retries, wall excluding waits 79.9 s; run 4 6.1 s over 0 retries, wall excluding waits 74.2 s; run 5 6.8 s over 0 retries, wall excluding waits 80.9 s; run 6 4.9 s over 0 retries, wall excluding waits 66.7 s; run 7 6.4 s over 0 retries, wall excluding waits 67.1 s; run 8 5.2 s over 0 retries, wall excluding waits 89.6 s; run 9 5.0 s over 0 retries, wall excluding waits 82.5 s; run 10 17.6 s over 1 retries, wall excluding waits 75.6 s

Rule: investigated 10/10, valid reports 10/10, trace overflow runs 0, median wall 81.6495740409955, median active 74.88380599949305 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: not applicable (M5 reports the comparison only)**
