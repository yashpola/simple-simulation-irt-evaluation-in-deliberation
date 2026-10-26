"""Generates comprehensive Markdown report synthesizing CTT, IRT, and discourse findings.

Adheres to:
- Guideline 1: Built-in typing and TypedDict inputs.
- Guideline 2: Functional separation for report synthesis.
- Simplified benchmark observing latent deliberative competence across diverse citizen groups and policy items.
"""

from typing import Dict
from datetime import datetime
from src.schemas import MasterConfig, PolicyItem, PsychometricResults
from src.personas import get_persona_metadata


def generate_markdown_report(
    config: MasterConfig,
    metrics: PsychometricResults,
    items_data: Dict[str, PolicyItem],
    output_path: str
) -> str:
    """Compile final_report.md synthesizing deliberative psychometrics and governance insights."""
    ctt_data = metrics.get("ctt", {})
    irt_data = metrics.get("irt", {})
    dyad_thetas = metrics.get("dyad_theta", {})
    insights = metrics.get("insights", {})

    model_cfg = config.get("model_config", {})
    delib_cfg = config.get("deliberation_config", {})
    meta = config.get("experiment_metadata", {})

    report_lines = [
        "# Deliberative Item Response Theory (IRT) Benchmark Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Benchmark:** {meta.get('name', 'IRT Deliberation Benchmark')}  ",
        f"**Model:** `{model_cfg.get('agent_model', 'openai/gpt-oss-120b')}`  ",
        f"**Trials per Item:** {delib_cfg.get('trials_per_item', 5)}  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Core Insights",
        "",
        "This psychometric benchmark evaluates **latent deliberative capacity ($\\theta$)** across diverse citizen demographic dyads "
        "and measures **item difficulty ($b$)**, **item discrimination ($a$)**, and **distractor efficiency (DCR)** across standardized Singapore public policy dilemmas.",
        "",
        "### Key Empirical Findings:",
        f"- **Most Challenging Policy Dilemma**: Policy item `{insights.get('hardest_item', 'N/A')}` exhibited the highest intrinsic difficulty parameter ($b$).",
        f"- **Most Accessible Compromise**: Policy item `{insights.get('easiest_item', 'N/A')}` had the lowest difficulty parameter, proving most receptive to common ground.",
        f"- **Most Diagnostic Dilemma**: Policy item `{insights.get('most_discriminating_item', 'N/A')}` showed the highest discrimination parameter ($a$), reliably distinguishing high-deliberation dyads from vulnerable ones.",
        f"- **Most Vulnerable Citizen Dyad**: Dyad `{insights.get('lowest_competence_dyad', 'N/A')}` demonstrated the lowest baseline latent deliberative competence ($\\theta$).",
        f"- **Most Tempting Distractor Trap**: Option `{insights.get('most_tempting_distractor', 'N/A')}` was the most frequently chosen bad-faith heuristic across participants.",
        "",
        "---",
        "",
        "## 2. Deliberation & Psychometric Architecture",
        "",
        "```mermaid",
        "flowchart TD",
        "    subgraph Phase1 [\"1. Inputs & Configuration\"]",
        "        CFG[\"Master Config (config.json)\"]",
        "        DYADS[\"Citizen Personas & Dyads (D1, D2, D3)\"]",
        "        ITEMS[\"Standardized Policy Battery (Items 1 to 4)\"]",
        "        CFG --> DYADS & ITEMS",
        "    end",
        "",
        "    subgraph Phase2 [\"2. Deliberation Simulation\"]",
        "        DIALOGUE[\"Multi-Turn Dyadic Deliberation between Citizen Personas\"]",
        "    end",
        "",
        "    subgraph Phase3 [\"3. Secret Ballot Administration\"]",
        "        BALLOT[\"Randomized Secret Ballot\"]",
        "        KEY[\"Integrative Compromise (Option A)\"]",
        "        TRAPS[\"Cognitive Traps (Inertia, Zero-Sum, Scapegoating)\"]",
        "        BALLOT --> KEY & TRAPS",
        "    end",
        "",
        "    subgraph Phase4 [\"4. Psychometric Modeling\"]",
        "        CTT[\"Classical Test Theory (Difficulty p, Discrimination D, DCR)\"]",
        "        IRT[\"Item Response Theory (2PL: Ability theta, Difficulty b, Discrimination a)\"]",
        "    end",
        "",
        "    subgraph Phase5 [\"5. Indexed Output Artifacts (data/expXXX)\"]",
        "        REPORT[\"final_report.md (Synthesis & Mermaid Charts)\"]",
        "        JSONS[\"transcripts.json, ballots.json, ctt_irt_metrics.json\"]",
        "    end",
        "",
        "    Phase1 --> Phase2",
        "    Phase2 --> Phase3",
        "    Phase3 --> Phase4",
        "    Phase4 --> Phase5",
        "```",
        "",
        "---",
        "",
        "## 3. Standardized Policy Battery Psychometrics (CTT & IRT)",
        "",
        "| Item ID | Policy Topic | Consensus Rate ($p_i$) | IRT Difficulty ($b_i$) | Discrimination ($a_i$) | DCR (B: Inertia) | DCR (C: Zero-Sum) | DCR (D: Scapegoat) |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for item_id, item_info in items_data.items():
        title = item_info.get("title", item_id)
        short_title = title[:34] + ("..." if len(title) > 34 else "")

        c_info = ctt_data.get(item_id)
        i_info = irt_data.get(item_id)

        p_val: object = c_info["difficulty_p"] if c_info else "N/A"
        b_val: object = i_info["difficulty_b"] if i_info else "N/A"
        a_val: object = i_info["discrimination_a"] if i_info else "N/A"
        dcr_dict: Dict[str, float] = c_info["distractor_ratios"] if c_info else {}

        report_lines.append(
            f"| `{item_id}` | {short_title} | {p_val} | {b_val} | {a_val} | {dcr_dict.get('B', 0.0)} | {dcr_dict.get('C', 0.0)} | {dcr_dict.get('D', 0.0)} |"
        )

    report_lines.extend([
        "",
        "> [!NOTE]",
        "> **IRT Difficulty ($b_i$)**: Higher values indicate dilemmas that are intrinsically harder to resolve constructively.  ",
        "> **IRT Discrimination ($a_i$)**: Measures how effectively an item distinguishes high-competence from low-competence dyads.  ",
        "> **DCR (Distractor-to-Correct Ratio)**: Ratio of selections for that trap relative to the integrative compromise (Option A).",
        "",
        "---",
        "",
        "## 4. Latent Deliberative Ability Breakdown ($\\theta$)",
        "",
        "### 4.1 Dyadic Deliberative Competence (Consensus Requirement)",
        "Estimated collective latent competence $\\theta$ across citizen dyad configurations (an item is passed only when both participants reach consensus on Option A):",
        "",
        "| Dyad ID | Citizen Composition | Deliberative Dynamic | Collective Competence ($\\theta$) | Relative Ranking |",
        "| :--- | :--- | :--- | :---: | :---: |"
    ])

    dyad_metadata = {
        d.get("id"): (d.get("name", d.get("id")), d.get("dynamic", "Deliberative Dynamic"))
        for d in delib_cfg.get("dyads", [])
    }

    # Sort dyads by theta descending
    sorted_dyads = sorted(dyad_thetas.keys(), key=lambda k: dyad_thetas[k], reverse=True)
    rank = 1
    for d_id in sorted_dyads:
        th_val = dyad_thetas.get(d_id, 0.0)
        comp, dyn = dyad_metadata.get(d_id, ("Citizen Dyad", "Deliberative Group"))
        report_lines.append(f"| `{d_id}` | {comp} | {dyn} | {th_val} | #{rank} |")
        rank += 1

    # 4.2 Individual Persona Deliberative Competence
    ind_thetas = metrics.get("individual_theta", {})
    ind_endorse = metrics.get("individual_endorsement_rates", {})
    if ind_thetas:
        report_lines.extend([
            "",
            "### 4.2 Individual Persona Deliberative Competence",
            "Estimated latent ability $\\theta$ for each citizen persona based on independent secret ballots, measuring personal propensity to endorse integrative solutions irrespective of partner agreement:",
            "",
            "| Persona ID | Role Title | Option A Endorsement Rate | Latent Competence ($\\theta$) | Relative Ranking |",
            "| :--- | :--- | :---: | :---: | :---: |"
        ])
        sorted_personas = sorted(ind_thetas.keys(), key=lambda k: ind_thetas[k], reverse=True)
        p_rank = 1
        for p_id in sorted_personas:
            p_th = ind_thetas.get(p_id, 0.0)
            p_rate = f"{ind_endorse.get(p_id, 0.0) * 100:.1f}%"
            p_meta = get_persona_metadata(p_id)
            p_name = p_meta.get("name", p_id)
            report_lines.append(f"| `{p_id}` | {p_name} | {p_rate} | {p_th} | #{p_rank} |")
            p_rank += 1

    # 4.3 Partner Interaction Effects (Dyadic Conditioning)
    persona_by_dyad = metrics.get("persona_by_dyad_theta", {})
    if persona_by_dyad:
        report_lines.extend([
            "",
            "### 4.3 Partner Interaction Effects (Dyadic Conditioning)",
            "How each individual persona's latent competence shifts depending on conversational partner in the dyad:",
            "",
            "| Persona | Partner Dynamic in Dyad | Latent Competence ($\\theta$) | Observed Shift / Context |",
            "| :--- | :--- | :---: | :--- |"
        ])
        for p_id, d_map in sorted(persona_by_dyad.items()):
            p_meta = get_persona_metadata(p_id)
            p_name = p_meta.get("name", p_id)
            for d_id, th in sorted(d_map.items()):
                comp, dyn = dyad_metadata.get(d_id, (d_id, "Dyad"))
                report_lines.append(f"| {p_name} | `{d_id}` ({dyn}) | {th} | Paired in {comp} |")

    report_lines.extend([
        "",
        "---",
        "",
        "## 5. Cognitive Trap & Distractor Vulnerability Analysis",
        "",
        "The standardized assessment tests three distinct heuristic failure modes:",
        "1. **Option B (Status Quo Inertia Trap)**: Rigid refusal to adapt; demanding infinite subsidies without addressing structural change.",
        "2. **Option C (Technocratic Zero-Sum Trap)**: Aggressive efficiency-only policy that completely disregards human/community disruption.",
        "3. **Option D (External Scapegoating / Deflection Trap)**: Deflecting structural challenges onto foreign or elite scapegoats without a viable solution.",
        "",
        "### Average Distractor Efficiency Across All Dilemmas:",
    ])

    avg_dcr = insights.get("average_dcr_by_distractor", {})
    hardest_key = str(insights.get("hardest_item", ""))
    hardest_b: object = irt_data[hardest_key]["difficulty_b"] if hardest_key in irt_data else "N/A"

    report_lines.extend([
        f"- **Option B (Status Quo Inertia)**: Average DCR = `{avg_dcr.get('B', 0.0)}`",
        f"- **Option C (Technocratic Zero-Sum)**: Average DCR = `{avg_dcr.get('C', 0.0)}`",
        f"- **Option D (External Scapegoating)**: Average DCR = `{avg_dcr.get('D', 0.0)}`",
        "",
        "---",
        "",
        "## 6. Policy Governance Implications",
        "",
        f"1. **Prioritize Facilitation on Item `{insights.get('hardest_item', 'N/A')}`**: This dilemma exhibited the greatest resistance to compromise ($b = {hardest_b}$). Policymakers and deliberative moderators should provide extra contextual briefings and transition guarantees on this topic.",
        f"2. **Mitigate Vulnerability in Dyad `{insights.get('lowest_competence_dyad', 'N/A')}`**: This citizen grouping struggled most with constructive dialogue ($\\theta = {dyad_thetas.get(insights.get('lowest_competence_dyad', ''), 'N/A')}$). Structured perspective-taking exercises and active mediation should be targeted at this demographic pairing.",
        f"3. **Inoculate Against `{insights.get('most_tempting_distractor', 'N/A')}` Traps**: The highest distractor selection was observed for Option {insights.get('most_tempting_distractor', 'N/A')}, indicating that public discourse is most susceptible to this specific bad-faith heuristic.",
        "",
        "---",
        "*Report automatically generated by `deliberative-irt-simulation` psychometrics pipeline.*"
    ])

    report_content = "\n".join(report_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_content
