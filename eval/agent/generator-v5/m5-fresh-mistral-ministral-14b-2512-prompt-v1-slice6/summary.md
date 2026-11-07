# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `cdc6ea2`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-d8730ff208 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 9 | logs, metrics | 72.1 | 6128 / 5958 | 4 | True |
| 2 | sc-dc18a6e0b7 | original | standard | context_exhausted | no | no (nyynny) | 19 | 9 | logs, metrics | 51.9 | 6116 / 5820 | 3 | – |
| 3 | sc-e1bf6642a1 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 11 | logs, metrics | 88.2 | 6016 / 5831 | 4 | True |
| 4 | sc-e1d0178552 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 23 | 8 | logs, metrics | 73.2 | 6023 / 5922 | 4 | False |
| 5 | sc-e6b7d5c7f2 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 71.5 | 6015 / 5790 | 4 | True |
| 6 | sc-e9b5e3681a | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 66.1 | 6141 / 5933 | 4 | True |
| 7 | sc-ecef41eac7 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 24 | 6 | logs, metrics | 71.6 | 6136 / 6071 | 4 | False |
| 8 | sc-f648c2a4b9 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 9 | changes, logs, metrics | 71.1 | 6140 / 5890 | 4 | True |
| 9 | sc-f70fe24b38 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 8 | logs, metrics | 68.5 | 6131 / 5958 | 4 | False |
| 10 | sc-fcd6a60def | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 67.6 | 6133 / 5944 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 5.0 s over 0 retries, wall excluding waits 67.1 s; run 2 5.6 s over 0 retries, wall excluding waits 46.2 s; run 3 13.4 s over 0 retries, wall excluding waits 74.8 s; run 4 9.5 s over 0 retries, wall excluding waits 63.7 s; run 5 10.2 s over 0 retries, wall excluding waits 61.3 s; run 6 7.9 s over 0 retries, wall excluding waits 58.2 s; run 7 12.2 s over 0 retries, wall excluding waits 59.4 s; run 8 9.1 s over 0 retries, wall excluding waits 62.0 s; run 9 10.6 s over 0 retries, wall excluding waits 57.9 s; run 10 10.3 s over 0 retries, wall excluding waits 57.3 s

Rule: investigated 9/10, valid reports 9/10, trace overflow runs 0, median wall 71.2973226039976, median active 60.33822597650433 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: not applicable (M5 reports the comparison only)**
