"""
models.py
=========
Shared data schemas used across all tools and the orchestrator agent.

Keeping the schema in one place means every tool speaks the same "language" -
change a field here and every tool/agent that touches it stays in sync.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Scenario:
    """A mission-planning input. Domain-agnostic: applies to force planning,
    disaster-response logistics, search & rescue, or game-AI strategy."""

    name: str
    objective: str                  # e.g. "secure_area", "escort", "recon", "relief_delivery"
    terrain: str                    # e.g. "urban", "desert", "mountain", "riverine"
    weather: str                    # e.g. "clear", "storm", "night", "fog"
    force_size: int                 # personnel/units available
    time_limit_hours: int
    threat_level: str               # "low", "medium", "high"
    special_constraints: List[str] = field(default_factory=list)
