# M5 single-pass baseline (no-timeline): mistral (ministral-14b-2512), attempt 1

Hash `e4acb736ce5b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-228de563cc | ambiguous | sufficient_evidence | yes | False | False | 1 | 5257 | – |
| 2 | sc-2b384227b2 | standard | sufficient_evidence | yes | True | True | 1 | 5547 | – |
| 3 | sc-2c5f30e96c | standard | sufficient_evidence | yes | True | True | 1 | 5624 | – |
| 4 | sc-2dbc378a2e | standard | sufficient_evidence | yes | False | False | 2 | 5338 | – |
| 5 | sc-2e574241de | ambiguous | sufficient_evidence | yes | True | True | 1 | 5385 | – |
| 6 | sc-30ee0ad0f8 | ambiguous | sufficient_evidence | yes | False | True | 1 | 5147 | – |
| 7 | sc-360e8e4d66 | missing_evidence | sufficient_evidence | yes | False | True | 1 | 5340 | – |
| 8 | sc-3e06d6193b | standard | sufficient_evidence | yes | True | True | 1 | 5447 | – |
| 9 | sc-439a222f06 | standard | sufficient_evidence | yes | True | True | 1 | 5315 | – |
| 10 | sc-47a1a72db2 | standard | sufficient_evidence | yes | True | True | 1 | 5391 | – |

valid reports 10/10, top-1 6/10, top-3 8/10
