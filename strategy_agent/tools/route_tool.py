"""
route_tool.py
==============
RouteEstimatorTool: generates candidate routes with a composite risk/time
score. Depends on both TerrainAnalysisTool and ResourceEstimatorTool output,
so it runs last in the pipeline.
"""

from typing import Any, Dict

from models import Scenario
from tools.base import BaseTool


class RouteEstimatorTool(BaseTool):
    name = "route_estimation"

    def _score_route(self, scenario: Scenario, terrain_info: Dict[str, Any],
                      base_risk: float, speed_factor: float) -> Dict[str, Any]:
        risk = base_risk
        if terrain_info["reduced_visibility"]:
            risk += 0.15
        if scenario.threat_level == "high":
            risk += 0.2
        elif scenario.threat_level == "medium":
            risk += 0.1
        risk = min(round(risk, 2), 1.0)

        est_time = round(scenario.time_limit_hours * (1 / speed_factor) * 0.6, 1)
        return {
            "risk_score": risk,
            "est_time_hours": est_time,
            "hazards": terrain_info["profile"].get("key_hazards", []),
        }

    def run(self, scenario: Scenario, terrain_info: Dict[str, Any],
            resource_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:

        vehicle_access = terrain_info["profile"].get("vehicle_access", "unknown")

        routes = {
            "primary_route": {
                "description": f"Most direct path suited to {vehicle_access} access.",
                **self._score_route(scenario, terrain_info, base_risk=0.35, speed_factor=1.0),
            },
            "alternate_route": {
                "description": "Longer, lower-exposure path avoiding known choke points/hazards.",
                **self._score_route(scenario, terrain_info, base_risk=0.2, speed_factor=0.7),
            },
        }

        if scenario.terrain == "mountain":
            routes["dismounted_route"] = {
                "description": "Foot-only path for sections above vehicle-access limit.",
                **self._score_route(scenario, terrain_info, base_risk=0.25, speed_factor=0.4),
            }
        if scenario.terrain == "riverine":
            routes["waterway_route"] = {
                "description": "Boat-based route bypassing damaged bridge infrastructure.",
                **self._score_route(scenario, terrain_info, base_risk=0.3, speed_factor=0.8),
            }

        recommended = min(routes.items(), key=lambda kv: kv[1]["risk_score"])

        return {
            "candidate_routes": routes,
            "recommended_route": recommended[0],
            "reasoning": (
                f"'{recommended[0]}' has the lowest composite risk score "
                f"({recommended[1]['risk_score']}) given current threat level and visibility."
            ),
        }
