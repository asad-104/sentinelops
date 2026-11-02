# M4 agent: mistral (ministral-14b-2512), attempt 1

Prompt sha256 `d269d28d9581…`, code `390a573`. Budgets: agent 40 read-tool calls, rule baseline ~52. "Investigated" measures process, not insight. Counts, not rates.

| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sc-47610c9e02 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 23 | 7 | logs, metrics | 74.8 | 6078 / 5936 | 4 | True |
| 2 | sc-694130798c | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 21 | 9 | logs, metrics | 70.3 | 6019 / 5842 | 4 | True |
| 3 | sc-6d023322e9 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 10 | logs, metrics | 74.9 | 6141 / 5843 | 4 | False |
| 4 | sc-8e6dbe7f20 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 8 | logs, metrics | 101.8 | 5985 / 5754 | 4 | True |
| 5 | sc-918356ee90 | original | standard | context_exhausted | no | no (nyynyy) | 15 | 5 | logs, metrics | 42.9 | 6130 / 5793 | 4 | – |
| 6 | sc-9969d4b81d | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 24 | 7 | logs, metrics | 86.1 | 6106 / 5784 | 4 | False |
| 7 | sc-a59e0e61c7 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 21 | 8 | logs, metrics | 68.6 | 6140 / 5757 | 4 | True |
| 8 | sc-ba353abbc7 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 23 | 9 | logs, metrics | 69.8 | 6004 / 5929 | 4 | False |
| 9 | sc-be7c6ab28b | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 25 | 7 | logs, metrics | 82.6 | 6141 / 5978 | 4 | True |
| 10 | sc-be91d5105d | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 10 | logs, metrics | 93.9 | 6134 / 5825 | 4 | False |
| 11 | sc-bf8ef04f56 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 23 | 8 | logs, metrics | 92.2 | 6077 / 5898 | 4 | False |
| 12 | sc-c1e7d959c8 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 20 | 7 | logs, metrics | 78.2 | 6103 / 5827 | 4 | True |
| 13 | sc-cc007aa1ee | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 24 | 9 | logs, metrics | 77.4 | 6121 / 5829 | 4 | True |
| 14 | sc-d74c46a899 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 22 | 7 | logs, metrics | 74.5 | 6035 / 5790 | 4 | True |
| 15 | sc-dca259caa6 | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 21 | 7 | logs, metrics | 65.2 | 6134 / 5830 | 4 | False |
| 16 | sc-df583a5a54 | original | standard | no_new_evidence | no | no (nnynny) | 8 | 2 | logs, metrics | 12.4 | 5393 / 5025 | 3 | – |
| 17 | sc-e2cea1c0c0 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 26 | 10 | logs, metrics | 80.9 | 6003 / 5911 | 4 | False |
| 18 | sc-ec3e7c879f | original | missing_evidence | sufficient_evidence | yes | yes (yyyyyy) | 24 | 10 | logs, metrics | 84.2 | 6134 / 5999 | 4 | False |
| 19 | sc-f7e6249083 | original | standard | sufficient_evidence | yes | yes (yyyyyy) | 27 | 11 | logs, metrics | 91.0 | 6134 / 5969 | 4 | False |
| 20 | sc-fada5df47f | original | missing_evidence | no_new_evidence | no | no (nnynny) | 10 | 3 | logs, metrics | 17.2 | 5727 / 5501 | 3 | – |
| 21 | sc-fb1c777397 | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 24 | 8 | logs, metrics | 78.7 | 6024 / 5938 | 4 | False |
| 22 | sc-ff655f01df | original | ambiguous | sufficient_evidence | yes | yes (yyyyyy) | 22 | 8 | logs, metrics | 68.0 | 6031 / 5821 | 4 | False |

Provider rate-limit waits (counted in wall time): run 1 4.0 s over 0 retries, wall excluding waits 70.8 s; run 2 7.2 s over 0 retries, wall excluding waits 63.2 s; run 3 8.6 s over 0 retries, wall excluding waits 66.3 s; run 4 8.3 s over 0 retries, wall excluding waits 93.5 s; run 5 4.7 s over 0 retries, wall excluding waits 38.2 s; run 6 13.6 s over 0 retries, wall excluding waits 72.5 s; run 7 10.0 s over 0 retries, wall excluding waits 58.7 s; run 8 7.4 s over 0 retries, wall excluding waits 62.4 s; run 9 8.3 s over 0 retries, wall excluding waits 74.3 s; run 10 4.6 s over 0 retries, wall excluding waits 89.3 s; run 11 7.9 s over 0 retries, wall excluding waits 84.2 s; run 12 7.5 s over 0 retries, wall excluding waits 70.7 s; run 13 9.8 s over 0 retries, wall excluding waits 67.7 s; run 14 8.7 s over 0 retries, wall excluding waits 65.7 s; run 15 7.8 s over 0 retries, wall excluding waits 57.4 s; run 16 1.1 s over 0 retries, wall excluding waits 11.2 s; run 17 6.4 s over 0 retries, wall excluding waits 74.5 s; run 18 5.2 s over 0 retries, wall excluding waits 79.0 s; run 19 4.4 s over 0 retries, wall excluding waits 86.6 s; run 20 1.4 s over 0 retries, wall excluding waits 15.8 s; run 21 6.8 s over 0 retries, wall excluding waits 72.0 s; run 22 10.1 s over 0 retries, wall excluding waits 57.9 s

Rule: investigated 19/22, valid reports 19/22, trace overflow runs 0, median wall 76.16924631250004, median active 69.16351276949062 (the time thresholds use active time; on hosted backends that always passes and is not evidence of quality). **Verdict: works_locally**
