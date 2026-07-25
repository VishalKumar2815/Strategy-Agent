"""
agent.py
========
StrategyOrchestratorAgent: the single entry point that wires the four tools
together in dependency order and synthesizes the final recommendation.

Dependency order
-----------------
    terrain_tool      (no deps)
    objective_tool     (no deps)          -- can run in parallel with terrain
    resource_tool      (needs terrain)
    route_tool         (needs terrain, resources)

Swap-in point
-------------
Each tool's `run()` is rule-based today. To upgrade a tool to call a real
LLM (Claude / GPT / DeepSeek), replace only that tool's internals - keep the
same input args and the same dict-shaped return value - and this agent
requires no changes.
"""

from typing import Any, Dict

from models import Scenario
from tools.terrain_tool import TerrainAnalysisTool
from tools.objective_tool import ObjectiveAnalysisTool
from tools.resource_tool import ResourceEstimatorTool
from tools.route_tool import RouteEstimatorTool


class StrategyOrchestratorAgent:
    """Orchestrates terrain, objective, resource, and route tools into one
    final AI-generated mission strategy."""

    def __init__(self):
        self.terrain_tool = TerrainAnalysisTool()
        self.objective_tool = ObjectiveAnalysisTool()
        self.resource_tool = ResourceEstimatorTool()
        self.route_tool = RouteEstimatorTool()

    def _synthesize_strategy(self, objective_info: Dict[str, Any],
                              terrain_info: Dict[str, Any],
                              scenario: Scenario) -> Dict[str, Any]:
        """Final reasoning step: combine objective posture + terrain mobility
        into one recommended approach. Rule-based here; swap for an LLM
        reasoning call for richer synthesis if desired."""

        posture = objective_info["posture"]
        mobility = terrain_info["profile"]["mobility"]

        if "restricted" in mobility and scenario.threat_level == "high":
            approach = "Phased, small-unit movement with overwatch; avoid single large formation."
        elif posture.startswith("covert"):
            approach = "Minimal footprint, staggered movement timed to weather/visibility windows."
        elif posture.startswith("logistics"):
            approach = "Prioritize fastest low-risk route; stage backup transport at midpoint."
        else:
            approach = "Standard coordinated movement with escort/perimeter elements per doctrine."

        return {
            "recommended_posture": posture,
            "approach": approach,
            "priority": objective_info["priority"],
        }

    def run(self, scenario: Scenario) -> Dict[str, Any]:
        """Execute the full tool pipeline for a scenario and return the
        final, synthesized strategy answer."""

        # Step 1: independent analyses
        terrain_info = self.terrain_tool.run(scenario=scenario)
        objective_info = self.objective_tool.run(scenario=scenario)

        # Step 2: dependent estimates
        resource_info = self.resource_tool.run(scenario=scenario, terrain_info=terrain_info)
        route_info = self.route_tool.run(
            scenario=scenario, terrain_info=terrain_info, resource_info=resource_info
        )

        # Step 3: synthesis
        strategy = self._synthesize_strategy(objective_info, terrain_info, scenario)

        return {
            "scenario": scenario.name,
            "1_engagement_strategy": strategy,
            "2_resource_requirements": resource_info,
            "3_route_plan": route_info,
            "success_criteria": objective_info["success_criteria"],
            "constraints_considered": scenario.special_constraints,
        }
