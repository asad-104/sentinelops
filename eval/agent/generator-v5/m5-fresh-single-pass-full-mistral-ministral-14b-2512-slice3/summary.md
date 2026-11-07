# M5 single-pass baseline (full): mistral (ministral-14b-2512), attempt 1

Hash `2bf74a3f683b…`, code `cdc6ea2`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-4c85022a2c | standard | sufficient_evidence | yes | True | True | 1 | 6019 | – |
| 2 | sc-52263b6770 | standard | sufficient_evidence | yes | False | True | 1 | 5699 | – |
| 3 | sc-56bd812449 | missing_evidence | sufficient_evidence | yes | False | True | 1 | 5346 | – |
| 4 | sc-584c55df9a | standard | sufficient_evidence | yes | True | True | 1 | 5650 | – |
| 5 | sc-5e481a8387 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5778 | – |
| 6 | sc-5f87f3ce59 | standard | sufficient_evidence | yes | True | True | 2 | 5653 | – |
| 7 | sc-5fda7149c6 | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5784 | – |
| 8 | sc-65adda6d50 | standard | sufficient_evidence | yes | False | True | 1 | 5841 | – |
| 9 | sc-6a4f160b9b | ambiguous | sufficient_evidence | yes | True | True | 1 | 5989 | – |
| 10 | sc-6c006fa3a3 | standard | sufficient_evidence | yes | True | True | 2 | 5690 | – |

valid reports 10/10, top-1 7/10, top-3 10/10
