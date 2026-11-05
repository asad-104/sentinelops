# M5 single-pass baseline (no-timeline): mistral (ministral-14b-2512), attempt 1

Hash `e4acb736ce5b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-05c57ba12f | standard | sufficient_evidence | yes | True | True | 2 | 5522 | – |
| 2 | sc-065074775d | standard | error | no | False | False | 2 | 5495 | – |
| 3 | sc-0aa14e8087 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5666 | – |
| 4 | sc-0d1bfba9dc | ambiguous | error | no | False | False | 2 | 5358 | – |
| 5 | sc-112b0c8f69 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5203 | – |
| 6 | sc-11a73721f7 | missing_evidence | sufficient_evidence | yes | False | False | 2 | 5077 | – |
| 7 | sc-1200cd7f9f | missing_evidence | sufficient_evidence | yes | False | False | 1 | 4966 | – |
| 8 | sc-14d713e967 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5549 | – |
| 9 | sc-161173fd11 | missing_evidence | error | no | False | False | 2 | 5827 | – |
| 10 | sc-1d8e8a8caa | ambiguous | sufficient_evidence | yes | True | True | 1 | 5283 | – |

valid reports 7/10, top-1 5/10, top-3 5/10
