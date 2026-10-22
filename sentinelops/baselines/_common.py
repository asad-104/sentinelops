"""Shared helpers for baselines. Everything goes through ``ToolCaller.call``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sentinelops.models import Alert, FaultType, Service
from sentinelops.report import Confidence, Hypothesis, ToolCaller
from sentinelops.baselines.signatures import (
    HIGH_CONFIDENCE_MARGIN,
    HIGH_CONFIDENCE_SCORE,
    KEYWORDS,
    LOOKBACK,
    MEDIUM_CONFIDENCE_SCORE,
    TOP_K,
    CITATIONS_PER_KEYWORD,
)

SERVICE_ORDER = list(Service)
FAULT_ORDER = list(FaultType)


@dataclass(frozen=True)
class Context:
    alert: Alert
    window_start: datetime
    lookback_start: datetime


def context(tools: ToolCaller) -> Context:
    alert = tools.call("get_alert").items[0]
    # Tools do not expose the window; every service reports a metric point at minute 0.
    first = tools.call("get_metrics", {"service": Service.GATEWAY.value, "metric": "error_rate", "limit": 1})
    window_start = first.items[0].timestamp if first.ok and first.items else alert.timestamp - LOOKBACK
    return Context(alert, window_start, max(window_start, alert.timestamp - LOOKBACK))


def keyword_hits(tools: ToolCaller, ctx: Context) -> dict[tuple[Service, str], tuple[int, list[str]]]:
    """(service, keyword) -> (total matches since lookback start, first citation IDs)."""
    hits = {}
    for service in SERVICE_ORDER:
        for keyword in dict.fromkeys(k for ks in KEYWORDS.values() for k in ks):
            result = tools.call("search_logs", {"service": service.value, "contains": keyword,
                                                "start": ctx.lookback_start.isoformat(),
                                                "limit": CITATIONS_PER_KEYWORD})
            hits[(service, keyword)] = (result.total_matches, [r.source_id for r in result.items]) if result.ok else (0, [])
    return hits


def confidence(score: float, next_score: float | None, is_top: bool) -> Confidence:
    if is_top and score >= HIGH_CONFIDENCE_SCORE and (next_score is None or score - next_score >= HIGH_CONFIDENCE_MARGIN):
        return "high"
    return "medium" if score >= MEDIUM_CONFIDENCE_SCORE else "low"


def rank(scored: dict[tuple[Service, FaultType], tuple[float, list[str], str]]) -> list[Hypothesis]:
    """Top-K hypotheses from {(service, fault): (score, evidence, rationale)}, deterministic tie-breaks."""
    ordered = sorted(scored.items(), key=lambda kv: (-kv[1][0], SERVICE_ORDER.index(kv[0][0]),
                                                     FAULT_ORDER.index(kv[0][1])))[:TOP_K]
    hypotheses = []
    for i, ((service, fault), (score, evidence, rationale)) in enumerate(ordered):
        next_score = ordered[i + 1][1][0] if i + 1 < len(ordered) else None
        hypotheses.append(Hypothesis(rank=i + 1, service=service, fault_type=fault,
                                     confidence=confidence(score, next_score, i == 0),
                                     supporting_evidence=tuple(dict.fromkeys(evidence)), rationale=rationale))
    return hypotheses
