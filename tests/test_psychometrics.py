"""Unit tests for CTT and IRT psychometric modeling engines."""

import numpy as np
from src.psychometrics import (
    compute_ctt_metrics,
    fit_irt_1pl,
    fit_irt_2pl
)
from src.schemas import DyadBallotRecord


def test_ctt_metrics_calculation():
    ballots: list[DyadBallotRecord] = [
        # Session 1: passes both items
        {
            "item_id": "ITEM_01",
            "dyad_id": "D1",
            "trial_index": 0,
            "votes": {
                "p1": {"item_id": "ITEM_01", "dyad_id": "D1", "trial_index": 0, "persona_id": "p1", "raw_response": "A", "displayed_letter": "A", "selected_key": "A", "is_correct": True, "display_mapping": {}},
                "p2": {"item_id": "ITEM_01", "dyad_id": "D1", "trial_index": 0, "persona_id": "p2", "raw_response": "A", "displayed_letter": "A", "selected_key": "A", "is_correct": True, "display_mapping": {}},
            },
            "consensus_reached": True
        },
        {
            "item_id": "ITEM_02",
            "dyad_id": "D1",
            "trial_index": 0,
            "votes": {
                "p1": {"item_id": "ITEM_02", "dyad_id": "D1", "trial_index": 0, "persona_id": "p1", "raw_response": "A", "displayed_letter": "A", "selected_key": "A", "is_correct": True, "display_mapping": {}},
                "p2": {"item_id": "ITEM_02", "dyad_id": "D1", "trial_index": 0, "persona_id": "p2", "raw_response": "A", "displayed_letter": "A", "selected_key": "A", "is_correct": True, "display_mapping": {}},
            },
            "consensus_reached": True
        },
        # Session 2: fails ITEM_01 (chose B and C), passes ITEM_02
        {
            "item_id": "ITEM_01",
            "dyad_id": "D2",
            "trial_index": 0,
            "votes": {
                "p1": {"item_id": "ITEM_01", "dyad_id": "D2", "trial_index": 0, "persona_id": "p1", "raw_response": "B", "displayed_letter": "B", "selected_key": "B", "is_correct": False, "display_mapping": {}},
                "p2": {"item_id": "ITEM_01", "dyad_id": "D2", "trial_index": 0, "persona_id": "p2", "raw_response": "C", "displayed_letter": "C", "selected_key": "C", "is_correct": False, "display_mapping": {}},
            },
            "consensus_reached": False
        },
        {
            "item_id": "ITEM_02",
            "dyad_id": "D2",
            "trial_index": 0,
            "votes": {
                "p1": {"item_id": "ITEM_02", "dyad_id": "D2", "trial_index": 0, "persona_id": "p1", "raw_response": "A", "displayed_letter": "A", "selected_key": "A", "is_correct": True, "display_mapping": {}},
                "p2": {"item_id": "ITEM_02", "dyad_id": "D2", "trial_index": 0, "persona_id": "p2", "raw_response": "A", "displayed_letter": "A", "selected_key": "A", "is_correct": True, "display_mapping": {}},
            },
            "consensus_reached": True
        },
    ]

    metrics = compute_ctt_metrics(ballots, ["ITEM_01", "ITEM_02"])
    assert "ITEM_01" in metrics
    assert "ITEM_02" in metrics

    # ITEM_01 consensus: 1 / 2 = 0.5
    assert metrics["ITEM_01"]["difficulty_p"] == 0.5
    # ITEM_02 consensus: 2 / 2 = 1.0
    assert metrics["ITEM_02"]["difficulty_p"] == 1.0

    # Distractor counts on ITEM_01: 2 'A', 1 'B', 1 'C'
    assert metrics["ITEM_01"]["distractor_counts"]["A"] == 2
    assert metrics["ITEM_01"]["distractor_counts"]["B"] == 1
    assert metrics["ITEM_01"]["distractor_counts"]["C"] == 1
    # DCR for B: 1 / 2 = 0.5
    assert metrics["ITEM_01"]["distractor_ratios"]["B"] == 0.5


def test_irt_2pl_monotonicity():
    Y = np.array([
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ])

    theta, a, b = fit_irt_2pl(Y)

    assert len(theta) == 4
    assert len(a) == 4
    assert len(b) == 4

    assert not np.isnan(theta).any()
    assert not np.isnan(a).any()
    assert not np.isnan(b).any()

    # Monotonicity of latent ability theta
    assert theta[0] > theta[1]
    assert theta[1] > theta[2]
    assert theta[2] > theta[3]


def test_irt_1pl_monotonicity():
    Y = np.array([
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0]
    ])

    theta, b = fit_irt_1pl(Y)
    assert not np.isnan(theta).any()
    assert not np.isnan(b).any()

    assert theta[0] > theta[1] > theta[2] > theta[3]
    assert b[0] < b[2]


def test_irt_edge_cases():
    Y_all_ones = np.ones((3, 3))
    theta, _, _ = fit_irt_2pl(Y_all_ones)
    assert not np.isnan(theta).any()

    Y_all_zeros = np.zeros((3, 3))
    theta, _, _ = fit_irt_2pl(Y_all_zeros)
    assert not np.isnan(theta).any()
