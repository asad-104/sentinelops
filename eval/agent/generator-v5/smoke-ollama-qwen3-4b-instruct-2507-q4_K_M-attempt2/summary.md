# M4 agent: ollama (qwen3:4b-instruct-2507-q4_K_M), attempt 2

Prompt sha256 `d269d28d9581…`, code `66dc483`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | error | no | no (nyynny) | 18 | 5 | changes, logs, metrics | 169.0 | 6081 / 5303 | 3 | – |
| 2 | sc-45fa1390ea | twin | standard | sufficient_evidence | yes | yes (yyyyyy) | 19 | 7 | logs, metrics | 297.1 | 6139 / 5238 | 4 | False |

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 168.95260687500001. **Verdict: not applicable (smoke run)**
