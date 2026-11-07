# M5 single-pass baseline (no-timeline): mistral (ministral-14b-2512), attempt 1

Hash `e4acb736ce5b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-7577f19d1b | missing_evidence | sufficient_evidence | yes | False | False | 1 | 5063 | – |
| 2 | sc-76d4881991 | standard | sufficient_evidence | yes | True | True | 1 | 5351 | – |
| 3 | sc-7e6b907afe | standard | sufficient_evidence | yes | True | True | 1 | 5597 | – |
| 4 | sc-83b8725d48 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 4885 | – |
| 5 | sc-8a2124d02a | ambiguous | sufficient_evidence | yes | True | True | 1 | 5637 | – |
| 6 | sc-8e89b7f797 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5000 | – |
| 7 | sc-8f71122f15 | standard | sufficient_evidence | yes | True | True | 1 | 5655 | – |
| 8 | sc-9025e811cc | standard | sufficient_evidence | yes | True | True | 1 | 5494 | – |
| 9 | sc-95cc2de814 | standard | sufficient_evidence | yes | False | False | 1 | 5604 | – |
| 10 | sc-96ea8f008e | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5554 | – |

valid reports 10/10, top-1 8/10, top-3 8/10
