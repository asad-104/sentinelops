# M5 single-pass baseline (full): mistral (ministral-14b-2512), attempt 1

Hash `2bf74a3f683b…`, code `390a573`. One request per scenario, a fixed evidence bundle, frozen before the first call and never tuned. Counts, not rates.

| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |
|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-47610c9e02 | ambiguous | sufficient_evidence | yes | False | True | 2 | 5832 | – |
| 2 | sc-694130798c | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5965 | – |
| 3 | sc-6d023322e9 | standard | sufficient_evidence | yes | True | True | 1 | 6005 | – |
| 4 | sc-8e6dbe7f20 | standard | sufficient_evidence | yes | True | True | 1 | 5838 | – |
| 5 | sc-918356ee90 | standard | sufficient_evidence | yes | True | True | 1 | 6109 | – |
| 6 | sc-9969d4b81d | ambiguous | sufficient_evidence | yes | False | False | 1 | 5512 | – |
| 7 | sc-a59e0e61c7 | standard | sufficient_evidence | yes | True | True | 1 | 5415 | – |
| 8 | sc-ba353abbc7 | standard | sufficient_evidence | yes | True | True | 1 | 5704 | – |
| 9 | sc-be7c6ab28b | standard | sufficient_evidence | yes | True | True | 2 | 5750 | – |
| 10 | sc-be91d5105d | standard | sufficient_evidence | yes | True | True | 1 | 5602 | – |
| 11 | sc-bf8ef04f56 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5894 | – |
| 12 | sc-c1e7d959c8 | standard | sufficient_evidence | yes | True | True | 1 | 5611 | – |
| 13 | sc-cc007aa1ee | ambiguous | sufficient_evidence | yes | True | True | 2 | 5973 | – |
| 14 | sc-d74c46a899 | standard | sufficient_evidence | yes | True | True | 1 | 5870 | – |
| 15 | sc-dca259caa6 | missing_evidence | sufficient_evidence | yes | True | True | 2 | 5623 | – |
| 16 | sc-df583a5a54 | standard | sufficient_evidence | yes | True | True | 1 | 6090 | – |
| 17 | sc-e2cea1c0c0 | ambiguous | sufficient_evidence | yes | True | True | 1 | 5856 | – |
| 18 | sc-ec3e7c879f | missing_evidence | sufficient_evidence | yes | True | True | 1 | 5893 | – |
| 19 | sc-f7e6249083 | standard | sufficient_evidence | yes | True | True | 1 | 5841 | – |
| 20 | sc-fada5df47f | missing_evidence | sufficient_evidence | yes | True | True | 2 | 5454 | – |
| 21 | sc-fb1c777397 | ambiguous | sufficient_evidence | yes | True | True | 1 | 6120 | – |
| 22 | sc-ff655f01df | ambiguous | sufficient_evidence | yes | True | True | 1 | 5673 | – |

valid reports 22/22, top-1 20/22, top-3 21/22
