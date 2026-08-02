import os
from flask import Flask, render_template, request

from strategy_agent.agent2 import StrategyOrchestratorAgent
from strategy_agent.tools.query_parser_tool import QueryParserTool
from strategy_agent.tools.escape_tool import IncidentResponseTool  # adjust path to match wherever you place escape_tool_optimized.py

app = Flask(__name__)

agent = StrategyOrchestratorAgent()
incident_tool = IncidentResponseTool()


@app.route("/", methods=["GET", "POST"])
@app.route("/agent", methods=["GET", "POST"])
def defence_agent():

    if request.method == "POST":
        incident_query = (request.form.get("incident_query") or "").strip()
        query = (request.form.get("question") or "").strip()

        # ---- Escape / incident-response form submitted ----
        if incident_query:
            incident_response = incident_tool.run(query=incident_query)
            return render_template(
                "index.html",
                incident_query=incident_query,
                incident_response=incident_response,
            )

        # ---- Mission strategy form submitted ----
        if not query:
            return render_template(
                "index.html",
                error="Enter a mission description first!",
                query=query,
            )

        parsed = QueryParserTool().run(query)
        scenario = parsed["scenario"]
        result = agent.run(query=query)
        summary = agent.summarize(result)

        return render_template(
            "index.html",
            query=query,
            result=result,
            summary=summary,
            scenario=scenario,
            assumptions=parsed.get("assumptions_used_default", []),
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
