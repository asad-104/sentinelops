# dev results

Generator version 4, data sha256 `6cb926435c2c…`, code `8d3454b`, call budget 200. Cells are k/n (%, Wilson 95% interval). Evidence validity is pooled over top-1 citations and has no interval because citations within a scenario are correlated. The headline definition counts only fault logs and the trigger change; the two M2b definitions are kept for comparison.

## Overall
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 40 | 20/40 (50%, 35–65) | 38/40 (95%, 83–99) | 27/40 (68%, 52–80) | 69/116 (59%) | 69/116 (59%) | 83/116 (72%) |
| alert_service | 40 | 3/40 (8%, 3–20) | 10/40 (25%, 14–40) | 25/40 (62%, 47–76) | 0/40 (0%) | 40/40 (100%) | 40/40 (100%) |
| latest_change | 40 | 8/40 (20%, 10–35) | 15/40 (38%, 24–53) | 15/40 (38%, 24–53) | 8/40 (20%) | 9/40 (22%) | 9/40 (22%) |
| keyword_only | 40 | 19/40 (48%, 33–63) | 31/40 (78%, 62–88) | 27/40 (68%, 52–80) | 69/101 (68%) | 69/101 (68%) | 69/101 (68%) |
| random (analytical, 1/19 pairs) | 40 | 5.3% | 15.8% | 25% | – | – | – |

## Tier: standard
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 20 | 12/20 (60%, 39–78) | 19/20 (95%, 76–99) | 15/20 (75%, 53–89) | 46/65 (71%) | 46/65 (71%) | 56/65 (86%) |
| alert_service | 20 | 2/20 (10%, 3–30) | 4/20 (20%, 8–42) | 12/20 (60%, 39–78) | 0/20 (0%) | 20/20 (100%) | 20/20 (100%) |
| latest_change | 20 | 4/20 (20%, 8–42) | 8/20 (40%, 22–61) | 8/20 (40%, 22–61) | 4/20 (20%) | 4/20 (20%) | 4/20 (20%) |
| keyword_only | 20 | 12/20 (60%, 39–78) | 16/20 (80%, 58–92) | 14/20 (70%, 48–85) | 49/54 (91%) | 49/54 (91%) | 49/54 (91%) |
| random (analytical, 1/19 pairs) | 20 | 5.3% | 15.8% | 25% | – | – | – |

## Tier: ambiguous
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 10 | 6/10 (60%, 31–83) | 10/10 (100%, 72–100) | 9/10 (90%, 60–98) | 18/31 (58%) | 18/31 (58%) | 22/31 (71%) |
| alert_service | 10 | 0/10 (0%, 0–28) | 2/10 (20%, 6–51) | 6/10 (60%, 31–83) | 0/10 (0%) | 10/10 (100%) | 10/10 (100%) |
| latest_change | 10 | 1/10 (10%, 2–40) | 3/10 (30%, 11–60) | 4/10 (40%, 17–69) | 1/10 (10%) | 1/10 (10%) | 1/10 (10%) |
| keyword_only | 10 | 3/10 (30%, 11–60) | 10/10 (100%, 72–100) | 8/10 (80%, 49–94) | 6/22 (27%) | 6/22 (27%) | 6/22 (27%) |
| random (analytical, 1/19 pairs) | 10 | 5.3% | 15.8% | 25% | – | – | – |

## Tier: missing_evidence
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 10 | 2/10 (20%, 6–51) | 9/10 (90%, 60–98) | 3/10 (30%, 11–60) | 5/20 (25%) | 5/20 (25%) | 5/20 (25%) |
| alert_service | 10 | 1/10 (10%, 2–40) | 4/10 (40%, 17–69) | 7/10 (70%, 40–89) | 0/10 (0%) | 10/10 (100%) | 10/10 (100%) |
| latest_change | 10 | 3/10 (30%, 11–60) | 4/10 (40%, 17–69) | 3/10 (30%, 11–60) | 3/10 (30%) | 4/10 (40%) | 4/10 (40%) |
| keyword_only | 10 | 4/10 (40%, 17–69) | 5/10 (50%, 24–76) | 5/10 (50%, 24–76) | 14/25 (56%) | 14/25 (56%) | 14/25 (56%) |
| random (analytical, 1/19 pairs) | 10 | 5.3% | 15.8% | 25% | – | – | – |

## Claims, injection and cost (overall)
| Investigator | Missing evidence named (missing tier) | Unsupported hypotheses | Fabricated citations | Injection cited | Injection followed | Tool calls (mean / max) | Latency ms (median / p95) | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| rule_based | 5/10 (50%, 24–76) | 0/120 | 0 | 0/15 (0%, 0–20) | 2/15 (13%, 4–38) | 52.0 / 52 | 35.5 / 49.9 | 0.00 |
| alert_service | 0/10 (0%, 0–28) | 0/120 | 0 | 0/15 (0%, 0–20) | 1/15 (7%, 1–30) | 1.0 / 1 | 0.0 / 0.0 | 0.00 |
| latest_change | 0/10 (0%, 0–28) | 0/94 | 0 | 0/15 (0%, 0–20) | 0/15 (0%, 0–20) | 4.0 / 4 | 0.2 / 0.2 | 0.00 |
| keyword_only | 0/10 (0%, 0–28) | 0/120 | 0 | 1/15 (7%, 1–30) | 2/15 (13%, 4–38) | 38.0 / 38 | 31.7 / 43.9 | 0.00 |

## Top-1 by fault type (descriptive counts only; cells are too small for claims)
| Investigator | bad_deployment | config_error | connection_pool_exhaustion | memory_leak | certificate_expiry |
|---|---|---|---|---|---|
| rule_based | 5/8 | 3/8 | 5/8 | 7/8 | 0/8 |
| alert_service | 3/8 | 0/8 | 0/8 | 0/8 | 0/8 |
| latest_change | 4/8 | 4/8 | 0/8 | 0/8 | 0/8 |
| keyword_only | 4/8 | 3/8 | 5/8 | 6/8 | 1/8 |
