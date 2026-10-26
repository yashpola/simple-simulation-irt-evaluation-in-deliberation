"""Citizen persona registry and configuration-driven prompt resolution.

Adheres to Guideline 4: Zero hardcoded prompt strings in Python logic.
All prompts are loaded strictly from MasterConfig.
"""

from typing import Dict
from src.schemas import MasterConfig


PERSONA_METADATA: Dict[str, Dict[str, str]] = {
    "technocrat": {
        "id": "technocrat",
        "name": "Technocratic Pragmatist (P1)",
        "knowledge": "High",
        "affective_polarization": "Low",
        "description": "Focuses on fiscal feasibility, operational constraints, and systemic efficiency; uses analytical, neutral language.",
        "typical_trap": "Technocratic zero-sum coldness (Option C) disregarding citizen lived disruption."
    },
    "ideologue": {
        "id": "ideologue",
        "name": "Ideological Advocate (P2)",
        "knowledge": "High",
        "affective_polarization": "High",
        "description": "Possesses sophisticated policy awareness, but maintains rigid moral commitments and deep skepticism toward technocratic trade-offs.",
        "typical_trap": "Ideological rigidity / status quo inertia (Option B) if uncompromising on pristine principles."
    },
    "populist": {
        "id": "populist",
        "name": "Disaffected Populist (P3)",
        "knowledge": "Low",
        "affective_polarization": "High",
        "description": "Emotive, candid, and defensive; feels everyday citizens are sidelined by out-of-touch elites; prone to deflection heuristics.",
        "typical_trap": "External scapegoating/deflection (Option D) or status-quo freeze (Option B)."
    },
    "everyman": {
        "id": "everyman",
        "name": "Open-Minded Everyman (P4)",
        "knowledge": "Low",
        "affective_polarization": "Low",
        "description": "Limited policy jargon, intuitive daily-life common sense, humble, constructive, and highly receptive to reasonable arguments.",
        "typical_trap": "Vulnerable to whichever rhetoric seems most persuasive if unguided."
    }
}


def get_persona_metadata(persona_id: str) -> Dict[str, str]:
    """Retrieve persona biographical metadata by ID with safe defaults."""
    clean_id = persona_id.lower().strip()
    return PERSONA_METADATA.get(
        clean_id,
        {
            "id": clean_id,
            "name": clean_id.capitalize(),
            "knowledge": "Medium",
            "affective_polarization": "Medium",
            "description": f"Citizen persona: {clean_id}",
            "typical_trap": "General heuristic trap"
        }
    )


def resolve_persona_system_prompt(
    persona_id: str,
    config: MasterConfig
) -> str:
    """Resolve system prompt for a persona strictly from MasterConfig."""
    clean_id = persona_id.lower().strip()
    system_prompts = config.get("system_prompts", {})
    prompt = system_prompts.get(clean_id, "")
    return str(prompt) if prompt else ""
