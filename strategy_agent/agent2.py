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

summarize()
-----------
The ONLY method in this file that calls an LLM. It is fed strictly the JSON
that run() already produced - it does not call any tool, does not decide
tool order, and is instructed not to introduce facts beyond that JSON. It
just turns the finished structured result into a natural-language summary.

Requires ANTHROPIC_API_KEY as an environment variable. If it's not set (or
the call fails), falls back to a clearly-labeled plain-text formatting of
the same JSON, so run() + summarize() stay testable without a key.
"""

import os
import json
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from models import Scenario
from tools.terrain_tool import TerrainAnalysisTool
from tools.objective_tool import ObjectiveAnalysisTool
from tools.resource_tool import ResourceEstimatorTool
from tools.route_tool import RouteEstimatorTool
from tools.query_parser_tool import QueryParserTool
from tools.escape_tool import IncidentResponseTool



load_dotenv() 

api_key = os.getenv("GROQ_API_KEY")

SUMMARY_SYSTEM_PROMPT = (
    "You are a mission-planning briefing writer. You will be given a strict "
    "JSON object: an engagement strategy, resource requirements, a route "
    "plan, success criteria, and constraints. Write a clear, professional "
    "natural-language mission briefing based ONLY on the data provided - "
    "never invent facts, numbers, or routes that aren't present in the "
    "JSON. Use short labeled sections: Strategy, Resources, Routes, Success "
    "Criteria, Constraints. Keep it concise (under 300 words)."
)


class StrategyOrchestratorAgent:
    """Orchestrates terrain, objective, resource, and route tools into one
    final mission strategy answer."""


    def __init__(self):
        self.terrain_tool = TerrainAnalysisTool()
        self.objective_tool = ObjectiveAnalysisTool()
        self.resource_tool = ResourceEstimatorTool()
        self.route_tool = RouteEstimatorTool()
        self.incident_tool = IncidentResponseTool()
        

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

    def run(self, query:str,maps: Optional[str] = None) -> Dict[str, Any]:

        """Execute the full tool pipeline for a scenario and return the
        final, synthesized strategy answer as strict JSON. No LLM calls."""

        parsed_query=QueryParserTool().run(query)
        scenario=parsed_query["scenario"]

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

        result ={
            "scenario": scenario.name,
            "1_engagement_strategy": strategy,
            "2_resource_requirements": resource_info,
            "3_route_plan": route_info,
            "success_criteria": objective_info["success_criteria"],
            "constraints_considered": scenario.special_constraints, }
        
        
        return result

    def _escape_response(self, query:str) -> Dict[str, Any]:
        incident_response = self.incident_tool.run(query=query)
        return incident_response
    
    def _fallback_summary(self, result: Dict[str, Any], error: Optional[str] = None) -> str:
        """Plain-text formatting fallback - no LLM, used only when the API
        call can't be made (no key, or the call failed)."""

        header = "[Fallback summary — ANTHROPIC_API_KEY not set or call failed"
        header += f": {error}]" if error else "]"

        strategy = result.get("1_engagement_strategy", {})
        resources = result.get("2_resource_requirements", {})
        routes = result.get("3_route_plan", {})
        success = result.get("success_criteria", [])
        constraints = result.get("constraints_considered", [])

        lines = [
            header, "",
            f"Strategy: {strategy.get('approach', 'N/A')} "
            f"(posture: {strategy.get('recommended_posture', 'N/A')}, "
            f"priority: {strategy.get('priority', 'N/A')})",
            f"Resources: {resources.get('personnel', 0)} personnel; "
            f"{resources.get('estimated_resources', {})}",
            f"Routes: recommended '{routes.get('recommended_route', 'N/A')}' — "
            f"{routes.get('reasoning', '')}",
            f"Success criteria: {', '.join(success) if success else 'none specified'}",
            f"Constraints: {', '.join(constraints) if constraints else 'none specified'}",
        ]
        return "\n".join(lines)

    def summarize(self, result: Dict[str, Any]) -> str:
        """Turn the strict JSON from run() into a natural-language summary
        via an LLM call. This is the only place in the agent that calls an
        LLM - it receives nothing but `result` (the finished JSON) and is
        instructed not to add facts beyond it."""

        model = ChatGroq(model="qwen/qwen3.6-27b",reasoning_format="hidden")
        try:
            messages = [
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(result, indent=2)},
            ]
            response = model.invoke(messages)
            summary = response.content.strip()
            return summary or self._fallback_summary(result)
        except Exception as exc:
            return self._fallback_summary(result, error=str(exc))



# if __name__ == "__main__":
#     agent = StrategyOrchestratorAgent()
#     incident_response = agent._escape_response(query="A building collapse happened.20 people are trapped.Five are critically injured.Ten rescued.")
#     print(incident_response)
