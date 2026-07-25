"""
query_parser_tool.py
=====================
QueryParserTool: turns a free-text mission description into a Scenario
object, so the pipeline can start from "Plan a mission to secure an urban
area at night with 40 personnel..." instead of a hand-built Scenario.

This is rule-based (keyword + regex matching) so it works with zero
external dependencies. Any field not mentioned in the query falls back to
a documented default and is flagged in `assumptions_used_default` so the
caller knows what was guessed.

Swap-in point: replace the body of `run()` with an LLM call that extracts
the same fields as structured JSON (more robust to phrasing variety),
keeping the same return shape - the rest of the pipeline (agent.py,
cli.py) needs no changes.
"""

import re
from typing import Any, Dict, List

from strategy_agent.models import Scenario
from strategy_agent.tools.base import BaseTool


class QueryParserTool(BaseTool):
    name = "query_parser"

    OBJECTIVE_KEYWORDS = {
        "secure_area": ["secure", "clear the area", "hold the area", "dominate", "lockdown","hold","defend"],
        "escort": ["escort", "convoy", "protect the convoy", "accompany"],
        "recon": ["recon", "reconnaissance", "surveil", "observe", "scout", "gather intel"],
        "relief_delivery": ["relief", "deliver aid", "humanitarian", "deliver supplies", "aid delivery"],
    }

    TERRAIN_KEYWORDS = {
        "urban": ["urban", "city", "town", "street", "downtown"],
        "desert": ["desert", "arid", "sand", "dunes"],
        "mountain": ["mountain", "highland", "alpine", "peak", "ridge"],
        "riverine": ["river", "riverine", "flood", "waterway", "swamp", "delta"],
    }

    WEATHER_KEYWORDS = {
        "night": ["night", "dark", "nighttime", "after dusk"],
        "storm": ["storm", "rain", "hurricane", "typhoon", "monsoon"],
        "fog": ["fog", "mist", "low visibility", "haze"],
        "clear": ["clear skies", "sunny", "daylight", "clear weather"],
    }

    THREAT_KEYWORDS = {
        "high": ["high threat", "hostile", "contested", "dangerous", "high risk", "active resistance"],
        "medium": ["medium threat", "moderate threat", "some risk", "moderate risk"],
        "low": ["low threat", "permissive", "safe", "low risk", "uncontested"],
    }

    CONSTRAINT_PATTERNS = [
        "minimize civilian disruption", "limited air support", "fuel resupply",
        "stealth priority", "no vehicle access", "flood-damaged", "time-sensitive",
        "night operations only", "limited visibility", "restricted rules of engagement",
        "no air support", "limited fuel", "medical supplies time-sensitive",
    ]

    DEFAULTS = {
        "objective": "secure_area",
        "terrain": "urban",
        "weather": "clear",
        "force_size": 20,
        "time_limit_hours": 12,
        "threat_level": "medium",
    }

    def _match_keyword(self, text_lower: str, keyword_map: Dict[str, List[str]]) -> str | None:
        for key, phrases in keyword_map.items():
            if any(phrase in text_lower for phrase in phrases):
                return key
        return None

    def _extract_force_size(self, text: str) -> int | None:
        match = re.search(
            r"(\d+)\s*(personnel|troops|soldiers|people|units|team members|responders)",
            text, re.IGNORECASE,
        )
        return int(match.group(1)) if match else None

    def _extract_time_limit(self, text: str) -> int | None:
        hour_match = re.search(r"(\d+)\s*(hours|hour|hrs|hr)\b", text, re.IGNORECASE)
        if hour_match:
            return int(hour_match.group(1))
        day_match = re.search(r"(\d+)\s*(days|day)\b", text, re.IGNORECASE)
        if day_match:
            return int(day_match.group(1)) * 24
        return None

    def _extract_constraints(self, text_lower: str) -> List[str]:
        return [c for c in self.CONSTRAINT_PATTERNS if c in text_lower]

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        text_lower = query

        objective = self._match_keyword(text_lower, self.OBJECTIVE_KEYWORDS)
        terrain = self._match_keyword(text_lower, self.TERRAIN_KEYWORDS)
        weather = self._match_keyword(text_lower, self.WEATHER_KEYWORDS)
        threat_level = self._match_keyword(text_lower, self.THREAT_KEYWORDS)
        force_size = self._extract_force_size(query)
        time_limit_hours = self._extract_time_limit(query)
        constraints = self._extract_constraints(text_lower)

        assumptions_used_default: List[str] = []
        fields = {
            "objective": objective, "terrain": terrain, "weather": weather,
            "threat_level": threat_level, "force_size": force_size,
            "time_limit_hours": time_limit_hours,
        }
        for field_name, value in fields.items():
            if value is None:
                assumptions_used_default.append(field_name)
                fields[field_name] = self.DEFAULTS[field_name]

        scenario = Scenario(
            name=f"User Query - {fields['objective']}/{fields['terrain']}",
            objective=fields["objective"],
            terrain=fields["terrain"],
            weather=fields["weather"],
            force_size=fields["force_size"],
            time_limit_hours=fields["time_limit_hours"],
            threat_level=fields["threat_level"],
            special_constraints=constraints,
        )

        return {
            "scenario": scenario,
            "assumptions_used_default": assumptions_used_default,
            "raw_query": query,
        }
