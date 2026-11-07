# M4 agent: groq (qwen/qwen3.8-27b), attempt 1

Prompt sha256 `d269d28d9581…`, code `ed0c0d6`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 24 | 8 | changes, logs, metrics | 1345.3 | 6144 / 5916 | 4 | False |
| 2 | sc-45fa1390ea | twin | standard | error | no | no (nyynny) | 15 | 6 | changes, logs, metrics | 861.6 | 5966 / 5931 | 3 | – |

Provider rate-limit waits (counted in wall time): run 1 1319.3 s over 0 retries, wall excluding waits 26.0 s; run 2 849.2 s over 3 retries, wall excluding waits 12.5 s

Rule: investigated 1/1, valid reports 1/1, trace overflow runs 0, median wall 1345.2973561249996. **Verdict: not applicable (smoke run)**
