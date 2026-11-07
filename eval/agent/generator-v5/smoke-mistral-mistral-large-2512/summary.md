# M4 agent: mistral (mistral-large-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `6154875`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | error | no | no (nnnnny) | 3 | 0 | – | 1.5 | 4455 / None | 0 | – |
| 2 | sc-45fa1390ea | twin | standard | error | no | no (nnnnny) | 3 | 0 | – | 2.4 | 4455 / None | 0 | – |

Provider rate-limit waits (counted in wall time): run 1 0.2 s over 0 retries, wall excluding waits 1.4 s; run 2 1.7 s over 0 retries, wall excluding waits 0.6 s

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 1.519638167001176. **Verdict: not applicable (smoke run)**
