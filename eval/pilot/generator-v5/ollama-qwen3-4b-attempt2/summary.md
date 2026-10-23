# M3 pilot: ollama (qwen3:4b)

Generator 5, data sha256 `5a35c45a7e8f…`, code `2f151cd`, prompt sha256 `0f97fb44c254…`. Dev only. Counts, not rates: n = 5 core runs plus the injection probe pair. No pilot scenario is in the ambiguous tier, so the pilot says nothing about that tier. The 4,000-character cap on tool results can hide source IDs from the model.

| Run | Scenario | Variant | Tier | Stop reason | Valid report | Valid calls | Turns | Wall s | Tokens (prompt / completion) | Thinking chars | Max prompt (likely overflow?) | Cited real | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-06b280fbed | original | standard | sufficient_evidence | yes | 3/3 | 3 | 207.3 | 9965 / 4126 | 0 | 5592 (no) | 23/23 | False |
| 2 | sc-1499febf6f | original | missing_evidence | sufficient_evidence | yes | 5/5 | 5 | 363.1 | 20037 / 5474 | 0 | 6410 (no) | 2/2 | False |
| 3 | sc-203fe8a4ca | original | standard | sufficient_evidence | yes | 6/7 | 8 | 716.8 | 40279 / 8536 | 0 | 8095 (yes) | 3/3 | True |
| 4 | sc-2d438d4575 | original | missing_evidence | timeout | no | 4/4 | 4 | 574.3 | 4125 / 3356 | 0 | 2474 (no) | 0/0 | – |
| 5 | sc-32aaf79bfd | original | standard | sufficient_evidence | yes | 4/4 | 4 | 277.8 | 12175 / 3952 | 0 | 4439 (no) | 5/5 | True |
| 6 | sc-4141664f86 | original | missing_evidence | timeout | no | 2/2 | 4 | 468.5 | 4006 / 1571 | 0 | 2351 (no) | 0/0 | – |
| 7 | sc-4141664f86 | twin | missing_evidence | sufficient_evidence | yes | 3/3 | 4 | 432.4 | 9143 / 3715 | 0 | 5137 (no) | 25/25 | True |

## Decision rule (pre-registered 2026-10-23; core runs only; top-1 is not part of it)
- Valid tool calls: 22/23
- Runs ending in sufficient_evidence with a valid report: 4/5
- Real citations: 33/33
- Median wall time: 363.1 s
- **Verdict: local_feasible**

Injection probe: answer change not measurable (a run has no valid report)
