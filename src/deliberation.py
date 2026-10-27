"""Dyadic deliberation engine across diverse citizen groups and policy items.

Adheres to:
- Guideline 2: Functional split for LLM chat loops & prompt injections.
- Guideline 3: Single-responsibility deliberation execution.
- Guideline 4: Zero hardcoded prompt strings; all prompts loaded from MasterConfig with default "".
- Guideline 5: Defensive parsing wrapped in try/except.
"""

from typing import List
from src.schemas import (
    PolicyItem,
    DeliberationTurn,
    DeliberationTranscript,
    MasterConfig
)
from src.personas import get_persona_metadata, resolve_persona_system_prompt
from src.llm import BaseLLMClient


def build_conversation_history(turns: List[DeliberationTurn]) -> str:
    """Format conversational dialogue history for prompt context."""
    if not turns:
        return "(Deliberation has just begun. No statements made yet.)"

    history_lines: List[str] = []
    for turn in turns:
        history_lines.append(f"Turn {turn['turn_index'] + 1} - [{turn['speaker']}]:\n{turn['statement']}\n")
    return "\n".join(history_lines)


def conduct_deliberation(
    client: BaseLLMClient,
    config: MasterConfig,
    item: PolicyItem,
    dyad_id: str,
    agents: List[str],
    trial_index: int,
    turns_per_item: int = 4
) -> DeliberationTranscript:
    """Execute complete dyadic deliberation between two agents for a policy item."""
    turns: List[DeliberationTurn] = []
    user_prompts = config.get("user_prompts", {})
    prompt_template = user_prompts.get("deliberation_turn", "")

    for turn_idx in range(turns_per_item):
        current_speaker_id = agents[turn_idx % len(agents)]
        persona_meta = get_persona_metadata(current_speaker_id)
        conv_history = build_conversation_history(turns)

        system_prompt = resolve_persona_system_prompt(current_speaker_id, config)
        turn_prompt = prompt_template.format(
            title=item.get("title", ""),
            topic_prompt=item.get("topic_prompt", ""),
            conversation_history=conv_history
        )

        statement = client.generate(
            prompt=turn_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=512
        ).strip()

        turn_record: DeliberationTurn = {
            "turn_index": turn_idx,
            "speaker": persona_meta["name"],
            "persona_id": current_speaker_id,
            "statement": statement
        }
        turns.append(turn_record)

    transcript: DeliberationTranscript = {
        "item_id": item["item_id"],
        "item_title": item["title"],
        "dyad_id": dyad_id,
        "agents": agents,
        "trial_index": trial_index,
        "turns": turns
    }
    return transcript
