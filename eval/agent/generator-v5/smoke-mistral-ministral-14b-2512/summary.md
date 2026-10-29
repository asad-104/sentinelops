# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `8ad0147`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | context_exhausted | no | no (nyynny) | 19 | 7 | logs, metrics | 52.8 | 6141 / 5843 | 3 | – |
| 2 | sc-45fa1390ea | twin | standard | context_exhausted | no | no (nyynny) | 16 | 8 | logs, metrics | 60.8 | 6141 / 5912 | 3 | – |

Provider rate-limit waits (counted in wall time): run 1 0.5 s over 0 retries, wall excluding waits 52.3 s; run 2 2.0 s over 1 retries, wall excluding waits 58.8 s

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 52.77989304199946. **Verdict: not applicable (smoke run)**
