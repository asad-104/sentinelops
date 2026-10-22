"""Rule-based baseline v1 (see docs/PROGRESS.md, "Baseline specification v1").

With ``use_metrics`` and ``use_changes`` off it is the ``keyword_only`` floor.
Injection lines are not special-cased: they count like any other log line.
"""

from __future__ import annotations

from sentinelops.baselines._common import FAULT_ORDER, SERVICE_ORDER, Context, context, keyword_hits, rank
from sentinelops.baselines.signatures import (
    CONFIG_KEY_KEYWORD,
    KEYWORDS,
    LOG_SATURATION,
    MEMORY_THRESHOLD,
    MISSING_WINDOW,
    POOL_THRESHOLD,
    SUFFICIENT_EVIDENCE_SCORE,
)
from sentinelops.models import FaultType, Metric, Service
from sentinelops.report import Hypothesis, InvestigationReport, ToolCaller

METRIC_SIGNALS = (
    (Metric.DB_POOL_UTILIZATION, POOL_THRESHOLD, FaultType.CONNECTION_POOL_EXHAUSTION),
    (Metric.MEMORY_PCT, MEMORY_THRESHOLD, FaultType.MEMORY_LEAK),
)

NEXT_CHECKS: dict[FaultType, str] = {
    FaultType.BAD_DEPLOYMENT: "Compare error rates and exceptions before and after the most recent deployment on {s}.",
    FaultType.CONFIG_ERROR: "Diff the recent configuration change on {s} against its previous value.",
    FaultType.CONNECTION_POOL_EXHAUSTION: "Check {s}'s pool utilization and long-running queries; confirm the pool size is unchanged.",
    FaultType.MEMORY_LEAK: "Check {s}'s memory trend and restart history for a sawtooth pattern.",
    FaultType.CERTIFICATE_EXPIRY: "Check the validity dates of the certificate served by {s}.",
}
REMEDIATION: dict[FaultType, str] = {
    FaultType.BAD_DEPLOYMENT: "Consider rolling back the latest deployment on {s} (requires human approval).",
    FaultType.CONFIG_ERROR: "Consider reverting the latest configuration change on {s} (requires human approval).",
    FaultType.CONNECTION_POOL_EXHAUSTION: "Consider recycling {s}'s connections and killing long-running queries (requires human approval).",
    FaultType.MEMORY_LEAK: "Consider a controlled restart of {s} and capturing a heap dump (requires human approval).",
    FaultType.CERTIFICATE_EXPIRY: "Consider renewing and redeploying {s}'s certificate (requires human approval).",
}


class RuleBasedInvestigator:
    def __init__(self, name: str = "rule_based", use_metrics: bool = True, use_changes: bool = True,
                 detect_missing: bool = True) -> None:
        self.name = name
        self.use_metrics = use_metrics
        self.use_changes = use_changes
        self.detect_missing = detect_missing

    def investigate(self, tools: ToolCaller, scenario_id: str) -> InvestigationReport:
        ctx = context(tools)
        hits = keyword_hits(tools, ctx)
        metric_hits = self._metric_hits(tools, ctx) if self.use_metrics else {}
        deployments, configs = self._changes(tools, ctx) if self.use_changes else ([], [])

        scored: dict[tuple[Service, FaultType], tuple[float, list[str], str]] = {}
        for service in SERVICE_ORDER:
            for fault in FAULT_ORDER:
                count = sum(hits[(service, k)][0] for k in KEYWORDS[fault])
                score = min(count, LOG_SATURATION) / LOG_SATURATION
                evidence = [i for k in KEYWORDS[fault] for i in hits[(service, k)][1]]
                reasons = [f"{count} keyword matches"] if count else []
                if (service, fault) in metric_hits:
                    score += 1
                    evidence.append(metric_hits[(service, fault)])
                    reasons.append("metric threshold breached")
                if fault is FaultType.BAD_DEPLOYMENT:
                    deploy = next((d for d in reversed(deployments) if d.service is service), None)
                    if deploy is not None:
                        score += 1
                        evidence.append(deploy.source_id)
                        reasons.append(f"deployment {deploy.source_id} before the alert")
                if fault is FaultType.CONFIG_ERROR:
                    change = next((c for c in reversed(configs) if c.service is service
                                   and hits.get((service, CONFIG_KEY_KEYWORD.get(c.key, "")), (0, []))[0] > 0), None)
                    if change is not None:
                        score += 1
                        evidence.append(change.source_id)
                        reasons.append(f"config change {change.source_id} ({change.key}) matches a symptom")
                if score > 0:
                    scored[(service, fault)] = (score, evidence, "; ".join(reasons))

        missing = self._missing(tools, ctx) if self.detect_missing else []
        if scored:
            hypotheses = rank(scored)
            top_score = scored[(hypotheses[0].service, hypotheses[0].fault_type)][0]
        else:
            hypotheses = [Hypothesis(rank=1, service=ctx.alert.service, fault_type=FaultType.BAD_DEPLOYMENT,
                                     confidence="low", supporting_evidence=(ctx.alert.source_id,),
                                     rationale="no signature evidence; defaulting to the alerting service")]
            top_score = 0.0
        top = hypotheses[0]
        uncertainty = (f"Top score {top_score:.2f}" + (f" vs {scored[(hypotheses[1].service, hypotheses[1].fault_type)][0]:.2f} "
                       f"for the runner-up" if len(hypotheses) > 1 else "") + ". Scores are rule weights, not probabilities.")
        if missing:
            uncertainty += " Some evidence appears to be missing."
        return InvestigationReport(
            scenario_id=scenario_id,
            investigator=self.name,
            summary=f"Most likely {top.fault_type.value} on {top.service.value}.",
            affected_services=tuple(dict.fromkeys(h.service for h in hypotheses)),
            hypotheses=tuple(hypotheses),
            missing_evidence=tuple(missing),
            uncertainty=uncertainty,
            next_checks=tuple(NEXT_CHECKS[h.fault_type].format(s=h.service.value) for h in hypotheses),
            recommended_remediation=(REMEDIATION[top.fault_type].format(s=top.service.value),),
            tool_calls=0,  # measured by the harness
            duration_s=0.0,
            stop_reason="sufficient_evidence" if top_score >= SUFFICIENT_EVIDENCE_SCORE else "no_new_evidence",
        )

    @staticmethod
    def _metric_hits(tools: ToolCaller, ctx: Context) -> dict[tuple[Service, FaultType], str]:
        found = {}
        for service in SERVICE_ORDER:
            for metric, threshold, fault in METRIC_SIGNALS:
                result = tools.call("get_metrics", {"service": service.value, "metric": metric.value,
                                                    "start": ctx.lookback_start.isoformat(), "limit": 500})
                if result.ok and result.items:
                    peak = max(result.items, key=lambda p: p.value)
                    if peak.value > threshold:
                        found[(service, fault)] = peak.source_id
        return found

    @staticmethod
    def _changes(tools: ToolCaller, ctx: Context) -> tuple[list, list]:
        window = {"start": ctx.lookback_start.isoformat(), "end": ctx.alert.timestamp.isoformat(), "limit": 100}
        deployments = tools.call("list_deployments", window)
        configs = tools.call("list_config_changes", window)
        return (list(deployments.items) if deployments.ok else [], list(configs.items) if configs.ok else [])

    @staticmethod
    def _missing(tools: ToolCaller, ctx: Context) -> list[str]:
        start = max(ctx.window_start, ctx.alert.timestamp - MISSING_WINDOW)
        counts = {}
        for service in SERVICE_ORDER:
            args = {"service": service.value, "start": start.isoformat(),
                    "end": (ctx.alert.timestamp + MISSING_WINDOW).isoformat(), "limit": 1}
            result = tools.call("search_logs", args)
            if not result.ok and result.error is not None and result.error.code == "out_of_window":
                args.pop("end")  # the alert is near the window end
                result = tools.call("search_logs", args)
            counts[service] = result.total_matches if result.ok else 0
        if not any(counts.values()):
            return []
        return [f"No logs from {s.value} within {int(MISSING_WINDOW.total_seconds() // 60)} minutes of the alert "
                f"while other services logged normally." for s, n in counts.items() if n == 0]


def keyword_only() -> RuleBasedInvestigator:
    return RuleBasedInvestigator("keyword_only", use_metrics=False, use_changes=False, detect_missing=False)
