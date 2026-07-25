from flask import Flask, render_template, request

from agent2 import StrategyOrchestratorAgent
from tools.query_parser_tool import QueryParserTool

app = Flask(__name__)

agent = StrategyOrchestratorAgent()


@app.route("/", methods=["GET", "POST"])
def entry_point():
    return render_template("index.html")
    
@app.route("/agent", methods=["GET", "POST"])
def defence_agent():
    if request.method == "POST":
        query = (request.form.get("question") or "").strip()
        if not query:
            return render_template(
                "index.html",
                error="Enter a mission description first!",
                query=query,
            )

        parsed = QueryParserTool().run(query)
        scenario = parsed["scenario"]
        result = agent.run(query)
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
