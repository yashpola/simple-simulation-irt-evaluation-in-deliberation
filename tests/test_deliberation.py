"""Unit tests for dyadic deliberation."""

from typing import Optional
from src.deliberation import (
    build_conversation_history,
    conduct_deliberation,
    generate_initial_stances,
    generate_final_stances
)
from src.schemas import DeliberationTurn, PolicyItem
from src.main import load_master_configuration
from src.llm import BaseLLMClient


class TestLLMClient(BaseLLMClient):
    """Simple test double for deliberation unit tests."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        if "initial perspective" in prompt.lower():
            return "Initial stance statement."
        if "final consolidated stance" in prompt.lower():
            return "Concluded stance statement."
        return "I propose we combine necessary structural reform with direct targeted protections."


def test_build_conversation_history():
    turns: list[DeliberationTurn] = [
        {
            "turn_index": 0,
            "speaker": "Technocrat",
            "persona_id": "technocrat",
            "statement": "Let us look at the budget numbers."
        },
        {
            "turn_index": 1,
            "speaker": "Populist",
            "persona_id": "populist",
            "statement": "What about everyday people?"
        }
    ]

    history = build_conversation_history(turns)
    assert "Let us look at the budget numbers." in history
    assert "What about everyday people?" in history


def test_generate_initial_and_final_stances():
    config = load_master_configuration("data/config.json")
    item: PolicyItem = {
        "item_id": "ITEM_01",
        "title": "Test Policy",
        "topic_prompt": "Deliberate on policy",
        "ballot": {"prompt": "Vote", "options": {"A": "Key", "B": "Trap"}, "correct_key": "A"}
    }
    client = TestLLMClient()
    pre_stances = generate_initial_stances(client, config, item, ["technocrat", "ideologue"])
    assert "technocrat" in pre_stances
    assert "ideologue" in pre_stances
    assert len(pre_stances["technocrat"]) > 0

    post_stances = generate_final_stances(client, config, item, ["technocrat", "ideologue"])
    assert "technocrat" in post_stances
    assert "ideologue" in post_stances
    assert len(post_stances["technocrat"]) > 0


def test_conduct_deliberation_turn_structure():
    config = load_master_configuration("data/config.json")
    item: PolicyItem = {
        "item_id": "ITEM_01",
        "title": "Test Policy",
        "topic_prompt": "Deliberate on policy",
        "ballot": {"prompt": "Vote", "options": {"A": "Key", "B": "Trap"}, "correct_key": "A"}
    }

    client = TestLLMClient()
    transcript = conduct_deliberation(
        client=client,
        config=config,
        item=item,
        dyad_id="D1",
        agents=["technocrat", "ideologue"],
        trial_index=0,
        turns_per_item=4
    )

    assert len(transcript["turns"]) == 4
    assert transcript["turns"][0]["persona_id"] == "technocrat"
    assert transcript["turns"][1]["persona_id"] == "ideologue"
    assert transcript["turns"][2]["persona_id"] == "technocrat"
    assert transcript["turns"][3]["persona_id"] == "ideologue"

    for t in transcript["turns"]:
        assert len(t["statement"]) > 0
