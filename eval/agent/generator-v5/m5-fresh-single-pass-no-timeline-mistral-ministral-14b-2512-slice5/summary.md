# M5 single-pass baseline (no-timeline): mistral (ministral-14b-2512), attempt 1

Hash `e4acb736ce5b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-9c186c309c | standard | sufficient_evidence | yes | True | True | 1 | 5432 | – |
| 2 | sc-a01526b2d1 | missing_evidence | sufficient_evidence | yes | False | True | 1 | 4977 | – |
| 3 | sc-a5c4288d13 | standard | sufficient_evidence | yes | True | True | 1 | 5298 | – |
| 4 | sc-a724d62702 | standard | sufficient_evidence | yes | True | True | 1 | 5426 | – |
| 5 | sc-b1596d0b2e | ambiguous | sufficient_evidence | yes | False | True | 1 | 5667 | – |
| 6 | sc-c1c14f1dff | standard | sufficient_evidence | yes | True | True | 2 | 5614 | – |
| 7 | sc-c98178998c | standard | sufficient_evidence | yes | True | True | 1 | 5494 | – |
| 8 | sc-d0affadab8 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5058 | – |
| 9 | sc-d480b03292 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5070 | – |
| 10 | sc-d858fb6e4d | missing_evidence | sufficient_evidence | yes | False | False | 1 | 4806 | – |

valid reports 10/10, top-1 7/10, top-3 9/10
