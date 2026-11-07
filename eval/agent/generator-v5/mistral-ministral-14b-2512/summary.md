# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `17fe7f5`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-30385ffc64 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 25 | 10 | logs, metrics | 94.4 | 6120 / 5727 | 4 | True |
| 2 | sc-3836c69ef7 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 25 | 7 | logs, metrics | 103.8 | 6140 / 6013 | 4 | True |
| 3 | sc-3e3ceb314e | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 180.4 | 6142 / 5929 | 4 | True |
| 4 | sc-4001bf784c | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 22 | 6 | logs, metrics | 97.6 | 6098 / 6007 | 4 | True |
| 5 | sc-408b514aeb | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 9 | logs, metrics | 98.5 | 6074 / 5742 | 4 | True |
| 6 | sc-4251e8920a | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 23 | 7 | logs, metrics | 129.7 | 6127 / 5843 | 4 | True |
| 7 | sc-497fd61898 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 24 | 8 | logs, metrics | 245.7 | 6141 / 5899 | 4 | False |
| 8 | sc-5b55b772de | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 10 | logs, metrics | 224.5 | 6141 / 5871 | 4 | True |
| 9 | sc-5b55b772de | twin | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 10 | logs, metrics | 145.1 | 6141 / 5967 | 4 | True |
| 10 | sc-5c5b9b9197 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 26 | 10 | logs, metrics | 131.4 | 6140 / 6066 | 4 | True |
| 11 | sc-5c5b9b9197 | twin | standard | sufficient_evidence | yes | yes (yyyyyy) | 24 | 10 | logs, metrics | 153.4 | 6138 / 5953 | 4 | True |
| 12 | sc-91404ea5fc | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 23 | 7 | logs, metrics | 146.6 | 6012 / 5863 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 0.6 s over 0 retries, wall excluding waits 93.8 s; run 2 15.2 s over 1 retries, wall excluding waits 88.6 s; run 3 90.1 s over 5 retries, wall excluding waits 90.3 s; run 4 15.3 s over 1 retries, wall excluding waits 82.3 s; run 5 15.4 s over 1 retries, wall excluding waits 83.1 s; run 6 45.6 s over 3 retries, wall excluding waits 84.1 s; run 7 135.5 s over 7 retries, wall excluding waits 110.2 s; run 8 120.2 s over 4 retries, wall excluding waits 104.3 s; run 9 45.5 s over 3 retries, wall excluding waits 99.6 s; run 10 46.5 s over 3 retries, wall excluding waits 84.8 s; run 11 60.5 s over 4 retries, wall excluding waits 92.9 s; run 12 60.2 s over 4 retries, wall excluding waits 86.4 s

Rule: investigated 10/10, valid reports 10/10, trace overflow runs 0, median wall 130.5109495204979, median active 87.49925522949962 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: works_locally**
