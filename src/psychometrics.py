"""Psychometric modeling engine: Classical Test Theory (CTT) and Item Response Theory (IRT).

Adheres to:
- Guideline 1: Strict typing using TypedDict schemas (CTTMetrics, IRTMetrics, PsychometricResults).
- Guideline 3: Single-responsibility mathematical modeling functions.
- Simplified single-benchmark modeling across items and diverse citizen groups.
"""

import math
from typing import Dict, List, Tuple, Any
import numpy as np
import numpy.typing as npt
from scipy.optimize import minimize  # pyright: ignore[reportMissingTypeStubs] # type: ignore[import-untyped]
from scipy.special import expit  # pyright: ignore[reportMissingTypeStubs] # type: ignore[import-untyped]

from src.schemas import (
    DyadBallotRecord,
    CTTMetrics,
    IRTMetrics,
    PsychometricResults
)


def compute_ctt_metrics(
    ballots: List[DyadBallotRecord],
    item_ids: List[str]
) -> Dict[str, CTTMetrics]:
    """Compute Classical Test Theory metrics:

    - Item Difficulty (p_i): consensus rate N_consensus / N_total
    - Distractor Efficiency / DCR_k: count(distractor_k) / count(integrative compromise)
    - Item Discrimination Index (D_27%): P_top27% - P_bottom27%
    """
    metrics: Dict[str, CTTMetrics] = {}
    if not ballots:
        return metrics

    # Session key: (dyad_id, trial_index)
    session_scores: Dict[Tuple[str, int], int] = {}
    session_item_passed: Dict[Tuple[str, int], Dict[str, int]] = {}

    for b in ballots:
        key = (b["dyad_id"], b["trial_index"])
        if key not in session_scores:
            session_scores[key] = 0
            session_item_passed[key] = {}
        pass_val = 1 if b["consensus_reached"] else 0
        session_scores[key] += pass_val
        session_item_passed[key][b["item_id"]] = pass_val

    sorted_sessions = sorted(session_scores.keys(), key=lambda k: session_scores[k], reverse=True)
    n_sessions = len(sorted_sessions)
    n_27 = max(1, int(math.ceil(0.27 * n_sessions)))

    top_group = set(sorted_sessions[:n_27])
    bottom_group = set(sorted_sessions[-n_27:])

    for item_id in item_ids:
        item_ballots = [b for b in ballots if b["item_id"] == item_id]
        total_sessions = len(item_ballots)
        if total_sessions == 0:
            continue

        n_consensus = sum(1 for b in item_ballots if b["consensus_reached"])
        p_val = n_consensus / total_sessions

        opt_counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
        for b in item_ballots:
            for vote in b["votes"].values():
                k = vote["selected_key"].upper()
                opt_counts[k] = opt_counts.get(k, 0) + 1

        correct_count = opt_counts.get("A", 0)
        dcr: Dict[str, float] = {}
        for distractor in ["B", "C", "D"]:
            cnt = opt_counts.get(distractor, 0)
            if correct_count > 0:
                dcr[distractor] = round(cnt / correct_count, 4)
            else:
                dcr[distractor] = float(cnt) if cnt > 0 else 0.0

        top_passes = sum(
            session_item_passed.get(s, {}).get(item_id, 0) for s in top_group
        )
        bottom_passes = sum(
            session_item_passed.get(s, {}).get(item_id, 0) for s in bottom_group
        )

        p_top = top_passes / len(top_group) if top_group else 0.0
        p_bottom = bottom_passes / len(bottom_group) if bottom_group else 0.0
        discrim_index = round(p_top - p_bottom, 4)

        ctt_metric: CTTMetrics = {
            "item_id": item_id,
            "difficulty_p": round(p_val, 4),
            "discrimination_index": discrim_index,
            "distractor_counts": opt_counts,
            "distractor_ratios": dcr
        }
        metrics[item_id] = ctt_metric

    return metrics


def build_response_matrix(
    ballots: List[DyadBallotRecord],
    item_ids: List[str]
) -> Tuple[npt.NDArray[np.float64], List[str], List[str]]:
    """Build binary response matrix Y of shape (N_sessions, N_items).

    Deliberative agent unit = unique dyad session (dyad_id, trial_index).
    Y[j, i] = 1 if consensus reached (both chose A), else 0.
    """
    sessions = sorted(list(set((b["dyad_id"], b["trial_index"]) for b in ballots)))
    session_names = [f"{d}_t{t}" for (d, t) in sessions]
    session_map = {s: idx for idx, s in enumerate(sessions)}
    item_map = {item_id: idx for idx, item_id in enumerate(item_ids)}

    Y: npt.NDArray[np.float64] = np.zeros((len(sessions), len(item_ids)), dtype=np.float64)

    for b in ballots:
        s_key = (b["dyad_id"], b["trial_index"])
        if s_key in session_map and b["item_id"] in item_map:
            s_idx = session_map[s_key]
            i_idx = item_map[b["item_id"]]
            Y[s_idx, i_idx] = 1.0 if b["consensus_reached"] else 0.0

    return Y, session_names, item_ids


def build_individual_response_matrix(
    ballots: List[DyadBallotRecord],
    item_ids: List[str]
) -> Tuple[npt.NDArray[np.float64], List[Tuple[str, str, int]], List[str]]:
    """Build binary response matrix Y_ind of shape (N_individual_agents, N_items).

    Deliberative agent unit = unique individual session (persona_id, dyad_id, trial_index).
    Y[j, i] = 1 if the agent chose the integrative compromise (is_correct=True), else 0.
    """
    examinees = sorted(list(set(
        (persona_id, b["dyad_id"], b["trial_index"])
        for b in ballots
        for persona_id in b["votes"].keys()
    )))
    examinee_map = {e: idx for idx, e in enumerate(examinees)}
    item_map = {item_id: idx for idx, item_id in enumerate(item_ids)}

    Y: npt.NDArray[np.float64] = np.zeros((len(examinees), len(item_ids)), dtype=np.float64)

    for b in ballots:
        dyad_id = b["dyad_id"]
        trial_idx = b["trial_index"]
        item_id = b["item_id"]
        if item_id not in item_map:
            continue
        i_idx = item_map[item_id]

        for persona_id, vote in b["votes"].items():
            e_key = (persona_id, dyad_id, trial_idx)
            if e_key in examinee_map:
                e_idx = examinee_map[e_key]
                Y[e_idx, i_idx] = 1.0 if vote.get("is_correct", False) else 0.0

    return Y, examinees, item_ids


def fit_irt_2pl(
    Y: npt.NDArray[np.float64],
    regularization_theta: float = 0.5,
    regularization_b: float = 0.5,
    regularization_a: float = 0.5,
) -> Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Fit 2-Parameter Logistic (2PL) IRT Model via Regularized Maximum Likelihood.

    Model:
    P(Y_ji = 1 | theta_j, a_i, b_i) = 1 / (1 + exp(-a_i * (theta_j - b_i)))
    """
    n_examinees, n_items = Y.shape
    if n_examinees == 0 or n_items == 0:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty

    p_items: npt.NDArray[np.float64] = np.clip(np.mean(Y, axis=0), 0.05, 0.95)
    b_init: npt.NDArray[np.float64] = -np.log(p_items / (1.0 - p_items))
    a_init: npt.NDArray[np.float64] = np.ones(n_items, dtype=np.float64)

    p_examinees: npt.NDArray[np.float64] = np.clip(np.mean(Y, axis=1), 0.05, 0.95)
    theta_init: npt.NDArray[np.float64] = np.log(p_examinees / (1.0 - p_examinees))

    x0: npt.NDArray[np.float64] = np.concatenate([theta_init, a_init, b_init])

    def neg_log_likelihood(params: npt.NDArray[np.float64]) -> float:
        theta = params[:n_examinees]
        a = params[n_examinees:n_examinees + n_items]
        b = params[n_examinees + n_items:]

        diff = theta[:, np.newaxis] - b[np.newaxis, :]
        logits = a[np.newaxis, :] * diff

        p_mat: npt.NDArray[np.float64] = expit(logits)
        eps = 1e-9
        p_mat = np.clip(p_mat, eps, 1.0 - eps)

        log_lik = float(np.sum(Y * np.log(p_mat) + (1.0 - Y) * np.log(1.0 - p_mat)))

        prior_theta = 0.5 * regularization_theta * float(np.sum(theta ** 2))
        prior_b = 0.5 * regularization_b * float(np.sum(b ** 2))
        prior_a = 0.5 * regularization_a * float(np.sum((a - 1.0) ** 2))

        return -(log_lik - prior_theta - prior_b - prior_a)

    bounds: List[Tuple[float, float]] = []
    for _ in range(n_examinees):
        bounds.append((-4.0, 4.0))
    for _ in range(n_items):
        bounds.append((0.1, 4.0))
    for _ in range(n_items):
        bounds.append((-4.0, 4.0))

    res: Any = minimize(  # pyright: ignore[reportUnknownVariableType]
        neg_log_likelihood,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 500, "ftol": 1e-6}
    )

    opt_params: npt.NDArray[np.float64] = np.asarray(res.x, dtype=np.float64)  # pyright: ignore[reportUnknownMemberType]
    theta_est: npt.NDArray[np.float64] = opt_params[:n_examinees]
    a_est: npt.NDArray[np.float64] = opt_params[n_examinees:n_examinees + n_items]
    b_est: npt.NDArray[np.float64] = opt_params[n_examinees + n_items:]

    return theta_est, a_est, b_est


def fit_irt_1pl(
    Y: npt.NDArray[np.float64],
    regularization_theta: float = 0.5,
    regularization_b: float = 0.5,
) -> Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Fit 1-Parameter Logistic (Rasch) IRT Model where a_i = 1 for all items."""
    n_examinees, n_items = Y.shape
    if n_examinees == 0 or n_items == 0:
        empty = np.array([], dtype=np.float64)
        return empty, empty

    p_items: npt.NDArray[np.float64] = np.clip(np.mean(Y, axis=0), 0.05, 0.95)
    b_init: npt.NDArray[np.float64] = -np.log(p_items / (1.0 - p_items))
    p_examinees: npt.NDArray[np.float64] = np.clip(np.mean(Y, axis=1), 0.05, 0.95)
    theta_init: npt.NDArray[np.float64] = np.log(p_examinees / (1.0 - p_examinees))

    x0: npt.NDArray[np.float64] = np.concatenate([theta_init, b_init])

    def neg_log_likelihood(params: npt.NDArray[np.float64]) -> float:
        theta = params[:n_examinees]
        b = params[n_examinees:]

        diff = theta[:, np.newaxis] - b[np.newaxis, :]
        p_mat: npt.NDArray[np.float64] = expit(diff)
        eps = 1e-9
        p_mat = np.clip(p_mat, eps, 1.0 - eps)

        log_lik = float(np.sum(Y * np.log(p_mat) + (1.0 - Y) * np.log(1.0 - p_mat)))
        prior_theta = 0.5 * regularization_theta * float(np.sum(theta ** 2))
        prior_b = 0.5 * regularization_b * float(np.sum(b ** 2))

        return -(log_lik - prior_theta - prior_b)

    bounds: List[Tuple[float, float]] = [(-4.0, 4.0)] * (n_examinees + n_items)
    res: Any = minimize(  # pyright: ignore[reportUnknownVariableType]
        neg_log_likelihood,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 400, "ftol": 1e-6}
    )

    opt_params: npt.NDArray[np.float64] = np.asarray(res.x, dtype=np.float64)  # pyright: ignore[reportUnknownMemberType]
    theta_est: npt.NDArray[np.float64] = opt_params[:n_examinees]
    b_est: npt.NDArray[np.float64] = opt_params[n_examinees:]

    return theta_est, b_est


def analyze_experiment_psychometrics(
    ballots: List[DyadBallotRecord],
    item_ids: List[str]
) -> PsychometricResults:
    """Benchmark analysis estimating item parameters (b_i, a_i), CTT metrics, and group abilities (theta)."""
    # 1. CTT Metrics
    ctt_metrics = compute_ctt_metrics(ballots, item_ids)

    # 2. IRT Calibration (2PL)
    Y, sessions, _ = build_response_matrix(ballots, item_ids)
    theta_est, a_est, b_est = fit_irt_2pl(Y)

    # Map deliberative agents to dyad group
    dyad_theta_map: Dict[str, List[float]] = {}
    for sess_name, th in zip(sessions, theta_est):
        parts = sess_name.split("_")
        dyad_id = parts[0]
        dyad_theta_map.setdefault(dyad_id, []).append(float(th))

    mean_dyad_thetas = {
        d_id: round(float(np.mean(vals)), 4)
        for d_id, vals in dyad_theta_map.items()
    }

    irt_items: Dict[str, IRTMetrics] = {}
    for idx, i_id in enumerate(item_ids):
        irt_items[i_id] = {
            "item_id": i_id,
            "difficulty_b": round(float(b_est[idx]), 4) if len(b_est) > idx else 0.0,
            "discrimination_a": round(float(a_est[idx]), 4) if len(a_est) > idx else 1.0,
        }

    # 2b. Individual IRT Calibration (2PL)
    Y_ind, ind_examinees, _ = build_individual_response_matrix(ballots, item_ids)
    ind_thetas, _, _ = fit_irt_2pl(Y_ind)

    persona_thetas_map: Dict[str, List[float]] = {}
    persona_by_dyad_map: Dict[str, Dict[str, List[float]]] = {}
    persona_success_map: Dict[str, List[int]] = {}

    for (p_id, d_id, _), th in zip(ind_examinees, ind_thetas):
        persona_thetas_map.setdefault(p_id, []).append(float(th))
        persona_by_dyad_map.setdefault(p_id, {}).setdefault(d_id, []).append(float(th))

    for b in ballots:
        for p_id, v in b["votes"].items():
            persona_success_map.setdefault(p_id, []).append(1 if v.get("is_correct") else 0)

    mean_individual_thetas = {
        p_id: round(float(np.mean(vals)), 4)
        for p_id, vals in persona_thetas_map.items()
    }

    mean_persona_by_dyad = {
        p_id: {d_id: round(float(np.mean(vals)), 4) for d_id, vals in d_dict.items()}
        for p_id, d_dict in persona_by_dyad_map.items()
    }

    individual_success_rates = {
        p_id: round(float(np.mean(vals)), 4)
        for p_id, vals in persona_success_map.items()
    }

    # 3. Governance Insights & Ranking
    hardest_item = max(irt_items.keys(), key=lambda k: irt_items[k]["difficulty_b"]) if irt_items else "N/A"
    easiest_item = min(irt_items.keys(), key=lambda k: irt_items[k]["difficulty_b"]) if irt_items else "N/A"
    most_discriminating = max(irt_items.keys(), key=lambda k: irt_items[k]["discrimination_a"]) if irt_items else "N/A"

    lowest_dyad = min(mean_dyad_thetas.keys(), key=lambda k: mean_dyad_thetas[k]) if mean_dyad_thetas else "N/A"
    highest_dyad = max(mean_dyad_thetas.keys(), key=lambda k: mean_dyad_thetas[k]) if mean_dyad_thetas else "N/A"

    # Overall DCR across distractors
    avg_dcr: Dict[str, float] = {}
    for d_key in ["B", "C", "D"]:
        vals = [m["distractor_ratios"].get(d_key, 0.0) for m in ctt_metrics.values()]
        avg_dcr[d_key] = round(float(np.mean(vals)), 4) if vals else 0.0

    most_tempting_trap = max(avg_dcr.keys(), key=lambda k: avg_dcr[k]) if avg_dcr else "N/A"

    psych_results: PsychometricResults = {
        "ctt": ctt_metrics,
        "irt": {
            "items": irt_items,
            "deliberators": {
                "dyad_theta": mean_dyad_thetas,
                "individual_theta": mean_individual_thetas,
                "persona_by_dyad_theta": mean_persona_by_dyad,
            },
        },
        "individual_success_rates": individual_success_rates,
        "insights": {
            "hardest_item": hardest_item,
            "easiest_item": easiest_item,
            "most_discriminating_item": most_discriminating,
            "lowest_competence_dyad": lowest_dyad,
            "highest_competence_dyad": highest_dyad,
            "average_dcr_by_distractor": avg_dcr,
            "most_tempting_distractor": most_tempting_trap
        }
    }
    return psych_results
