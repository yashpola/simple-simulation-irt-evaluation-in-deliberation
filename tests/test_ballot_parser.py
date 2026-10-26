"""Unit tests for secret ballot parser and option display randomization."""

import random
from src.ballot import parse_ballot_choice, prepare_randomized_ballot
from src.schemas import PolicyItem


def test_parse_ballot_choice_exact():
    assert parse_ballot_choice("A") == "A"
    assert parse_ballot_choice("b") == "B"
    assert parse_ballot_choice(" C ") == "C"
    assert parse_ballot_choice("D\n") == "D"


def test_parse_ballot_choice_prefixed():
    assert parse_ballot_choice("Option A") == "A"
    assert parse_ballot_choice("Choice: B") == "B"
    assert parse_ballot_choice("Answer: C.") == "C"
    assert parse_ballot_choice("Selection: D") == "D"
    assert parse_ballot_choice("Option (B)") == "B"


def test_parse_ballot_choice_markdown_and_tokens():
    assert parse_ballot_choice("**A**") == "A"
    assert parse_ballot_choice("(C)") == "C"
    assert parse_ballot_choice("[B]") == "B"
    assert parse_ballot_choice("I choose Option A.") == "A"
    assert parse_ballot_choice("My final vote is C.") == "C"


def test_parse_ballot_choice_invalid():
    assert parse_ballot_choice("E") is None
    assert parse_ballot_choice("None of the above") is None
    assert parse_ballot_choice("I cannot decide") is None


def test_prepare_randomized_ballot_mappings():
    item: PolicyItem = {
        "item_id": "TEST_01",
        "title": "Test Item",
        "topic_prompt": "Prompt context",
        "ballot": {
            "prompt": "Choose one",
            "options": {
                "A": "Integrative Compromise",
                "B": "Status Quo",
                "C": "Zero Sum",
                "D": "Scapegoat"
            },
            "correct_key": "A"
        }
    }

    rng = random.Random(123)
    disp_to_canon, canon_to_disp, formatted_text = prepare_randomized_ballot(item, rng)

    # Validate bijection
    assert set(disp_to_canon.keys()) == {"A", "B", "C", "D"}
    assert set(disp_to_canon.values()) == {"A", "B", "C", "D"}
    for d, c in disp_to_canon.items():
        assert canon_to_disp[c] == d

    # Validate formatted text contains all option descriptions
    for _, desc in item["ballot"]["options"].items():
        assert desc in formatted_text
