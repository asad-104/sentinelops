"""Floors: deliberately naive investigators that every real approach must beat."""

from __future__ import annotations

from sentinelops.baselines._common import context
from sentinelops.models import ConfigChange, FaultType
from sentinelops.report import Hypothesis, InvestigationReport, ToolCaller

ALPHABETICAL_FAULTS = sorted(FaultType, key=lambda f: f.value)


def _report(name: str, scenario_id: str, hypotheses: list[Hypothesis], summary: str) -> InvestigationReport:
    return InvestigationReport(scenario_id=scenario_id, investigator=name, summary=summary,
                               hypotheses=tuple(hypotheses), uncertainty="Floor heuristic; no evidence weighing.",
                               tool_calls=0, duration_s=0.0, stop_reason="no_new_evidence")


class AlertServiceFloor:
    """Blame the alerting service, with fault types in alphabetical order."""

    name = "alert_service"

    def investigate(self, tools: ToolCaller, scenario_id: str) -> InvestigationReport:
        alert = tools.call("get_alert").items[0]
        hypotheses = [Hypothesis(rank=i + 1, service=alert.service, fault_type=fault, confidence="low",
                                 supporting_evidence=(alert.source_id,), rationale="the alerting service")
                      for i, fault in enumerate(ALPHABETICAL_FAULTS[:3])]
        return _report(self.name, scenario_id, hypotheses, f"Blame {alert.service.value}, the alerting service.")


class LatestChangeFloor:
    """Blame the most recent deployments or config changes before the alert, newest first."""

    name = "latest_change"

    def investigate(self, tools: ToolCaller, scenario_id: str) -> InvestigationReport:
        ctx = context(tools)
        window = {"start": ctx.window_start.isoformat(), "end": ctx.alert.timestamp.isoformat(), "limit": 100}
        changes = [*tools.call("list_deployments", window).items, *tools.call("list_config_changes", window).items]
        hypotheses: list[Hypothesis] = []
        for change in sorted(changes, key=lambda c: c.timestamp, reverse=True):
            fault = FaultType.CONFIG_ERROR if isinstance(change, ConfigChange) else FaultType.BAD_DEPLOYMENT
            if any((h.service, h.fault_type) == (change.service, fault) for h in hypotheses):
                continue
            hypotheses.append(Hypothesis(rank=len(hypotheses) + 1, service=change.service, fault_type=fault,
                                         confidence="low", supporting_evidence=(change.source_id,),
                                         rationale=f"most recent change {change.source_id} before the alert"))
            if len(hypotheses) == 3:
                break
        if not hypotheses:
            hypotheses = [Hypothesis(rank=1, service=ctx.alert.service, fault_type=FaultType.BAD_DEPLOYMENT,
                                     confidence="low", supporting_evidence=(ctx.alert.source_id,),
                                     rationale="no change before the alert; defaulting to the alerting service")]
        return _report(self.name, scenario_id, hypotheses, "Blame the most recent change before the alert.")
