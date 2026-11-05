# M5 single-pass baseline (no-timeline): mistral (ministral-14b-2512), attempt 1

Hash `e4acb736ce5b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-4c85022a2c | standard | error | no | False | False | 2 | 5596 | – |
| 2 | sc-52263b6770 | standard | sufficient_evidence | yes | False | False | 1 | 5273 | – |
| 3 | sc-56bd812449 | missing_evidence | error | no | False | False | 2 | 4985 | – |
| 4 | sc-584c55df9a | standard | sufficient_evidence | yes | False | False | 1 | 5281 | – |
| 5 | sc-5e481a8387 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5478 | – |
| 6 | sc-5f87f3ce59 | standard | sufficient_evidence | yes | True | True | 2 | 5227 | – |
| 7 | sc-5fda7149c6 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5423 | – |
| 8 | sc-65adda6d50 | standard | error | no | False | False | 2 | 5352 | – |
| 9 | sc-6a4f160b9b | ambiguous | sufficient_evidence | yes | True | True | 1 | 5755 | – |
| 10 | sc-6c006fa3a3 | standard | sufficient_evidence | yes | False | False | 1 | 5456 | – |

valid reports 7/10, top-1 4/10, top-3 4/10
