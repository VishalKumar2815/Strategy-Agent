import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from tools.base import BaseTool

try:
    from langchain_groq import ChatGroq
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")


PARSER_PROMPT = """
You are an Incident Intelligence Extraction Agent.
Your job is ONLY to extract operational information.
Do NOT recommend anything.
Return ONLY valid JSON.
Extract every important fact.

Schema:
{
"incident_type":"",
"location":"",
"severity":"",
"casualties":0,
"critical_casualties":0,
"trapped_people":0,
"weather":"",
"terrain":"",
"visibility":"",
"road_status":"",
"bridge_status":"",
"communication_status":"",
"hostile_activity":false,
"civilian_presence":false,
"infrastructure_damage":"",
"vehicle_damage":"",
"fire_present":false,
"hazardous_material":false,
"medical_evacuation":false,
"requested_resources":[],
"additional_information":""
}

Return JSON only.
No markdown.
No explanation.
"""

ANALYZER_PROMPT = """
You are a Senior Emergency Incident Commander.
Analyze the structured incident below.
DO NOT recommend medical teams.
DO NOT recommend reinforcement.
ONLY assess the situation.
Return JSON.
Schema
{
"mission_priority":"",
"threat_level":"",
"operational_complexity":"",
"civilian_risk":"",
"responder_risk":"",
"resource_urgency":"",
"estimated_response_time":"",
"recommended_command_level":"",
"key_risks":[],
"reasoning":"",
"confidence":0.0
}
Return ONLY JSON.
"""

PLANNER_PROMPT = """
You are the Strategic Incident Response Planner.
You are given
1. Incident Information
2. Situation Analysis
Recommend
- Reinforcement
- Medical Resources
- Logistics
- Equipment
- Immediate Actions
- Deployment Order
- Evacuation Strategy
Return ONLY JSON.
Schema
{
"reinforcement":{"personnel":0,"combat_units":[],"support_units":[],"engineering_units":[],"air_support":[]},
"medical":{"ambulances":0,"field_medics":0,"doctors":0,"trauma_teams":0,"field_hospital":false,"air_evacuation":false},
"logistics":{"fuel_trucks":0,"water_supply":false,"food_supply":false,"portable_generators":0,"communication_vehicles":0},
"equipment":[],
"immediate_actions":[],
"deployment_sequence":[],
"evacuation_strategy":"",
"estimated_resources":{},
"commander_notes":""
}
Return ONLY JSON.
No explanation.
"""

REPORT_PROMPT = """
You are an Incident Commander.
Using the supplied Incident, Situation Analysis, and Operational Plan,
generate a professional operational report.
Format
1. Incident Summary
2. Threat Assessment
3. Recommended Reinforcement
4. Medical Deployment
5. Logistics
6. Immediate Actions
7. Evacuation
8. Command Notes
Keep it concise.
Return ONLY plain text.
"""


@dataclass
class Incident:
    raw_query: str
    incident_type: str = "Unknown"
    location: str = "Unknown"
    severity: str = "Unknown"
    casualties: int = 0
    critical_casualties: int = 0
    trapped_people: int = 0
    weather: str = "Unknown"
    terrain: str = "Unknown"
    visibility: str = "Unknown"
    road_status: str = "Unknown"
    bridge_status: str = "Unknown"
    communication_status: str = "Operational"
    hostile_activity: bool = False
    civilian_presence: bool = False
    infrastructure_damage: str = "Unknown"
    vehicle_damage: str = "Unknown"
    fire_present: bool = False
    hazardous_material: bool = False
    medical_evacuation: bool = False
    requested_resources: List[str] = field(default_factory=list)
    additional_information: str = ""
    used_fallback: bool = False   # NEW - tells the caller whether the LLM
                                    # actually parsed this, or the rule-based
                                    # fallback did.


@dataclass
class SituationAnalysis:
    mission_priority: str = "Unknown"
    threat_level: str = "Unknown"
    operational_complexity: str = "Unknown"
    civilian_risk: str = "Unknown"
    responder_risk: str = "Unknown"
    resource_urgency: str = "Unknown"
    estimated_response_time: str = "Unknown"
    recommended_command_level: str = "Unknown"
    key_risks: List[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    used_fallback: bool = False


@dataclass
class OperationalPlan:
    reinforcement: Dict = field(default_factory=dict)
    medical: Dict = field(default_factory=dict)
    logistics: Dict = field(default_factory=dict)
    equipment: List[str] = field(default_factory=list)
    immediate_actions: List[str] = field(default_factory=list)
    deployment_sequence: List[str] = field(default_factory=list)
    evacuation_strategy: str = ""
    estimated_resources: Dict = field(default_factory=dict)
    commander_notes: str = ""
    used_fallback: bool = False


# ---------------------------------------------------------------------
# Type coercion helpers - LLMs frequently return "5" instead of 5, or
# "true"/"yes" instead of true. Coerce defensively instead of trusting
# the model's output shape blindly.
# ---------------------------------------------------------------------

def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return default


class LLMEngine:
    """Lazily-constructed - does NOT raise at import time or at
    IncidentResponseTool.__init__() time. The ChatGroq client is only
    built the first time it's actually needed, and any failure to build
    it is caught, not propagated - callers check `self.llm.available`
    instead of relying on an exception that used to happen too early."""

    def __init__(self):
        self.available = False
        self.model = None
        if not LLM_AVAILABLE or not api_key:
            return
        try:
            self.model = ChatGroq(model="qwen/qwen3.6-27b", temperature=0, reasoning_format="hidden")
            self.available = True
        except Exception:
            self.available = False

    def parse_json(self, response: str) -> Dict[str, Any]:
        response = response.strip()
        response = response.replace("```json", "").replace("```", "")
        start = response.find("{")
        end = response.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in LLM response")
        return json.loads(response[start:end + 1])

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.available:
            raise RuntimeError("LLM not available (no GROQ_API_KEY or client failed to initialize)")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self.model.invoke(messages)
        return response.content


class IncidentResponseTool(BaseTool):
    """
    Pipeline: SITREP -> _parse -> Incident -> _analyze -> SituationAnalysis
    -> _plan_resources -> OperationalPlan -> _generate_report -> plain text.

    Every LLM-backed stage now has a rule-based / safe-default fallback,
    so run() ALWAYS returns a usable result even with zero API key
    configured, or if Groq deprecates the model again mid-flight (this
    already happened once in this project - qwen/qwen3-32b 404'd).
    """

    name = "incident_response"

    def __init__(self):
        self.llm = LLMEngine()

    # -------------------------------------------------------------
    # Stage 1: Parse
    # -------------------------------------------------------------

    def _rule_based_parse(self, query: str) -> Incident:
        text_lower = query.lower()

        casualties = 0
        import re
        m = re.search(r"(\d+)\s*(people|persons)?\s*(are\s+)?(trapped|injured|casualt)", text_lower)
        if m:
            casualties = _to_int(m.group(1))

        incident_type = "Unknown"
        for kind, kws in {
            "structure_collapse": ["collapse", "building down", "rubble"],
            "ambush": ["ambush", "under fire", "engaged"],
            "flooding": ["flood", "water rising"],
            "medical_emergency": ["injured", "casualty", "wounded"],
        }.items():
            if any(k in text_lower for k in kws):
                incident_type = kind
                break

        return Incident(
            raw_query=query,
            incident_type=incident_type,
            casualties=casualties,
            trapped_people=casualties if "trapped" in text_lower else 0,
            hostile_activity=any(k in text_lower for k in ["ambush", "under fire", "hostile"]),
            fire_present="fire" in text_lower,
            used_fallback=True,
        )

    def _parse(self, query: str) -> Incident:
        if not self.llm.available:
            return self._rule_based_parse(query)
        try:
            response = self.llm.generate(PARSER_PROMPT, query)
            data = self.llm.parse_json(response)
            return Incident(
                raw_query=query,
                incident_type=data.get("incident_type", "Unknown"),
                location=data.get("location", "Unknown"),
                severity=data.get("severity", "Unknown"),
                casualties=_to_int(data.get("casualties", 0)),
                critical_casualties=_to_int(data.get("critical_casualties", 0)),
                trapped_people=_to_int(data.get("trapped_people", 0)),
                weather=data.get("weather", "Unknown"),
                terrain=data.get("terrain", "Unknown"),
                visibility=data.get("visibility", "Unknown"),
                road_status=data.get("road_status", "Unknown"),
                bridge_status=data.get("bridge_status", "Unknown"),
                communication_status=data.get("communication_status", "Operational"),
                hostile_activity=_to_bool(data.get("hostile_activity", False)),
                civilian_presence=_to_bool(data.get("civilian_presence", False)),
                infrastructure_damage=data.get("infrastructure_damage", "Unknown"),
                vehicle_damage=data.get("vehicle_damage", "Unknown"),
                fire_present=_to_bool(data.get("fire_present", False)),
                hazardous_material=_to_bool(data.get("hazardous_material", False)),
                medical_evacuation=_to_bool(data.get("medical_evacuation", False)),
                requested_resources=data.get("requested_resources", []) or [],
                additional_information=data.get("additional_information", ""),
                used_fallback=False,
            )
        except Exception:
            return self._rule_based_parse(query)

    # -------------------------------------------------------------
    # Stage 2: Analyze
    # -------------------------------------------------------------

    def _rule_based_analyze(self, incident: Incident) -> SituationAnalysis:
        score = incident.casualties + incident.critical_casualties * 2 + incident.trapped_people
        if incident.hostile_activity:
            score += 5
        priority = "Critical" if score >= 10 else "High" if score >= 5 else "Medium" if score >= 1 else "Low"
        return SituationAnalysis(
            mission_priority=priority,
            threat_level="High" if incident.hostile_activity else "Low",
            reasoning="Rule-based fallback analysis (LLM unavailable).",
            confidence=0.3,
            used_fallback=True,
        )

    def _analyze(self, incident: Incident) -> SituationAnalysis:
        if not self.llm.available:
            return self._rule_based_analyze(incident)
        try:
            incident_json = json.dumps(asdict(incident), indent=2)
            response = self.llm.generate(ANALYZER_PROMPT, incident_json)
            data = self.llm.parse_json(response)   # FIX: was raw json.loads before
            return SituationAnalysis(
                mission_priority=data.get("mission_priority", "Unknown"),
                threat_level=data.get("threat_level", "Unknown"),
                operational_complexity=data.get("operational_complexity", "Unknown"),
                civilian_risk=data.get("civilian_risk", "Unknown"),
                responder_risk=data.get("responder_risk", "Unknown"),
                resource_urgency=data.get("resource_urgency", "Unknown"),
                estimated_response_time=data.get("estimated_response_time", "Unknown"),
                recommended_command_level=data.get("recommended_command_level", "Unknown"),
                key_risks=data.get("key_risks", []) or [],
                reasoning=data.get("reasoning", ""),
                confidence=_to_float(data.get("confidence", 0)),
                used_fallback=False,
            )
        except Exception:
            return self._rule_based_analyze(incident)

    # -------------------------------------------------------------
    # Stage 3: Plan
    # -------------------------------------------------------------

    def _rule_based_plan(self, incident: Incident, analysis: SituationAnalysis) -> OperationalPlan:
        return OperationalPlan(
            reinforcement={"personnel": max(incident.casualties * 2, 5), "combat_units": [], "support_units": ["QRF"], "engineering_units": [], "air_support": []},
            medical={"ambulances": max(1, incident.casualties // 3), "field_medics": max(1, incident.casualties), "doctors": 1 if incident.critical_casualties else 0, "trauma_teams": 1 if incident.critical_casualties else 0, "field_hospital": incident.critical_casualties > 3, "air_evacuation": incident.critical_casualties > 0},
            logistics={"fuel_trucks": 0, "water_supply": False, "food_supply": False, "portable_generators": 0, "communication_vehicles": 1},
            immediate_actions=["Dispatch nearest available response unit", "Establish communications with scene"],
            commander_notes="Rule-based fallback plan (LLM unavailable) - verify manually.",
            used_fallback=True,
        )

    def _plan_resources(self, incident: Incident, analysis: SituationAnalysis) -> OperationalPlan:
        if not self.llm.available:
            return self._rule_based_plan(incident, analysis)
        try:
            payload = {"incident": asdict(incident), "analysis": asdict(analysis)}
            response = self.llm.generate(PLANNER_PROMPT, json.dumps(payload, indent=2))
            data = self.llm.parse_json(response)   # FIX: was raw json.loads before
            return OperationalPlan(
                reinforcement=data.get("reinforcement", {}) or {},
                medical=data.get("medical", {}) or {},
                logistics=data.get("logistics", {}) or {},
                equipment=data.get("equipment", []) or [],
                immediate_actions=data.get("immediate_actions", []) or [],
                deployment_sequence=data.get("deployment_sequence", []) or [],
                evacuation_strategy=data.get("evacuation_strategy", ""),
                estimated_resources=data.get("estimated_resources", {}) or {},
                commander_notes=data.get("commander_notes", ""),
                used_fallback=False,
            )
        except Exception:
            return self._rule_based_plan(incident, analysis)

    # -------------------------------------------------------------
    # Stage 4: Report
    # -------------------------------------------------------------

    def _fallback_report(self, incident: Incident, analysis: SituationAnalysis, plan: OperationalPlan) -> str:
        return (
            f"[Fallback report — LLM unavailable]\n\n"
            f"1. Incident Summary: {incident.incident_type} at {incident.location}, "
            f"{incident.casualties} casualties ({incident.critical_casualties} critical), "
            f"{incident.trapped_people} trapped.\n"
            f"2. Threat Assessment: priority={analysis.mission_priority}, threat={analysis.threat_level}\n"
            f"3. Recommended Reinforcement: {plan.reinforcement}\n"
            f"4. Medical Deployment: {plan.medical}\n"
            f"5. Logistics: {plan.logistics}\n"
            f"6. Immediate Actions: {', '.join(plan.immediate_actions) or 'none specified'}\n"
            f"7. Evacuation: {plan.evacuation_strategy or 'not specified'}\n"
            f"8. Command Notes: {plan.commander_notes}"
        )

    def _generate_report(self, incident: Incident, analysis: SituationAnalysis, plan: OperationalPlan) -> str:
        if not self.llm.available:
            return self._fallback_report(incident, analysis, plan)
        try:
            payload = {"incident": asdict(incident), "analysis": asdict(analysis), "plan": asdict(plan)}
            return self.llm.generate(REPORT_PROMPT, json.dumps(payload, indent=2))
        except Exception:
            return self._fallback_report(incident, analysis, plan)

    # -------------------------------------------------------------
    # Orchestration
    # -------------------------------------------------------------

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        incident = self._parse(query)
        analysis = self._analyze(incident)
        plan = self._plan_resources(incident, analysis)
        report = self._generate_report(incident, analysis, plan)

        return {
            "incident": asdict(incident),
            "analysis": asdict(analysis),
            "operational_plan": asdict(plan),
            "report": report,
            "llm_available": self.llm.available,
        }


# if __name__ == "__main__":
#     tool = IncidentResponseTool()
#     result = tool.run(query="A building collapse happened. 20 people are trapped. Five are critically injured. Ten rescued.")
#     print(json.dumps(result, indent=2))
