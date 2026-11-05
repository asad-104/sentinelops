# M5 single-pass baseline (full): mistral (ministral-14b-2512), attempt 1

Hash `2bf74a3f683b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-d8730ff208 | standard | sufficient_evidence | yes | True | True | 1 | 5627 | – |
| 2 | sc-dc18a6e0b7 | standard | error | no | False | False | 2 | 5861 | – |
| 3 | sc-e1bf6642a1 | standard | sufficient_evidence | yes | True | True | 2 | 5871 | – |
| 4 | sc-e1d0178552 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5587 | – |
| 5 | sc-e6b7d5c7f2 | standard | error | no | False | False | 2 | 5874 | – |
| 6 | sc-e9b5e3681a | ambiguous | sufficient_evidence | yes | False | True | 1 | 5758 | – |
| 7 | sc-ecef41eac7 | missing_evidence | sufficient_evidence | yes | False | True | 1 | 5659 | – |
| 8 | sc-f648c2a4b9 | standard | sufficient_evidence | yes | True | True | 1 | 6103 | – |
| 9 | sc-f70fe24b38 | standard | sufficient_evidence | yes | True | True | 2 | 5561 | – |
| 10 | sc-fcd6a60def | ambiguous | error | no | False | False | 2 | 5952 | – |

valid reports 7/10, top-1 5/10, top-3 7/10
