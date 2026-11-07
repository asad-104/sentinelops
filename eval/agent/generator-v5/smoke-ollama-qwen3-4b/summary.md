# M4 agent: ollama (qwen3:4b), attempt 1

Prompt sha256 `bd63ce71ce34…`, code `50dbf88`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | error | no | no (nnynny) | 6 | 2 | changes, logs | 772.3 | 5379 / 4900 | 0 | – |
| 2 | sc-45fa1390ea | twin | standard | error | no | no (nnynny) | 5 | 2 | changes, logs | 898.5 | 5379 / 4900 | 0 | – |

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 772.318391. **Verdict: not applicable (smoke run)**
