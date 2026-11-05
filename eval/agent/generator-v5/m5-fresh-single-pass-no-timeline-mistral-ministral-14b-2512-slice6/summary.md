# M5 single-pass baseline (no-timeline): mistral (ministral-14b-2512), attempt 1

Hash `e4acb736ce5b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-d8730ff208 | standard | sufficient_evidence | yes | True | True | 1 | 5187 | – |
| 2 | sc-dc18a6e0b7 | standard | sufficient_evidence | yes | True | True | 1 | 5432 | – |
| 3 | sc-e1bf6642a1 | standard | sufficient_evidence | yes | True | True | 1 | 5503 | – |
| 4 | sc-e1d0178552 | ambiguous | sufficient_evidence | yes | False | False | 1 | 5285 | – |
| 5 | sc-e6b7d5c7f2 | standard | sufficient_evidence | yes | True | True | 2 | 5578 | – |
| 6 | sc-e9b5e3681a | ambiguous | sufficient_evidence | yes | False | True | 1 | 5468 | – |
| 7 | sc-ecef41eac7 | missing_evidence | sufficient_evidence | yes | False | False | 2 | 5432 | – |
| 8 | sc-f648c2a4b9 | standard | sufficient_evidence | yes | True | True | 1 | 5600 | – |
| 9 | sc-f70fe24b38 | standard | sufficient_evidence | yes | False | False | 2 | 5272 | – |
| 10 | sc-fcd6a60def | ambiguous | sufficient_evidence | yes | False | False | 1 | 5589 | – |

valid reports 10/10, top-1 5/10, top-3 6/10
