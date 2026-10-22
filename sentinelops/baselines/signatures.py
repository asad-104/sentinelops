"""Rule baseline v1 signatures and thresholds.

These values are pre-registered in docs/PROGRESS.md ("Baseline specification
v1"). Any change must bump BASELINE_VERSION and be recorded in the Baseline
tuning log with a date and reason. Tune on dev data only.
"""

from __future__ import annotations

from datetime import timedelta

from sentinelops.models import FaultType

BASELINE_VERSION = "1"

LOOKBACK = timedelta(minutes=30)
MISSING_WINDOW = timedelta(minutes=5)  # on each side of the alert

KEYWORDS: dict[FaultType, tuple[str, ...]] = {
    FaultType.BAD_DEPLOYMENT: ("exception",),
    FaultType.CONFIG_ERROR: ("timeout", "rate limit", "cache miss"),
    FaultType.CONNECTION_POOL_EXHAUSTION: ("connection",),
    FaultType.MEMORY_LEAK: ("gc pause", "memory"),
    FaultType.CERTIFICATE_EXPIRY: ("certificate", "x509"),
}

# A config change supports config_error only if its symptom keyword was seen on that service.
CONFIG_KEY_KEYWORD: dict[str, str] = {
    "http_client.timeout_ms": "timeout",
    "rate_limit.rps": "rate limit",
    "cache.ttl_seconds": "cache miss",
    "db.pool_max": "connection",
}

POOL_THRESHOLD = 95.0
MEMORY_THRESHOLD = 85.0

LOG_SATURATION = 20  # keyword matches at which log evidence counts fully (score 1.0)
CITATIONS_PER_KEYWORD = 2
TOP_K = 3

HIGH_CONFIDENCE_SCORE = 1.5
HIGH_CONFIDENCE_MARGIN = 0.5
MEDIUM_CONFIDENCE_SCORE = 0.75
SUFFICIENT_EVIDENCE_SCORE = 1.0
