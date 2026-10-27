# M4 agent: ollama (qwen3:4b), attempt 2

Prompt sha256 `39a474ebdeca…`, code `26f4813`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | error | no | no (nyynny) | 7 | 4 | changes, logs, metrics | 1487.1 | 6123 / 6176 | 0 | – |
| 2 | sc-45fa1390ea | twin | standard | error | no | no (nnynny) | 8 | 3 | changes, logs, metrics | 941.2 | 5945 / 5926 | 0 | – |

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 1487.0763267500001. **Verdict: not applicable (smoke run)**
