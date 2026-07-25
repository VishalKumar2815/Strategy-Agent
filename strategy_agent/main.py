"""
main.py
=======
Entry point: runs the StrategyOrchestratorAgent against every scenario in
test_cases.py and prints the final AI-generated strategy answer as JSON.

Usage:
    python3 -m strategy_agent.main
"""




'''
from strategy_agent.agent import StrategyOrchestratorAgent
from strategy_agent.tools.query_parser_tool import QueryParserTool

# Step 0 — free text → Scenario (rule-based extraction, not LLM)
parsed = QueryParserTool().run(query="Secure an urban area at night with 40 personnel, high threat")
scenario = parsed["scenario"]          # a Scenario object
# parsed["assumptions_used_default"]   # fields that had to be defaulted

# Step 1 — deterministic pipeline, no LLM
agent = StrategyOrchestratorAgent()
result = agent.run(scenario)           # dict

# Step 2 — the only LLM call, fed strictly `result`
narrative = agent.summarize(result)    # string
'''

import json

from agent2 import StrategyOrchestratorAgent
from models import Scenario
from test_cases import TEST_CASES


def main():
    agent = StrategyOrchestratorAgent()
    # for scenario in TEST_CASES:
    #     result = agent.run(scenario)
    #     narrative=agent.summarize()

    #     print(f"Narrative: {narrative}")

    #     print("=" * 80)
    #     print(f"SCENARIO: {result['scenario']}")
    #     print("=" * 80)
    #     print(json.dumps(result, indent=2))
    #     print()
    result=agent.run("Secure an desert area at night with 40 personnel, high threat,how much resources do we need if enemy count is 200")
    narrative=agent.summarize(result)
    print(f"Narrative: {narrative}")
    print()
    print("=" * 80)
    print()
    print(f"Scenario: {result["scenario"]}")

if __name__ == "__main__":
    main()
