# dev results

Generator version 5, data sha256 `5a35c45a7e8f…`, code `e8c9279`, call budget 200. Cells are k/n (%, Wilson 95% interval). Evidence validity is pooled over top-1 citations and has no interval because citations within a scenario are correlated. The headline definition counts only fault logs and the trigger change; the two M2b definitions are kept for comparison. Injection influence is paired: each scenario with injected lines is rerun as its twin without them, and a change of top-1 between the two is counted (tool calls and latency exclude twin runs).

## Overall
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 40 | 25/40 (62%, 47–76) | 37/40 (92%, 80–97) | 28/40 (70%, 55–82) | 66/119 (55%) | 66/119 (55%) | 80/119 (67%) |
| alert_service | 40 | 5/40 (12%, 5–26) | 12/40 (30%, 18–45) | 22/40 (55%, 40–69) | 0/40 (0%) | 40/40 (100%) | 40/40 (100%) |
| latest_change | 40 | 10/40 (25%, 14–40) | 16/40 (40%, 26–55) | 20/40 (50%, 35–65) | 10/40 (25%) | 10/40 (25%) | 10/40 (25%) |
| keyword_only | 40 | 21/40 (52%, 37–67) | 32/40 (80%, 65–90) | 28/40 (70%, 55–82) | 63/101 (62%) | 63/101 (62%) | 63/101 (62%) |
| random (analytical, 1/19 pairs) | 40 | 5.3% | 15.8% | 25% | – | – | – |

## Tier: standard
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 20 | 15/20 (75%, 53–89) | 18/20 (90%, 70–97) | 15/20 (75%, 53–89) | 39/62 (63%) | 39/62 (63%) | 47/62 (76%) |
| alert_service | 20 | 2/20 (10%, 3–30) | 5/20 (25%, 11–47) | 10/20 (50%, 30–70) | 0/20 (0%) | 20/20 (100%) | 20/20 (100%) |
| latest_change | 20 | 6/20 (30%, 15–52) | 8/20 (40%, 22–61) | 9/20 (45%, 26–66) | 6/20 (30%) | 6/20 (30%) | 6/20 (30%) |
| keyword_only | 20 | 14/20 (70%, 48–85) | 18/20 (90%, 70–97) | 14/20 (70%, 48–85) | 41/50 (82%) | 41/50 (82%) | 41/50 (82%) |
| random (analytical, 1/19 pairs) | 20 | 5.3% | 15.8% | 25% | – | – | – |

## Tier: ambiguous
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 10 | 6/10 (60%, 31–83) | 9/10 (90%, 60–98) | 9/10 (90%, 60–98) | 16/35 (46%) | 16/35 (46%) | 21/35 (60%) |
| alert_service | 10 | 2/10 (20%, 6–51) | 5/10 (50%, 24–76) | 8/10 (80%, 49–94) | 0/10 (0%) | 10/10 (100%) | 10/10 (100%) |
| latest_change | 10 | 1/10 (10%, 2–40) | 4/10 (40%, 17–69) | 6/10 (60%, 31–83) | 1/10 (10%) | 1/10 (10%) | 1/10 (10%) |
| keyword_only | 10 | 3/10 (30%, 11–60) | 8/10 (80%, 49–94) | 10/10 (100%, 72–100) | 8/28 (29%) | 8/28 (29%) | 8/28 (29%) |
| random (analytical, 1/19 pairs) | 10 | 5.3% | 15.8% | 25% | – | – | – |

## Tier: missing_evidence
| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) | Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |
|---|---|---|---|---|---|---|---|
| rule_based | 10 | 4/10 (40%, 17–69) | 10/10 (100%, 72–100) | 4/10 (40%, 17–69) | 11/22 (50%) | 11/22 (50%) | 12/22 (55%) |
| alert_service | 10 | 1/10 (10%, 2–40) | 2/10 (20%, 6–51) | 4/10 (40%, 17–69) | 0/10 (0%) | 10/10 (100%) | 10/10 (100%) |
| latest_change | 10 | 3/10 (30%, 11–60) | 4/10 (40%, 17–69) | 5/10 (50%, 24–76) | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) |
| keyword_only | 10 | 4/10 (40%, 17–69) | 6/10 (60%, 31–83) | 4/10 (40%, 17–69) | 14/23 (61%) | 14/23 (61%) | 14/23 (61%) |
| random (analytical, 1/19 pairs) | 10 | 5.3% | 15.8% | 25% | – | – | – |

## Claims, injection and cost (overall)
| Investigator | Missing evidence named (missing tier) | Unsupported hypotheses | Fabricated citations | Injection cited | Injection changed answer (paired) | Changed to claimed | Tool calls (mean / max) | Latency ms (median / p95) | Cost (USD) |
|---|---|---|---|---|---|---|---|---|---|
| rule_based | 5/10 (50%, 24–76) | 0/120 | 0 | 2/12 (17%, 5–45) | 0/12 (0%, 0–24) | 0/12 (0%, 0–24) | 52.0 / 52 | 36.4 / 50.2 | 0.00 |
| alert_service | 0/10 (0%, 0–28) | 0/120 | 0 | 0/12 (0%, 0–24) | 0/12 (0%, 0–24) | 0/12 (0%, 0–24) | 1.0 / 1 | 0.0 / 0.0 | 0.00 |
| latest_change | 0/10 (0%, 0–28) | 0/102 | 0 | 0/12 (0%, 0–24) | 0/12 (0%, 0–24) | 0/12 (0%, 0–24) | 4.0 / 4 | 0.2 / 0.2 | 0.00 |
| keyword_only | 0/10 (0%, 0–28) | 0/120 | 0 | 3/12 (25%, 9–53) | 0/12 (0%, 0–24) | 0/12 (0%, 0–24) | 38.0 / 38 | 30.8 / 44.9 | 0.00 |

## Top-1 by fault type (descriptive counts only; cells are too small for claims)
| Investigator | bad_deployment | config_error | connection_pool_exhaustion | memory_leak | certificate_expiry |
|---|---|---|---|---|---|
| rule_based | 5/8 | 7/8 | 7/8 | 6/8 | 0/8 |
| alert_service | 5/8 | 0/8 | 0/8 | 0/8 | 0/8 |
| latest_change | 5/8 | 5/8 | 0/8 | 0/8 | 0/8 |
| keyword_only | 4/8 | 7/8 | 5/8 | 5/8 | 0/8 |
