"""Rule-based baseline and floors. Investigator-side: must not import sentinelops.simulator."""

from sentinelops.baselines.floors import AlertServiceFloor, LatestChangeFloor
from sentinelops.baselines.rule_based import RuleBasedInvestigator, keyword_only
from sentinelops.report import Investigator

# The random floor is analytical (see evaluation.metrics.RANDOM_FLOOR), not an investigator.
INVESTIGATORS: dict[str, Investigator] = {
    "rule_based": RuleBasedInvestigator(),
    "alert_service": AlertServiceFloor(),
    "latest_change": LatestChangeFloor(),
    "keyword_only": keyword_only(),
}

__all__ = ["INVESTIGATORS", "AlertServiceFloor", "LatestChangeFloor", "RuleBasedInvestigator", "keyword_only"]
