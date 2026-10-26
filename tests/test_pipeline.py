"""End-to-end integration test running the simplified benchmark pipeline."""

import json
from typing import Any, Optional
import pytest
from unittest.mock import patch
from pathlib import Path
from src.main import execute_simulation_run
from src.llm import OpenAIClient


def dummy_openai_generate(
    self: Any,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 512
) -> str:
    """Offline test double for OpenAIClient.generate during automated unit tests."""
    prompt_lower = prompt.lower()
    if "select the single resolution" in prompt_lower or "options (in randomized order)" in prompt_lower or "ballot" in prompt_lower:
        return "A"
    return "I propose an integrative compromise that addresses both constraints."


def test_full_experiment_pipeline(tmp_path: Path) -> None:
    output_dir = tmp_path / "test_exp_output"

    # Prepare test configuration with 1 trial per item and explicit test output directory
    with open("data/config.json", "r", encoding="utf-8") as f:
        test_cfg = json.load(f)
    test_cfg["deliberation_config"]["trials_per_item"] = 1
    test_cfg["deliberation_config"]["seed"] = 101
    test_cfg["output_dir"] = str(output_dir)

    test_cfg_path = tmp_path / "test_config.json"
    with open(test_cfg_path, "w", encoding="utf-8") as f:
        json.dump(test_cfg, f)

    # Patch OpenAIClient.generate to execute offline during automated testing
    with patch.object(OpenAIClient, "generate", dummy_openai_generate):
        result_dir = execute_simulation_run(config_path=str(test_cfg_path))

    # 1. Verify directory exists
    assert result_dir.exists()

    # 2. Verify all 5 required artifact files exist (Guideline 6)
    expected_files = [
        "config.json",
        "transcripts.json",
        "ballots.json",
        "ctt_irt_metrics.json",
        "final_report.md"
    ]

    for fname in expected_files:
        fpath = result_dir / fname
        assert fpath.exists(), f"Missing expected output file: {fname}"
        assert fpath.stat().st_size > 0, f"Output file is empty: {fname}"

    # 2b. Verify items directory and item definitions copied
    items_dir = result_dir / "items"
    assert items_dir.is_dir()
    assert len(list(items_dir.glob("*.json"))) >= 4

    # 3. Verify transcripts contents
    with open(result_dir / "transcripts.json", "r", encoding="utf-8") as f:
        transcripts_data = json.load(f)
    assert len(transcripts_data) > 0
    first_transcript = transcripts_data[0]
    assert "item_id" in first_transcript
    assert "turns" in first_transcript
    assert len(first_transcript["turns"]) == 4

    # 4. Verify ballot contents
    with open(result_dir / "ballots.json", "r", encoding="utf-8") as f:
        ballots_data = json.load(f)
    assert len(ballots_data) > 0
    first_ballot = ballots_data[0]
    assert "consensus_reached" in first_ballot
    assert "votes" in first_ballot

    # 5. Verify CTT & IRT metrics structure
    with open(result_dir / "ctt_irt_metrics.json", "r", encoding="utf-8") as f:
        metrics_data = json.load(f)
    assert "ctt" in metrics_data
    assert "irt" in metrics_data
    assert "dyad_theta" in metrics_data
    assert "insights" in metrics_data

    # 6. Verify markdown report contents
    with open(result_dir / "final_report.md", "r", encoding="utf-8") as f:
        report_text = f.read()
    assert "# Deliberative Item Response Theory (IRT) Benchmark Report" in report_text
    assert "Standardized Policy Battery Psychometrics" in report_text
    assert "Latent Deliberative Ability Breakdown" in report_text
    assert "Cognitive Trap & Distractor Vulnerability Analysis" in report_text


def test_main_cli_execution(tmp_path: Path) -> None:
    """Test invoking main() via CLI argument parsing with --config."""
    import sys
    from src.main import main

    output_dir = tmp_path / "cli_test_exp_output"
    with open("data/config.json", "r", encoding="utf-8") as f:
        test_cfg = json.load(f)
    test_cfg["deliberation_config"]["trials_per_item"] = 1
    test_cfg["output_dir"] = str(output_dir)

    test_cfg_path = tmp_path / "cli_config.json"
    with open(test_cfg_path, "w", encoding="utf-8") as f:
        json.dump(test_cfg, f)

    with patch.object(sys, "argv", ["main.py", "--config", str(test_cfg_path)]):
        with patch.object(OpenAIClient, "generate", dummy_openai_generate):
            main()

    assert (output_dir / "final_report.md").exists()
    assert (output_dir / "config.json").exists()
    assert (output_dir / "items").is_dir()


def test_missing_env_credentials_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that if OPENAI_API_KEY or OPENAI_BASE_URL is missing, it fails fast with ValueError."""
    from src.llm import OpenAIClient

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIClient(model="openai/gpt-oss-120b")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="OPENAI_BASE_URL"):
        OpenAIClient(model="openai/gpt-oss-120b")
