"""Master orchestrator and CLI entry point for Deliberative IRT Simulation.

Adheres to:
- Guideline 1: Strict typing schemas using TypedDict.
- Guideline 2: Separation of concerns (main.py is reserved strictly as the orchestrator and CLI).
- Guideline 3: Explicit orchestration naming (execute_simulation_run) and single-responsibility steps.
- Guideline 4: Zero hardcoded prompt strings.
- Guideline 6: Auto-incremented expXXX output directories.
"""

import argparse
import glob
import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    from dotenv import load_dotenv  # pyright: ignore[reportUnknownVariableType]
    _ = load_dotenv()
except ImportError:
    pass

from src.schemas import (
    MasterConfig,
    PolicyItem,
    DeliberationTranscript,
    DyadBallotRecord,
    PsychometricResults
)
from src.llm import get_llm_client
from src.deliberation import conduct_deliberation
from src.ballot import administer_dyad_ballot
from src.psychometrics import analyze_experiment_psychometrics
from src.report import generate_markdown_report


def get_next_experiment_dir(base_dir: str = "data") -> Path:
    """Detect existing expXXX directories and create the next auto-incremented index."""
    os.makedirs(base_dir, exist_ok=True)
    existing_dirs = glob.glob(os.path.join(base_dir, "exp[0-9][0-9][0-9]"))
    indices: List[int] = []
    for d in existing_dirs:
        m = re.search(r"exp(\d{3,})$", d)
        if m:
            indices.append(int(m.group(1)))

    next_idx = max(indices) + 1 if indices else 0
    exp_dir = Path(base_dir) / f"exp{next_idx:03d}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    return exp_dir


def load_master_configuration(config_path: str) -> MasterConfig:
    """Load master configuration from JSON file."""
    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(p, "r", encoding="utf-8") as f:
        data: MasterConfig = json.load(f)
    return data


def load_policy_battery_items(item_paths: List[str]) -> Dict[str, PolicyItem]:
    """Load standardized test battery items from individual JSON files."""
    items: Dict[str, PolicyItem] = {}
    for path in item_paths:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Policy battery item not found: {path}")
        with open(p, "r", encoding="utf-8") as f:
            item_data: PolicyItem = json.load(f)
        items[item_data["item_id"]] = item_data
    return items


def execute_simulation_run(
    config_path: str = "data/config.json",
    output_dir: Optional[Union[str, Path]] = None
) -> Path:
    """Primary simulation orchestrator executing the deliberative benchmark.

    All experimental parameters are defined within the configuration JSON file.
    Adheres to:
    - Guideline 3: Explicit orchestration naming and single-responsibility step dispatch.
    - Guideline 4: Total configuration abstraction.
    - Guideline 6: Dynamic experiment output indexing.
    """
    # 1. Load configuration
    config = load_master_configuration(config_path)

    # Apply environment variable defaults if present
    model_cfg = config.setdefault("model_config", {})

    # 2. Output directory resolution (Guideline 6)
    target_output_dir = output_dir or config.get("output_dir")
    if target_output_dir:
        exp_dir = Path(target_output_dir)
        exp_dir.mkdir(parents=True, exist_ok=True)
    else:
        exp_dir = get_next_experiment_dir()

    delib_cfg = config.get("deliberation_config", {})
    trials_per_item = delib_cfg.get("trials_per_item", 5)
    dyads = delib_cfg.get("dyads", [])
    turns_per_item = delib_cfg.get("turns_per_item", 4)
    seed = delib_cfg.get("seed", 42)

    # 3. Load standardized test battery
    items = load_policy_battery_items(config.get("items", []))

    # 4. Initialize LLM inference client
    client = get_llm_client(model_cfg, is_judge=False)

    print(f"🚀 Initializing Deliberative IRT Simulation Benchmark")
    print(f"📁 Output Directory: {exp_dir}")
    print(f"🤖 LLM Model: {client.model} (Fallback: {client.fallback_model})")
    print(f"📊 Policy Items: {list(items.keys())}")
    print(f"👥 Citizen Dyads: {[d.get('id') for d in dyads]}")
    print(f"🔄 Trials per item: {trials_per_item}")

    transcripts: List[DeliberationTranscript] = []
    all_ballots: List[DyadBallotRecord] = []

    # 5. Experimental Execution Matrix
    total_steps = trials_per_item * len(items) * len(dyads)
    current_step = 0

    for trial_idx in range(trials_per_item):
        for item_id, item in items.items():
            for dyad in dyads:
                current_step += 1
                dyad_label = f"{dyad.get('id')} ({'-'.join(dyad.get('agents', []))})"
                print(f"[{current_step}/{total_steps}] Trial {trial_idx + 1} | Dyad: {dyad_label} | Item: {item_id}")

                # Step A: Conduct Dyadic Deliberation
                transcript = conduct_deliberation(
                    client=client,
                    config=config,
                    item=item,
                    dyad_id=dyad.get("id", "D1"),
                    agents=dyad.get("agents", []),
                    trial_index=trial_idx,
                    turns_per_item=turns_per_item
                )
                transcripts.append(transcript)

                # Step B: Administer Independent Secret Ballot
                summary_lines = [f"{t['speaker']}: {t['statement']}" for t in transcript["turns"]]
                transcript_summary = "\n".join(summary_lines)

                ballot_record = administer_dyad_ballot(
                    client=client,
                    config=config,
                    agents=dyad.get("agents", []),
                    item=item,
                    dyad_id=dyad.get("id", "D1"),
                    trial_index=trial_idx,
                    transcript_summary=transcript_summary,
                    seed=(seed + current_step * 17)
                )
                all_ballots.append(ballot_record)

    # 6. Psychometrics Analysis (CTT & IRT)
    print("📈 Fitting CTT and 2PL IRT Psychometric Models...")
    psychometric_results: PsychometricResults = analyze_experiment_psychometrics(
        ballots=all_ballots,
        item_ids=list(items.keys())
    )

    # 7. Persist All Experiment Artifacts (Guideline 6)
    print("💾 Saving experiment artifacts to indexed output directory...")

    # (a) Config Snapshot
    with open(exp_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # (b) Battery Items Snapshot
    items_out_dir = exp_dir / "items"
    items_out_dir.mkdir(parents=True, exist_ok=True)
    for item_path in config.get("items", []):
        src_p = Path(item_path)
        if src_p.exists():
            shutil.copy2(src_p, items_out_dir / src_p.name)
        else:
            for item_id, item_obj in items.items():
                if item_id in src_p.name or item_obj.get("item_id") in src_p.name:
                    with open(items_out_dir / src_p.name, "w", encoding="utf-8") as f:
                        json.dump(item_obj, f, indent=2)

    # (c) Deliberation Transcripts
    with open(exp_dir / "transcripts.json", "w", encoding="utf-8") as f:
        json.dump(transcripts, f, indent=2)

    # (d) Secret Ballots
    with open(exp_dir / "ballots.json", "w", encoding="utf-8") as f:
        json.dump(all_ballots, f, indent=2)

    # (e) CTT & IRT Metrics
    with open(exp_dir / "ctt_irt_metrics.json", "w", encoding="utf-8") as f:
        json.dump(psychometric_results, f, indent=2)

    # (f) Final Markdown Synthesis Report
    report_path = exp_dir / "final_report.md"
    generate_markdown_report(
        config=config,
        metrics=psychometric_results,
        items_data=items,
        output_path=str(report_path)
    )

    print(f"\n🎉 Simulation Run Completed Successfully!")
    print(f"📄 Report written to: {report_path}")
    return exp_dir


def main() -> None:
    """CLI argument parsing entry point.

    Accepts ONLY the path to the configuration JSON file.
    All experimental parameters are defined within the configuration JSON.
    """
    parser = argparse.ArgumentParser(
        description="Deliberative IRT Simulation: Evaluating Persona Competence & Policy Items via Item Response Theory"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="data/config.json",
        help="Path to master config JSON (default: data/config.json)"
    )

    args = parser.parse_args()

    execute_simulation_run(config_path=args.config)


if __name__ == "__main__":
    main()
