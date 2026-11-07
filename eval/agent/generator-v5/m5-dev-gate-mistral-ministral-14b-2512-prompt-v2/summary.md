# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `0a788479eb8c…`, code `390a573`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-47610c9e02 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | changes, logs, metrics | 63.0 | 6122 / 5710 | 4 | False |
| 2 | sc-694130798c | original | missing_evidence | context_exhausted | no | no (nyynyy) | 17 | 8 | changes, logs, metrics | 43.8 | 6130 / 5819 | 4 | – |
| 3 | sc-6d023322e9 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | changes, logs, metrics | 66.0 | 6084 / 5822 | 4 | True |
| 4 | sc-8e6dbe7f20 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | changes, logs, metrics | 59.7 | 6019 / 5702 | 4 | True |
| 5 | sc-918356ee90 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | changes, logs, metrics | 61.9 | 6134 / 5797 | 4 | True |
| 6 | sc-9969d4b81d | original | ambiguous | context_exhausted | no | no (nyynyy) | 20 | 10 | changes, logs, metrics | 52.5 | 6132 / 5742 | 4 | – |
| 7 | sc-a59e0e61c7 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 6 | changes, logs, metrics | 64.3 | 6076 / 5889 | 4 | False |
| 8 | sc-ba353abbc7 | original | standard | context_exhausted | no | no (nyynyy) | 20 | 8 | changes, logs, metrics | 52.8 | 6141 / 5882 | 4 | – |
| 9 | sc-be7c6ab28b | original | standard | no_new_evidence | no | no (nnynny) | 8 | 2 | changes, logs | 12.3 | 5710 / 5280 | 3 | – |
| 10 | sc-be91d5105d | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | changes, logs, metrics | 63.1 | 6143 / 5884 | 4 | True |
| 11 | sc-bf8ef04f56 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 21 | 5 | changes, logs, metrics | 63.2 | 6116 / 5890 | 4 | False |
| 12 | sc-c1e7d959c8 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 9 | changes, logs, metrics | 79.0 | 6143 / 5942 | 4 | True |
| 13 | sc-cc007aa1ee | original | ambiguous | context_exhausted | no | no (nyynyy) | 17 | 8 | changes, logs, metrics | 44.5 | 6116 / 5785 | 4 | – |
| 14 | sc-d74c46a899 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 8 | changes, logs, metrics | 69.4 | 6083 / 5797 | 4 | True |
| 15 | sc-dca259caa6 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 19 | 6 | changes, logs, metrics | 59.0 | 6110 / 5634 | 4 | True |
| 16 | sc-df583a5a54 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 19 | 6 | changes, logs, metrics | 64.3 | 6144 / 5609 | 4 | True |
| 17 | sc-e2cea1c0c0 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 23 | 8 | changes, logs, metrics | 84.6 | 6065 / 5848 | 4 | True |
| 18 | sc-ec3e7c879f | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 23 | 7 | changes, logs, metrics | 71.1 | 6142 / 5940 | 4 | True |
| 19 | sc-f7e6249083 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | changes, logs, metrics | 69.1 | 6081 / 5851 | 4 | True |
| 20 | sc-fada5df47f | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 20 | 5 | changes, logs, metrics | 67.0 | 6128 / 5920 | 4 | True |
| 21 | sc-fb1c777397 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 21 | 5 | changes, logs, metrics | 68.3 | 6138 / 5847 | 4 | False |
| 22 | sc-ff655f01df | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 21 | 6 | changes, logs, metrics | 63.4 | 6116 / 5830 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 7.5 s over 0 retries, wall excluding waits 55.5 s; run 2 9.3 s over 0 retries, wall excluding waits 34.6 s; run 3 11.7 s over 0 retries, wall excluding waits 54.3 s; run 4 13.0 s over 0 retries, wall excluding waits 46.6 s; run 5 11.1 s over 0 retries, wall excluding waits 50.8 s; run 6 8.6 s over 0 retries, wall excluding waits 43.9 s; run 7 13.5 s over 0 retries, wall excluding waits 50.9 s; run 8 8.9 s over 0 retries, wall excluding waits 43.9 s; run 9 3.6 s over 0 retries, wall excluding waits 8.8 s; run 10 10.2 s over 0 retries, wall excluding waits 53.0 s; run 11 11.1 s over 0 retries, wall excluding waits 52.1 s; run 12 11.7 s over 0 retries, wall excluding waits 67.2 s; run 13 6.4 s over 0 retries, wall excluding waits 38.1 s; run 14 10.9 s over 0 retries, wall excluding waits 58.5 s; run 15 8.3 s over 0 retries, wall excluding waits 50.7 s; run 16 7.9 s over 0 retries, wall excluding waits 56.4 s; run 17 8.2 s over 0 retries, wall excluding waits 76.4 s; run 18 8.2 s over 0 retries, wall excluding waits 62.9 s; run 19 8.8 s over 0 retries, wall excluding waits 60.3 s; run 20 5.0 s over 0 retries, wall excluding waits 62.0 s; run 21 5.6 s over 0 retries, wall excluding waits 62.6 s; run 22 8.5 s over 0 retries, wall excluding waits 54.9 s

Rule: investigated 17/22, valid reports 17/22, trace overflow runs 0, median wall 63.31855025000186, median active 53.61799600050726 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: works_locally**
