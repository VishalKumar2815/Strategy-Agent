"""
test_cases.py
=============
Illustrative scenarios spanning different objectives, terrains, weather, and
threat levels. Add new Scenario entries here to extend coverage - no other
file needs to change.
"""

from typing import List

from models import Scenario


TEST_CASES: List[Scenario] = [
    Scenario(
        name="TC1 - Urban Area Security",
        objective="secure_area",
        terrain="urban",
        weather="night",
        force_size=40,
        time_limit_hours=12,
        threat_level="high",
        special_constraints=["minimize civilian disruption", "limited air support"],
    ),
    Scenario(
        name="TC2 - Desert Convoy Escort",
        objective="escort",
        terrain="desert",
        weather="clear",
        force_size=25,
        time_limit_hours=8,
        threat_level="medium",
        special_constraints=["fuel resupply needed every 150km"],
    ),
    Scenario(
        name="TC3 - Mountain Reconnaissance",
        objective="recon",
        terrain="mountain",
        weather="fog",
        force_size=10,
        time_limit_hours=24,
        threat_level="low",
        special_constraints=["stealth priority", "no vehicle access above 2500m"],
    ),
    Scenario(
        name="TC4 - Riverine Relief Delivery",
        objective="relief_delivery",
        terrain="riverine",
        weather="storm",
        force_size=30,
        time_limit_hours=18,
        threat_level="medium",
        special_constraints=["flood-damaged bridges", "medical supplies time-sensitive"],
    ),
]
