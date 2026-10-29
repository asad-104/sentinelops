# M4 agent: mistral (mistral-small-2603), attempt 1

**Aborted: provider-caused stop in sc-45fa1390ea: provider-caused: http_status: HTTP 429 after 4 retries: {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}. Incomplete: counts as propose hosted.**

Prompt sha256 `d269d28d9581…`, code `8ad0147`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-45fa1390ea | original | standard | error | no | no (nnnnny) | 3 | 0 | – | 33.0 | 4455 / None | 0 | – |

Provider rate-limit waits (counted in wall time): run 1 30.0 s over 4 retries, wall excluding waits 3.0 s

Rule: investigated 0/1, valid reports 0/1, trace overflow runs 0, median wall 32.97127716599971. **Verdict: not applicable (smoke run)**
