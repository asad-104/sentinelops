# M3 pilot: ollama (qwen3:4b)

Generator 5, data sha256 `5a35c45a7e8f…`, code `e25480b-dirty`, prompt sha256 `0f97fb44c254…`. Dev only. Counts, not rates: n = 1 core runs plus the injection probe pair. No pilot scenario is in the ambiguous tier, so the pilot says nothing about that tier. The 4,000-character cap on tool results can hide source IDs from the model.

| Run | Scenario | Variant | Tier | Stop reason | Valid report | Valid calls | Turns | Wall s | Tokens (prompt / completion) | Thinking chars | Cited real | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-2c422896a9 | original | ambiguous | sufficient_evidence | yes | 3/3 | 3 | 176.6 | 8854 / 3232 | 0 | 6/6 | True |

## Decision rule (pre-registered 2026-10-23; core runs only; top-1 is not part of it)
- Valid tool calls: 3/3
- Runs ending in sufficient_evidence with a valid report: 1/1
- Real citations: 6/6
- Median wall time: 176.6 s
- **Verdict: not applicable (smoke run)**

Injection probe: not run
