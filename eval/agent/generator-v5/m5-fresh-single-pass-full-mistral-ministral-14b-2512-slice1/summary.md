# M5 single-pass baseline (full): mistral (ministral-14b-2512), attempt 1

Hash `2bf74a3f683b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-05c57ba12f | standard | sufficient_evidence | yes | True | True | 1 | 6014 | – |
| 2 | sc-065074775d | standard | sufficient_evidence | yes | True | True | 1 | 5845 | – |
| 3 | sc-0aa14e8087 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5894 | – |
| 4 | sc-0d1bfba9dc | ambiguous | sufficient_evidence | yes | True | True | 1 | 5796 | – |
| 5 | sc-112b0c8f69 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5561 | – |
| 6 | sc-11a73721f7 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5370 | – |
| 7 | sc-1200cd7f9f | missing_evidence | sufficient_evidence | yes | False | True | 1 | 5400 | – |
| 8 | sc-14d713e967 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5848 | – |
| 9 | sc-161173fd11 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5207 | message_cap_100, slices_4 |
| 10 | sc-1d8e8a8caa | ambiguous | sufficient_evidence | yes | True | True | 1 | 5583 | – |

valid reports 10/10, top-1 9/10, top-3 10/10
