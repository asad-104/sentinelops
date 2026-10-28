# M4 agent: ollama (qwen3:4b-instruct-2507-q4_K_M), attempt 1

Prompt sha256 `39a474ebdeca…`, code `31c8f83`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | no_new_evidence | no | no (nyynny) | 15 | 5 | changes, logs, metrics | 118.8 | 6081 / 5303 | 3 | – |
| 2 | sc-45fa1390ea | twin | standard | no_new_evidence | no | no (nyynny) | 11 | 5 | logs, metrics | 102.2 | 6139 / 5238 | 3 | – |

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 118.81577570900004. **Verdict: not applicable (smoke run)**
