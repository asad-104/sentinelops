# dev results

Generator version 3, data sha256 `9b2c17e94299…`, code `015e654`, call budget 200. Cells are k/n (%, Wilson 95% interval). Evidence validity is pooled over top-1 citations and has no interval because citations within a scenario are correlated.

## Overall
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (lenient) | Evidence (strict) |
|---|---|---|---|---|---|---|
| rule_based | 40 | 34/40 (85%, 71–93) | 40/40 (100%, 91–100) | 37/40 (92%, 80–97) | 114/131 (87%) | 98/131 (75%) |
| alert_service | 40 | 4/40 (10%, 4–23) | 12/40 (30%, 18–45) | 23/40 (58%, 42–71) | 40/40 (100%) | 40/40 (100%) |
| latest_change | 40 | 12/40 (30%, 18–45) | 16/40 (40%, 26–55) | 20/40 (50%, 35–65) | 14/40 (35%) | 14/40 (35%) |
| keyword_only | 40 | 33/40 (82%, 68–91) | 37/40 (92%, 80–97) | 34/40 (85%, 71–93) | 88/108 (81%) | 88/108 (81%) |
| random (analytical, 1/19 pairs) | 40 | 5.3% | 15.8% | 25% | – | – |

## Tier: standard
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (lenient) | Evidence (strict) |
|---|---|---|---|---|---|---|
| rule_based | 20 | 17/20 (85%, 64–95) | 20/20 (100%, 84–100) | 19/20 (95%, 76–99) | 54/63 (86%) | 46/63 (73%) |
| alert_service | 20 | 2/20 (10%, 3–30) | 6/20 (30%, 15–52) | 12/20 (60%, 39–78) | 20/20 (100%) | 20/20 (100%) |
| latest_change | 20 | 7/20 (35%, 18–57) | 8/20 (40%, 22–61) | 10/20 (50%, 30–70) | 7/20 (35%) | 7/20 (35%) |
| keyword_only | 20 | 16/20 (80%, 58–92) | 18/20 (90%, 70–97) | 17/20 (85%, 64–95) | 42/53 (79%) | 42/53 (79%) |
| random (analytical, 1/19 pairs) | 20 | 5.3% | 15.8% | 25% | – | – |

## Tier: ambiguous
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (lenient) | Evidence (strict) |
|---|---|---|---|---|---|---|
| rule_based | 10 | 8/10 (80%, 49–94) | 10/10 (100%, 72–100) | 9/10 (90%, 60–98) | 29/34 (85%) | 25/34 (74%) |
| alert_service | 10 | 0/10 (0%, 0–28) | 1/10 (10%, 2–40) | 3/10 (30%, 11–60) | 10/10 (100%) | 10/10 (100%) |
| latest_change | 10 | 1/10 (10%, 2–40) | 4/10 (40%, 17–69) | 4/10 (40%, 17–69) | 1/10 (10%) | 1/10 (10%) |
| keyword_only | 10 | 9/10 (90%, 60–98) | 10/10 (100%, 72–100) | 9/10 (90%, 60–98) | 23/27 (85%) | 23/27 (85%) |
| random (analytical, 1/19 pairs) | 10 | 5.3% | 15.8% | 25% | – | – |

## Tier: missing_evidence
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (lenient) | Evidence (strict) |
|---|---|---|---|---|---|---|
| rule_based | 10 | 9/10 (90%, 60–98) | 10/10 (100%, 72–100) | 9/10 (90%, 60–98) | 31/34 (91%) | 27/34 (79%) |
| alert_service | 10 | 2/10 (20%, 6–51) | 5/10 (50%, 24–76) | 8/10 (80%, 49–94) | 10/10 (100%) | 10/10 (100%) |
| latest_change | 10 | 4/10 (40%, 17–69) | 4/10 (40%, 17–69) | 6/10 (60%, 31–83) | 6/10 (60%) | 6/10 (60%) |
| keyword_only | 10 | 8/10 (80%, 49–94) | 9/10 (90%, 60–98) | 8/10 (80%, 49–94) | 23/28 (82%) | 23/28 (82%) |
| random (analytical, 1/19 pairs) | 10 | 5.3% | 15.8% | 25% | – | – |

## Claims, injection and cost (overall)
| Investigator | Unsupported hypotheses | Fabricated citations | Injection cited | Injection followed | Tool calls (mean / max) | Latency ms (median / p95) | Cost (USD) |
|---|---|---|---|---|---|---|---|
| rule_based | 0/120 | 0 | 1/11 (9%, 2–38) | 0/11 (0%, 0–26) | 52.0 / 52 | 34.4 / 50.4 | 0.00 |
| alert_service | 0/120 | 0 | 0/11 (0%, 0–26) | 0/11 (0%, 0–26) | 1.0 / 1 | 0.0 / 0.0 | 0.00 |
| latest_change | 0/84 | 0 | 0/11 (0%, 0–26) | 0/11 (0%, 0–26) | 4.0 / 4 | 0.2 / 0.2 | 0.00 |
| keyword_only | 0/120 | 0 | 1/11 (9%, 2–38) | 0/11 (0%, 0–26) | 38.0 / 38 | 32.1 / 46.2 | 0.00 |

## Top-1 by fault type (descriptive counts only; cells are too small for claims)
| Investigator | bad_deployment | config_error | connection_pool_exhaustion | memory_leak | certificate_expiry |
|---|---|---|---|---|---|
| rule_based | 8/8 | 8/8 | 8/8 | 8/8 | 2/8 |
| alert_service | 4/8 | 0/8 | 0/8 | 0/8 | 0/8 |
| latest_change | 5/8 | 7/8 | 0/8 | 0/8 | 0/8 |
| keyword_only | 5/8 | 8/8 | 8/8 | 8/8 | 4/8 |
