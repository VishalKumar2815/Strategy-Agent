# AI Strategy Agent

A multi-tool orchestration framework for mission planning: given an
objective, terrain, and constraints, it produces an engagement strategy,
resource requirements, and a route plan.

Domain-agnostic by design — the same architecture works for force planning,
disaster-response logistics, search & rescue, or game-AI strategy.

## Structure

```
strategy_agent/
├── models.py            # Scenario input schema
├── test_cases.py         # sample scenarios (edit/add here)
├── agent.py               # StrategyOrchestratorAgent — the orchestrator
├── main.py                 # demo runner over test_cases.py
├── cli.py                  # free-text entry point (new)
└── tools/
    ├── base.py             # BaseTool interface all tools implement
    ├── query_parser_tool.py # QueryParserTool — free text → Scenario (new)
    ├── terrain_tool.py      # TerrainAnalysisTool
    ├── objective_tool.py    # ObjectiveAnalysisTool
    ├── resource_tool.py     # ResourceEstimatorTool
    └── route_tool.py        # RouteEstimatorTool
```

## Pipeline

```
Free-text query
   │
   ▼
QueryParserTool ──► Scenario
   │
   ├─► TerrainAnalysisTool   ─┐
   ├─► ObjectiveAnalysisTool  │  (independent, can run in parallel)
   │                          ▼
   │                  ResourceEstimatorTool  (needs terrain)
   │                          ▼
   │                  RouteEstimatorTool     (needs terrain + resources)
   ▼
StrategyOrchestratorAgent.run() ──► final synthesized answer
```

## Run it

Demo over the built-in test cases:

```bash
cd <parent of strategy_agent/>
python3 -m strategy_agent.main
```

From a free-text mission description:

```bash
python3 -m strategy_agent.cli "Secure an urban area at night with 40 personnel, high threat, 12 hour window, minimize civilian disruption"
```

Or run it interactively (prompts for input):

```bash
python3 -m strategy_agent.cli
```

`QueryParserTool` extracts `objective`, `terrain`, `weather`, `force_size`,
`time_limit_hours`, `threat_level`, and `special_constraints` from the text
via keyword/regex matching. Any field it can't find falls back to a
documented default and is reported in `assumptions_used_default`, so you
always see what was guessed vs. what was actually stated.

## Extending

- **Add a scenario**: append a `Scenario(...)` to `test_cases.py`.
- **Add a new terrain/objective**: add an entry to the relevant tool's
  lookup table (e.g. `TerrainAnalysisTool.PROFILES`).
- **Upgrade `QueryParserTool` to a real LLM call**: the keyword/regex
  matching is brittle to phrasing it hasn't seen. Replace `run()`'s body
  with a call to Claude/GPT/DeepSeek prompted to extract the same fields
  as structured JSON, keeping the return shape
  `{"scenario": Scenario(...), "assumptions_used_default": [...], "raw_query": str}` —
  `cli.py` needs no changes.
- **Upgrade a tool to a real LLM call** (Claude / GPT / DeepSeek): replace
  only that tool's `run()` body — keep the same input args and dict-shaped
  return value — and neither the agent nor any other tool needs to change.
- **Add a new tool**: subclass `BaseTool`, implement `run(**kwargs) -> dict`,
  then call it from `StrategyOrchestratorAgent.run()`.

## Output shape

`agent.run(scenario)` returns:

```json
{
  "scenario": "...",
  "1_engagement_strategy": {...},
  "2_resource_requirements": {...},
  "3_route_plan": {...},
  "success_criteria": [...],
  "constraints_considered": [...]
}
```
