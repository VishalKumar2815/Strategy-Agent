"""
terrain_tool.py
================
TerrainAnalysisTool: assesses terrain-driven mobility, cover, visibility,
and hazards for a given scenario. This is the first tool the agent calls,
since resource and route estimates both depend on its output.
"""

from typing import Any, Dict

from strategy_agent.models import Scenario
from strategy_agent.tools.base import BaseTool


class TerrainAnalysisTool(BaseTool):
    name = "terrain_analysis"

    PROFILES = {
        "urban": {
            "mobility": "restricted", "cover": "high", "visibility": "low",
            "vehicle_access": "partial",
            "key_hazards": ["choke points", "civilian presence"],
        },
        "desert": {
            "mobility": "open", "cover": "low", "visibility": "high",
            "vehicle_access": "full",
            "key_hazards": ["heat", "sandstorms", "long resupply lines"],
        },
        "mountain": {
            "mobility": "very restricted", "cover": "medium", "visibility": "variable",
            "vehicle_access": "limited",
            "key_hazards": ["altitude", "weather shifts", "narrow trails"],
        },
        "riverine": {
            "mobility": "channelized", "cover": "medium", "visibility": "medium",
            "vehicle_access": "boat/amphibious only",
            "key_hazards": ["flooding", "bridge damage", "currents"],
        },
    }

    def run(self, scenario: Scenario, **kwargs) -> Dict[str, Any]:
        profile = self.PROFILES.get(scenario.terrain, {
            "mobility": "unknown", "cover": "unknown", "visibility": "unknown",
            "vehicle_access": "unknown", "key_hazards": [],
        })
        weather_penalty = scenario.weather in ("storm", "fog", "night")

        return {
            "terrain": scenario.terrain,
            "weather": scenario.weather,
            "profile": profile,
            "reduced_visibility": weather_penalty,
            "notes": (
                f"{scenario.terrain.title()} terrain under {scenario.weather} conditions "
                f"{'compounds' if weather_penalty else 'does not significantly affect'} mobility risk."
            ),
        }
