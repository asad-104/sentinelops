# M5 single-pass baseline (full): mistral (ministral-14b-2512), attempt 1

Hash `2bf74a3f683b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-7577f19d1b | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5422 | – |
| 2 | sc-76d4881991 | standard | sufficient_evidence | yes | True | True | 2 | 5717 | – |
| 3 | sc-7e6b907afe | standard | sufficient_evidence | yes | True | True | 1 | 6035 | – |
| 4 | sc-83b8725d48 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5249 | – |
| 5 | sc-8a2124d02a | ambiguous | sufficient_evidence | yes | True | True | 1 | 6072 | – |
| 6 | sc-8e89b7f797 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5361 | – |
| 7 | sc-8f71122f15 | standard | sufficient_evidence | yes | True | True | 1 | 6022 | – |
| 8 | sc-9025e811cc | standard | sufficient_evidence | yes | True | True | 2 | 5792 | – |
| 9 | sc-95cc2de814 | standard | sufficient_evidence | yes | False | False | 1 | 5897 | – |
| 10 | sc-96ea8f008e | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5787 | – |

valid reports 10/10, top-1 9/10, top-3 9/10
