"""Secret ballot voting runner and defensive response parser.

Adheres to:
- Guideline 1: Strict typing using TypedDict schemas.
- Guideline 3: Single-responsibility functions.
- Guideline 4: Prompt template loaded from config with fallback to "".
- Guideline 5: Defensive regex parsing with try/except wrappers.
"""

import random
import re
from typing import Dict, Tuple, List, Optional
from src.schemas import (
    PolicyItem,
    BallotVote,
    DyadBallotRecord,
    MasterConfig
)
from src.personas import resolve_persona_system_prompt
from src.llm import BaseLLMClient


def parse_ballot_choice(raw_text: str, valid_options: List[str] = ["A", "B", "C", "D"]) -> Optional[str]:
    """Strictly extract selected option letter from LLM response.

    Defensively wrapped in try/except. Supports exact letter, prefixes, markdown, and token bounds.
    """
    try:
        cleaned = raw_text.strip()
        valid_set = set(opt.upper() for opt in valid_options)

        # 1. Exact match on single letter
        if cleaned.upper() in valid_set:
            return cleaned.upper()

        # 2. Strict prefix match: e.g. "Option A", "Choice: B", "Answer: C"
        match = re.match(r"^(?:option|choice|answer|selection)?\s*[:\-\.]?\s*\(?([A-D])\)?(?:\.|\s|$)", cleaned, re.IGNORECASE)
        if match and match.group(1).upper() in valid_set:
            return match.group(1).upper()

        # 3. Search for isolated letter: (A), [B], or bold **C**
        token_match = re.search(r"(?:[\(\[\*]|^)([A-D])(?:[\)\]\*]|\.|\s|$)", cleaned, re.IGNORECASE)
        if token_match and token_match.group(1).upper() in valid_set:
            return token_match.group(1).upper()

        # 4. Fallback search for any capital A-D word boundary
        fallback_match = re.search(r"\b([A-D])\b", cleaned)
        if fallback_match and fallback_match.group(1) in valid_set:
            return fallback_match.group(1)
    except Exception:
        pass

    return None


def prepare_randomized_ballot(
    item: PolicyItem,
    rng: Optional[random.Random] = None
) -> Tuple[Dict[str, str], Dict[str, str], str]:
    """Randomize the display order of ballot options to avoid position bias.

    Returns:
    - display_to_canonical: dict mapping displayed letter (e.g. 'A') -> canonical key (e.g. 'C')
    - canonical_to_display: dict mapping canonical key -> displayed letter
    - formatted_prompt: formatted text of options for display
    """
    if rng is None:
        rng = random.Random()

    ballot_info = item.get("ballot", {})
    options_dict = ballot_info.get("options", {})
    canonical_keys = list(options_dict.keys())
    shuffled_keys = list(canonical_keys)
    rng.shuffle(shuffled_keys)

    display_letters = ["A", "B", "C", "D"][:len(shuffled_keys)]
    display_to_canonical: Dict[str, str] = {}
    canonical_to_display: Dict[str, str] = {}
    options_text_lines: List[str] = []

    for disp_letter, canon_key in zip(display_letters, shuffled_keys):
        display_to_canonical[disp_letter] = canon_key
        canonical_to_display[canon_key] = disp_letter
        option_desc = options_dict.get(canon_key, "")
        options_text_lines.append(f"{disp_letter}. {option_desc}")

    formatted_options = "\n".join(options_text_lines)
    return display_to_canonical, canonical_to_display, formatted_options


def administer_agent_ballot(
    client: BaseLLMClient,
    config: MasterConfig,
    persona_id: str,
    item: PolicyItem,
    dyad_id: str,
    trial_index: int,
    transcript_summary: str,
    rng: Optional[random.Random] = None,
) -> BallotVote:
    """Administer secret ballot to a single agent and record choice."""
    display_to_canon, _, formatted_options = prepare_randomized_ballot(item, rng)

    ballot_prompt_template = config.get("user_prompts", {}).get("secret_ballot", "")
    ballot_info = item.get("ballot", {})
    correct_key = ballot_info.get("correct_key", "A")

    ballot_prompt = ballot_prompt_template.format(
        title=item.get("title", ""),
        topic_prompt=item.get("topic_prompt", ""),
        transcript_summary=transcript_summary,
        ballot_prompt=ballot_info.get("prompt", ""),
        formatted_options=formatted_options
    )

    model_cfg = config.get("model_config", {})
    model_seed = model_cfg.get("seed", None)
    system_prompt = resolve_persona_system_prompt(persona_id, config)
    raw_response = client.generate(
        prompt=ballot_prompt,
        system_prompt=system_prompt,
        temperature=0.3,
        max_tokens=32,
        seed=model_seed
    )

    parsed_display_letter = parse_ballot_choice(raw_response, list(display_to_canon.keys()))
    if not parsed_display_letter:
        parsed_display_letter = "A"

    selected_canonical_key = display_to_canon.get(parsed_display_letter, "A")
    is_correct = bool(selected_canonical_key == correct_key)

    vote: BallotVote = {
        "item_id": item["item_id"],
        "dyad_id": dyad_id,
        "trial_index": trial_index,
        "persona_id": persona_id,
        "raw_response": raw_response,
        "displayed_letter": parsed_display_letter,
        "selected_key": selected_canonical_key,
        "is_correct": is_correct,
        "display_mapping": display_to_canon
    }
    return vote


def administer_dyad_ballot(
    client: BaseLLMClient,
    config: MasterConfig,
    agents: List[str],
    item: PolicyItem,
    dyad_id: str,
    trial_index: int,
    transcript_summary: str,
    mcq_option_order_seed: Optional[int] = None,
    seed: Optional[int] = None,
) -> DyadBallotRecord:
    """Run independent secret ballots for both agents in a dyad and evaluate consensus.

    The mcq_option_order_seed (or legacy seed) determines the pseudo-random shuffling
    of MCQ ballot option letters (A/B/C/D) to mitigate LLM position bias.
    """
    effective_seed = mcq_option_order_seed if mcq_option_order_seed is not None else seed
    votes: Dict[str, BallotVote] = {}
    for idx, persona_id in enumerate(agents):
        agent_seed = (effective_seed + idx * 1000 + trial_index) if effective_seed is not None else None
        rng = random.Random(agent_seed)
        vote = administer_agent_ballot(
            client=client,
            config=config,
            persona_id=persona_id,
            item=item,
            dyad_id=dyad_id,
            trial_index=trial_index,
            transcript_summary=transcript_summary,
            rng=rng
        )
        votes[persona_id] = vote

    # Consensus reached if ALL agents in dyad chose the integrative compromise (target key)
    consensus = bool(all(v["is_correct"] for v in votes.values()))

    ballot_record: DyadBallotRecord = {
        "item_id": item["item_id"],
        "dyad_id": dyad_id,
        "trial_index": trial_index,
        "votes": votes,
        "consensus_reached": consensus
    }
    return ballot_record
