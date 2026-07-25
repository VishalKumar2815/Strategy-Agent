"""
resource_tool.py
=================
ResourceEstimatorTool: estimates required assets. Depends on TerrainAnalysisTool
output, so the orchestrator must call terrain analysis first.
"""

from typing import Any, Dict

from strategy_agent.models import Scenario
from strategy_agent.tools.base import BaseTool


class ResourceEstimatorTool(BaseTool):
    name = "resource_estimation"

    # objective -> {resource: units per 10 personnel}
    BASE_RATIOS = {
        "secure_area": {"vehicles": 2, "comms_units": 3, "medical_kits": 2, "drones": 1},
        "escort": {"vehicles": 4, "comms_units": 3, "medical_kits": 2, "drones": 1},
        "recon": {"vehicles": 1, "comms_units": 4, "medical_kits": 1, "drones": 2},
        "relief_delivery": {"vehicles": 3, "comms_units": 2, "medical_kits": 4, "cargo_units": 3},
    }

    TERRAIN_MODIFIERS = {
        "urban": {"vehicles": 0.75, "drones": 1.25},
        "desert": {"vehicles": 1.25, "fuel_reserves": 2.0},
        "mountain": {"vehicles": 0.4, "comms_units": 1.5},
        "riverine": {"vehicles": 0.3, "boats": 1.0},
    }

    def run(self, scenario: Scenario, terrain_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        base = self.BASE_RATIOS.get(scenario.objective, {})
        scale = scenario.force_size / 10.0
        resources = {k: round(v * scale, 1) for k, v in base.items()}

        mods = self.TERRAIN_MODIFIERS.get(scenario.terrain, {})
        for key, factor in mods.items():
            if key in resources:
                resources[key] = round(resources[key] * factor, 1)
            else:
                resources[key] = round(1 * scale * factor, 1)  # terrain-specific addition

        if scenario.threat_level == "high":
            resources["medical_kits"] = round(resources.get("medical_kits", 0) * 1.5, 1)
            resources["reserve_force"] = round(scenario.force_size * 0.2, 1)

        return {
            "personnel": scenario.force_size,
            "estimated_resources": resources,
            "resupply_needed": scenario.time_limit_hours > 10 or scenario.terrain == "desert",
        }
