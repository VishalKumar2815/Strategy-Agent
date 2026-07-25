"""
cli.py
======
Free-text entry point. Takes a natural-language mission description,
extracts a Scenario via QueryParserTool, then runs it through
StrategyOrchestratorAgent - no hand-built Scenario required.

Usage:
    python3 -m strategy_agent.cli "Secure an urban area at night with 40 \
personnel, high threat, 12 hour window, minimize civilian disruption"

    or interactively, with no arguments:
    python3 -m strategy_agent.cli
"""

import sys
import json

from agent import StrategyOrchestratorAgent
from tools.query_parser_tool import QueryParserTool


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Describe the mission: ")

    parsed = QueryParserTool().run(query=query)
    scenario = parsed["scenario"]

    print("=" * 80)
    print("EXTRACTED SCENARIO")
    print("=" * 80)
    print(json.dumps({
        "objective": scenario.objective,
        "terrain": scenario.terrain,
        "weather": scenario.weather,
        "force_size": scenario.force_size,
        "time_limit_hours": scenario.time_limit_hours,
        "threat_level": scenario.threat_level,
        "special_constraints": scenario.special_constraints,
    }, indent=2))

    if parsed["assumptions_used_default"]:
        defaulted = ", ".join(parsed["assumptions_used_default"])
        print(f"\nNote: these fields weren't mentioned in the query, defaults were used: {defaulted}")

    agent = StrategyOrchestratorAgent()
    result = agent.run(scenario)

    print("\n" + "=" * 80)
    print("FINAL STRATEGY")
    print("=" * 80)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
