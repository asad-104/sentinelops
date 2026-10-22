# dev paired ablation

Generator version 5, data sha256 `5a35c45a7e8f…`, code `e8c9279`. Each row pairs the dev scenarios where the mechanism is on with the same scenarios with only that mechanism switched off. Counts, not rates: cells are small. Injection: scenarios with injected lines (any tier). Overlap and decoy: ambiguous tier. Gap: missing-evidence tier.

| Mechanism | Investigator | n | Unchanged top-1 | Both correct | Both wrong | Correct only without it | Correct only with it |
|---|---|---|---|---|---|---|---|
| injection | rule_based | 12 | 12/12 | 6 | 6 | 0 | 0 |
| injection | alert_service | 12 | 12/12 | 1 | 11 | 0 | 0 |
| injection | latest_change | 12 | 12/12 | 2 | 10 | 0 | 0 |
| injection | keyword_only | 12 | 12/12 | 5 | 7 | 0 | 0 |
| overlap | rule_based | 10 | 10/10 | 6 | 4 | 0 | 0 |
| overlap | alert_service | 10 | 10/10 | 2 | 8 | 0 | 0 |
| overlap | latest_change | 10 | 10/10 | 1 | 9 | 0 | 0 |
| overlap | keyword_only | 10 | 5/10 | 3 | 2 | 5 | 0 |
| decoy | rule_based | 10 | 8/10 | 6 | 3 | 1 | 0 |
| decoy | alert_service | 10 | 10/10 | 2 | 8 | 0 | 0 |
| decoy | latest_change | 10 | 4/10 | 1 | 7 | 2 | 0 |
| decoy | keyword_only | 10 | 10/10 | 3 | 7 | 0 | 0 |
| gap | rule_based | 10 | 7/10 | 4 | 3 | 3 | 0 |
| gap | alert_service | 10 | 10/10 | 1 | 9 | 0 | 0 |
| gap | latest_change | 10 | 10/10 | 3 | 7 | 0 | 0 |
| gap | keyword_only | 10 | 7/10 | 4 | 3 | 3 | 0 |
