"""Strict typing schemas using Python built-in typing module (TypedDict).

Simplified benchmark observing latent deliberative competence and item psychometrics across diverse citizen groups.
"""

from typing import TypedDict, List, Dict, Optional, Any, NotRequired


class ItemBallot(TypedDict):
    prompt: str
    options: Dict[str, str]
    correct_key: str


class PolicyItem(TypedDict):
    item_id: str
    title: str
    topic_prompt: str
    ballot: ItemBallot


class DyadConfig(TypedDict, total=False):
    id: str
    name: str
    dynamic: str
    agents: List[str]


class DeliberationConfig(TypedDict, total=False):
    turns_per_item: int
    trials_per_item: int
    mcq_option_order_seed: int
    seed: int
    dyads: List[DyadConfig]


class ModelConfig(TypedDict, total=False):
    agent_model: str
    temperature: float
    max_tokens: int


class ExperimentMetadata(TypedDict):
    name: str
    description: str
    version: str


class SystemPrompts(TypedDict, total=False):
    technocrat: str
    ideologue: str
    populist: str
    everyman: str


class UserPrompts(TypedDict, total=False):
    pre_stance: str
    post_stance: str
    deliberation_turn: str
    secret_ballot: str


class MasterConfig(TypedDict, total=False):
    experiment_metadata: ExperimentMetadata
    model_config: ModelConfig
    system_prompts: SystemPrompts
    user_prompts: UserPrompts
    items: List[str]
    deliberation_config: DeliberationConfig
    output_dir: Optional[str]


class DeliberationTurn(TypedDict):
    turn_index: int
    speaker: str
    persona_id: str
    statement: str


class DeliberationTranscript(TypedDict):
    item_id: str
    item_title: str
    dyad_id: str
    agents: List[str]
    trial_index: int
    turns: List[DeliberationTurn]
    pre_stances: NotRequired[Dict[str, str]]
    post_stances: NotRequired[Dict[str, str]]


class BallotVote(TypedDict):
    item_id: str
    dyad_id: str
    trial_index: int
    persona_id: str
    raw_response: str
    displayed_letter: str
    selected_key: str
    is_correct: bool
    display_mapping: Dict[str, str]


class DyadBallotRecord(TypedDict):
    item_id: str
    dyad_id: str
    trial_index: int
    votes: Dict[str, BallotVote]
    consensus_reached: bool


class CTTMetrics(TypedDict):
    item_id: str
    difficulty_p: float
    discrimination_index: float
    distractor_counts: Dict[str, int]
    distractor_ratios: Dict[str, float]


class IRTMetrics(TypedDict):
    item_id: str
    difficulty_b: float
    discrimination_a: float


class PsychometricResults(TypedDict, total=False):
    ctt: Dict[str, CTTMetrics]
    irt: Dict[str, IRTMetrics]
    dyad_theta: Dict[str, float]
    individual_theta: Dict[str, float]
    persona_by_dyad_theta: Dict[str, Dict[str, float]]
    individual_endorsement_rates: Dict[str, float]
    insights: Dict[str, Any]
