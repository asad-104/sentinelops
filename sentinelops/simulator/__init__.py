"""Seeded incident simulator. Owns ground truth; never imported by tools."""

from sentinelops.simulator.faults import FaultType
from sentinelops.simulator.generator import Scenario, generate_dataset, generate_scenario
from sentinelops.simulator.ground_truth import GroundTruth

__all__ = ["FaultType", "GroundTruth", "Scenario", "generate_dataset", "generate_scenario"]
