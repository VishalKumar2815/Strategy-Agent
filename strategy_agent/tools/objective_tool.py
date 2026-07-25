"""
objective_tool.py
==================
ObjectiveAnalysisTool: classifies the mission type into a posture, priority,
and set of success criteria. Independent of terrain - can run in parallel
with TerrainAnalysisTool.
"""

from typing import Any, Dict

from models import Scenario
from tools.base import BaseTool


class ObjectiveAnalysisTool(BaseTool):
    name = "objective_analysis"

    LIBRARY = {
        "secure_area": {
            "posture": "defensive/dominance",
            "priority": "control",
            "success_criteria": [
                "area cleared", "perimeter held", "no unauthorized access for duration",
            ],
        },
        "escort": {
            "posture": "protective/mobile",
            "priority": "continuity of movement",
            "success_criteria": [
                "asset reaches destination intact", "no unplanned stops", "on schedule",
            ],
        },
        "recon": {
            "posture": "covert/observational",
            "priority": "stealth",
            "success_criteria": [
                "information gathered", "own presence undetected", "team returns safely",
            ],
        },
        "relief_delivery": {
            "posture": "logistics/humanitarian",
            "priority": "speed and reliability",
            "success_criteria": [
                "supplies delivered on time", "safe access route maintained", "no loss of cargo",
            ],
        },
    }

    def run(self, scenario: Scenario, **kwargs) -> Dict[str, Any]:
        spec = self.LIBRARY.get(scenario.objective, {
            "posture": "undefined", "priority": "undefined", "success_criteria": [],
        })
        return {
            "objective": scenario.objective,
            "posture": spec["posture"],
            "priority": spec["priority"],
            "success_criteria": spec["success_criteria"],
            "time_limit_hours": scenario.time_limit_hours,
        }
