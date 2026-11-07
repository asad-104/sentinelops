# M4 agent: mistral (ministral-14b-2512), attempt 2

Prompt sha256 `d269d28d9581…`, code `b969b0a`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 24 | 10 | logs, metrics | 244.4 | 6141 / 5937 | 4 | True |
| 2 | sc-45fa1390ea | twin | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 9 | logs, metrics | 213.4 | 6141 / 5970 | 4 | True |

Provider rate-limit waits (counted in wall time): run 1 90.0 s over 6 retries, wall excluding waits 154.4 s; run 2 75.0 s over 4 retries, wall excluding waits 138.4 s

Rule: investigated 1/1, valid reports 1/1, trace overflow runs 0, median wall 244.4459134580011. **Verdict: not applicable (smoke run)**
