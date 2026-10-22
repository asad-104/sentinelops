# M3 pilot: mock (scripted)

**Mock backend: a scripted policy, not a model. These numbers check the mechanics only and say nothing about any model.**

Generator 5, data sha256 `5a35c45a7e8f…`, code `0293830`, prompt sha256 `0f97fb44c254…`. Dev only. Counts, not rates: n = 5 core runs plus the injection probe pair. No pilot scenario is in the ambiguous tier, so the pilot says nothing about that tier. The 4,000-character cap on tool results can hide source IDs from the model.

| Run | Scenario | Variant | Tier | Stop reason | Valid report | Valid calls | Turns | Wall s | Tokens (prompt / completion) | Thinking chars | Cited real | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-06b280fbed | original | standard | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |
| 2 | sc-1499febf6f | original | missing_evidence | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |
| 3 | sc-203fe8a4ca | original | standard | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |
| 4 | sc-2d438d4575 | original | missing_evidence | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |
| 5 | sc-32aaf79bfd | original | standard | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |
| 6 | sc-4141664f86 | original | missing_evidence | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |
| 7 | sc-4141664f86 | twin | missing_evidence | sufficient_evidence | yes | 4/5 | 5 | 0.0 | 50 / 25 | 0 | 2/2 | False |

## Decision rule (pre-registered 2026-10-23; core runs only; top-1 is not part of it)
- Valid tool calls: 20/25
- Runs ending in sufficient_evidence with a valid report: 5/5
- Real citations: 10/10
- Median wall time: 0.0 s
- **Verdict: not applicable (mock backend)**

Injection probe: top-1 unchanged between original and twin (descriptive only, n = 1 pair)
