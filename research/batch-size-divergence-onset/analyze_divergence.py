#!/usr/bin/env python3
"""Deterministic local analysis of batch-size vs. token-divergence onset.

Runs in pure Python + NumPy (no PyTorch, transformers, or GPU required) from
committed per-prompt JSON artifacts in `runs/<prompt_id>.json`.

Usage:
    python3 research/batch-size-divergence-onset/analyze_divergence.py --preflight
    python3 research/batch-size-divergence-onset/analyze_divergence.py --analyze
    python3 research/batch-size-divergence-onset/analyze_divergence.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INPUTS_PATH = HERE / "inputs.json"
PREREG_PATH = HERE / "PREREGISTRATION.md"
RESULTS_PATH = HERE / "results.json"
RUNS_DIR = HERE / "runs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_inputs() -> dict:
    inputs = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    batch_sizes = inputs["conditions"]["batch_sizes"]
    if batch_sizes[0] != 1 or sorted(batch_sizes) != batch_sizes or len(set(batch_sizes)) != len(batch_sizes):
        raise ValueError("batch_sizes must start at 1 and be strictly increasing")
    if len(inputs["prompts"]) != 8:
        raise ValueError("expected 8 preregistered prompts")
    return inputs


def rankdata_average_ties(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = 0.5 * (i + j) + 1.0
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    return ranks


def spearman_rho(x: list[float], y: list[float]) -> float:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    if np.all(xa == xa[0]) or np.all(ya == ya[0]):
        return 0.0
    rx = rankdata_average_ties(xa)
    ry = rankdata_average_ties(ya)
    rx -= rx.mean()
    ry -= ry.mean()
    denom = float(np.sqrt(np.sum(rx ** 2) * np.sum(ry ** 2)))
    return float(np.sum(rx * ry) / denom) if denom > 0.0 else 0.0


def two_way_variance_decomposition(matrix: np.ndarray) -> dict:
    """Two-way additive ANOVA mean-effect variances on an (n_prompts, n_batches) array."""
    grand_mean = float(matrix.mean())
    prompt_means = matrix.mean(axis=1)
    batch_means = matrix.mean(axis=0)
    var_prompt = float(np.mean((prompt_means - grand_mean) ** 2))
    var_batch = float(np.mean((batch_means - grand_mean) ** 2))
    fitted = prompt_means[:, None] + batch_means[None, :] - grand_mean
    residual = matrix - fitted
    var_residual = float(np.mean(residual ** 2))
    var_total = float(np.mean((matrix - grand_mean) ** 2))
    ratio = (var_batch / var_prompt) if var_prompt > 0.0 else (float("inf") if var_batch > 0.0 else 0.0)
    return {
        "grand_mean_tokens": grand_mean,
        "var_prompt_main_effect": var_prompt,
        "var_batch_main_effect": var_batch,
        "var_interaction_residual": var_residual,
        "var_total": var_total,
        "prompt_share_of_total": (var_prompt / var_total) if var_total > 0.0 else 0.0,
        "batch_share_of_total": (var_batch / var_total) if var_total > 0.0 else 0.0,
        "residual_share_of_total": (var_residual / var_total) if var_total > 0.0 else 0.0,
        "batch_to_prompt_variance_ratio": ratio,
    }


def preflight_check(inputs: dict) -> dict:
    batch_sizes = inputs["conditions"]["batch_sizes"]
    multi_b = [b for b in batch_sizes if b >= 2]
    prompt_ids = [p["id"] for p in inputs["prompts"]]
    if len(set(prompt_ids)) != len(prompt_ids):
        raise ValueError("duplicate prompt IDs")
    return {
        "model_id": inputs["conditions"]["model_id"],
        "dtype": inputs["conditions"]["dtype"],
        "max_new_tokens": inputs["conditions"]["max_new_tokens"],
        "n_prompts": len(prompt_ids),
        "n_batch_sizes_total": len(batch_sizes),
        "n_multi_batch_sizes": len(multi_b),
        "batch_sizes": batch_sizes,
        "prompt_ids": prompt_ids,
        "decision": inputs["decision"],
    }


def first_mismatch_1indexed(seq_a: list[int], seq_b: list[int]) -> int | None:
    for idx, (ta, tb) in enumerate(zip(seq_a, seq_b, strict=True)):
        if ta != tb:
            return idx + 1
    return None


def build_results(inputs: dict, generated_at: str) -> dict:
    conditions = inputs["conditions"]
    decision = inputs["decision"]
    batch_sizes = conditions["batch_sizes"]
    multi_batches = [b for b in batch_sizes if b >= 2]
    max_tokens = int(conditions["max_new_tokens"])
    censored_val = int(conditions["censored_onset_value"])

    smoke_path = RUNS_DIR / "smoke_and_mm_check.json"
    if not smoke_path.is_file():
        raise FileNotFoundError(f"missing {smoke_path}")
    smoke_data = json.loads(smoke_path.read_text(encoding="utf-8"))
    run_artifacts = [{"path": repository_path(smoke_path), "sha256": sha256(smoke_path)}]

    env_path = RUNS_DIR / "environment_colab.json"
    if env_path.is_file():
        run_artifacts.append({"path": repository_path(env_path), "sha256": sha256(env_path)})

    prompt_summaries = {}
    onset_matrix_rows = []
    diverging_onset_matrix_rows = []
    within_prompt_ranges_diverging = []
    within_prompt_uncensored_ranges = []
    all_flip_margins = []
    all_nonflip_median_margins = []
    step1_logit_diffs_by_b = {str(b): [] for b in multi_batches}
    all_intra_batch_identical = True
    all_run_to_run_exact = True

    for p_spec in inputs["prompts"]:
        pid = p_spec["id"]
        p_path = RUNS_DIR / f"{pid}.json"
        if not p_path.is_file():
            raise FileNotFoundError(f"missing prompt run file: {p_path}")
        run_artifacts.append({"path": repository_path(p_path), "sha256": sha256(p_path)})
        pdata = json.loads(p_path.read_text(encoding="utf-8"))

        # Check run-to-run determinism gates (B=1 and B=32 repeated back-to-back)
        det = pdata["determinism_checks"]
        p_det_ok = all(
            item["token_mismatches"] == 0 and item["step1_logit_max_abs_diff"] == 0.0
            for item in det.values()
        )
        if not p_det_ok:
            all_run_to_run_exact = False

        b1_entry = pdata["batches"]["1"]
        b1_tokens = b1_entry["slot0_token_ids"]
        if len(b1_tokens) != max_tokens:
            raise ValueError(f"{pid} B=1 generated {len(b1_tokens)} tokens, expected {max_tokens}")

        b1_margins = [
            float(t1 - t2)
            for t1, t2 in zip(b1_entry["slot0_top1_logits"], b1_entry["slot0_top2_logits"], strict=True)
        ]

        unique_sequences = {tuple(b1_tokens): [1]}
        per_b = {}
        row_censored = []
        uncensored_onsets = []
        flip_steps_set = set()

        for b in multi_batches:
            b_entry = pdata["batches"][str(b)]
            b_tokens = b_entry["slot0_token_ids"]
            if len(b_tokens) != max_tokens:
                raise ValueError(f"{pid} B={b} generated {len(b_tokens)} tokens")
            seq_key = tuple(b_tokens)
            unique_sequences.setdefault(seq_key, []).append(b)

            if b_entry["intra_batch_unique_sequences"] != 1:
                all_intra_batch_identical = False

            onset = first_mismatch_1indexed(b1_tokens, b_tokens)
            censored_onset = onset if onset is not None else censored_val
            row_censored.append(float(censored_onset))
            if onset is not None:
                uncensored_onsets.append(onset)
                flip_steps_set.add(onset)

            s1_diff = float(b_entry["step1_logit_max_abs_diff_vs_b1"])
            step1_logit_diffs_by_b[str(b)].append(s1_diff)

            margin_at_onset = float(b1_margins[onset - 1]) if onset is not None else None
            per_b[str(b)] = {
                "diverged": onset is not None,
                "onset_token_1indexed": onset,
                "censored_onset_token": censored_onset,
                "step1_logit_max_abs_diff_vs_b1": s1_diff,
                "b1_top1_minus_top2_margin_at_onset": margin_at_onset,
                "intra_batch_unique_sequences": int(b_entry["intra_batch_unique_sequences"]),
                "divergence_snippet": b_entry.get("divergence_snippet"),
            }

        onset_matrix_rows.append(row_censored)
        diverged_any = len(uncensored_onsets) > 0

        for step_1idx in sorted(flip_steps_set):
            all_flip_margins.append(b1_margins[step_1idx - 1])
        nonflip_margins = [
            b1_margins[idx] for idx in range(max_tokens) if (idx + 1) not in flip_steps_set
        ]
        if nonflip_margins:
            all_nonflip_median_margins.append(float(np.median(nonflip_margins)))

        censored_range = float(max(row_censored) - min(row_censored))
        uncensored_range = (
            float(max(uncensored_onsets) - min(uncensored_onsets))
            if uncensored_onsets
            else 0.0
        )
        if diverged_any:
            diverging_onset_matrix_rows.append(row_censored)
            within_prompt_ranges_diverging.append(censored_range)
            within_prompt_uncensored_ranges.append(uncensored_range)

        rho_b = spearman_rho([float(b) for b in multi_batches], row_censored)

        # Group batch sizes into equivalence classes sharing identical 256-token completions
        equivalence_classes = [
            {"batch_sizes": bs_list, "matches_b1": (1 in bs_list)}
            for bs_list in unique_sequences.values()
        ]

        prompt_summaries[pid] = {
            "label": p_spec["label"],
            "prompt_text": p_spec["text"],
            "prompt_token_length": int(pdata["prompt_token_length"]),
            "determinism_passed": p_det_ok,
            "diverged_at_any_b": diverged_any,
            "n_diverging_batch_sizes": len(uncensored_onsets),
            "n_unique_completions_across_14_batches": len(unique_sequences),
            "equivalence_classes": equivalence_classes,
            "min_onset_token": min(uncensored_onsets) if uncensored_onsets else None,
            "max_onset_token_uncensored": max(uncensored_onsets) if uncensored_onsets else None,
            "within_prompt_censored_onset_range_tokens": censored_range,
            "within_prompt_uncensored_onset_range_tokens": uncensored_range,
            "spearman_rho_batch_vs_censored_onset": rho_b,
            "b1_min_margin": float(min(b1_margins)),
            "b1_median_margin": float(np.median(b1_margins)),
            "neighbor_content_control": pdata.get("neighbor_content_control"),
            "batches": per_b,
        }

    n_diverging_prompts = len(within_prompt_ranges_diverging)
    mm_ok = (
        float(smoke_data["torch_mm_fp32_max_abs_diff"]) > 0.0
        and float(smoke_data["torch_mm_bf16_max_abs_diff"]) > 0.0
        and bool(smoke_data["kv_loop_matches_hf_generate"])
    )
    signal_ok = n_diverging_prompts >= int(decision["min_diverging_prompts"])
    fidelity_passed = all_run_to_run_exact and mm_ok and signal_ok

    full_matrix = np.asarray(onset_matrix_rows, dtype=float)
    anova_all = two_way_variance_decomposition(full_matrix)
    anova_diverging = (
        two_way_variance_decomposition(np.asarray(diverging_onset_matrix_rows, dtype=float))
        if n_diverging_prompts >= 2
        else None
    )

    median_range_diverging = (
        float(np.median(within_prompt_ranges_diverging))
        if within_prompt_ranges_diverging
        else 0.0
    )
    median_uncensored_range = (
        float(np.median(within_prompt_uncensored_ranges))
        if within_prompt_uncensored_ranges
        else 0.0
    )
    var_ratio = float(anova_all["batch_to_prompt_variance_ratio"])

    non_flat_passed = median_range_diverging >= float(
        decision["min_median_within_prompt_onset_range_tokens"]
    )
    not_prompt_dominated_passed = var_ratio >= float(
        decision["min_batch_to_prompt_variance_ratio"]
    )

    if not fidelity_passed:
        verdict = "inconclusive"
        reason = "method-fidelity or minimum-signal gate failed"
    elif non_flat_passed and not_prompt_dominated_passed:
        verdict = "supported"
        reason = "divergence onset varied across B >= 2 and batch-size variance met the preregistered threshold relative to prompt variance"
    else:
        verdict = "falsified"
        reasons = []
        if not non_flat_passed:
            reasons.append("median within-prompt onset range across B >= 2 was below 5 tokens (flat/plateau in B)")
        if not not_prompt_dominated_passed:
            reasons.append("batch-to-prompt variance ratio was below 0.25 (dominated by prompt near-ties)")
        reason = "; ".join(reasons)

    # Aggregate curve across prompts by batch size B
    batch_curve = {}
    for col_idx, b in enumerate(multi_batches):
        col = full_matrix[:, col_idx]
        uncens = [float(v) for v in col if v <= max_tokens]
        s1_list = step1_logit_diffs_by_b[str(b)]
        batch_curve[str(b)] = {
            "n_prompts_diverged": len(uncens),
            "fraction_prompts_diverged": len(uncens) / len(inputs["prompts"]),
            "mean_censored_onset_tokens": float(np.mean(col)),
            "median_censored_onset_tokens": float(np.median(col)),
            "median_uncensored_onset_tokens": float(np.median(uncens)) if uncens else None,
            "mean_step1_logit_max_abs_diff": float(np.mean(s1_list)),
            "max_step1_logit_max_abs_diff": float(np.max(s1_list)),
        }

    unique_counts = [
        p["n_unique_completions_across_14_batches"] for p in prompt_summaries.values()
    ]

    return {
        "schema_version": 1,
        "experiment": inputs["experiment"],
        "generated_at": generated_at,
        "provenance": {
            "inputs": {"path": repository_path(INPUTS_PATH), "sha256": sha256(INPUTS_PATH)},
            "preregistration": {"path": repository_path(PREREG_PATH), "sha256": sha256(PREREG_PATH)},
            "run_artifacts": run_artifacts,
        },
        "protocol": {
            "conditions": conditions,
            "decision": decision,
        },
        "smoke_and_mm_check": smoke_data,
        "summary": {
            "n_prompts_total": len(inputs["prompts"]),
            "n_diverging_prompts": n_diverging_prompts,
            "median_within_prompt_censored_range_tokens": median_range_diverging,
            "median_within_prompt_uncensored_range_tokens": median_uncensored_range,
            "min_unique_completions_per_prompt": int(min(unique_counts)),
            "max_unique_completions_per_prompt": int(max(unique_counts)),
            "median_unique_completions_per_prompt": float(np.median(unique_counts)),
            "median_b1_margin_at_flip_steps": (
                float(np.median(all_flip_margins)) if all_flip_margins else None
            ),
            "max_b1_margin_at_flip_steps": (
                float(max(all_flip_margins)) if all_flip_margins else None
            ),
            "median_b1_margin_at_nonflip_steps": (
                float(np.median(all_nonflip_median_margins))
                if all_nonflip_median_margins
                else None
            ),
            "all_intra_batch_rows_identical": all_intra_batch_identical,
            "two_way_anova_all_prompts": anova_all,
            "two_way_anova_diverging_prompts": anova_diverging,
            "non_flat_criterion_passed": non_flat_passed,
            "not_prompt_dominated_criterion_passed": not_prompt_dominated_passed,
        },
        "batch_size_curve": batch_curve,
        "prompts": prompt_summaries,
        "fidelity": {
            "all_run_to_run_deterministic": all_run_to_run_exact,
            "matmul_noninvariance_and_kv_equivalence_verified": mm_ok,
            "minimum_signal_prompts_met": signal_ok,
            "passed": fidelity_passed,
        },
        "verdict": {
            "value": verdict,
            "reason": reason,
            "hypothesis_supported": verdict == "supported",
            "hypothesis_falsified": verdict == "falsified",
            "result_inconclusive": verdict == "inconclusive",
        },
    }


def rounded(value, significant: int = 10):
    if isinstance(value, bool) or not isinstance(value, float):
        if isinstance(value, dict):
            return {k: rounded(v, significant) for k, v in value.items()}
        if isinstance(value, list):
            return [rounded(v, significant) for v in value]
        return value
    if value == 0.0 or not math.isfinite(value):
        return value
    if abs(value) < 1.0e-12:
        return 0.0
    return float(f"{value:.{significant}g}")


def serialized(payload: dict) -> str:
    return json.dumps(rounded(payload), indent=2, sort_keys=False, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if sum((args.preflight, args.analyze, args.check)) > 1:
        parser.error("--preflight, --analyze, and --check are mutually exclusive")

    inputs = load_inputs()
    if args.preflight:
        print(serialized(preflight_check(inputs)), end="")
        return 0

    if args.check:
        if not RESULTS_PATH.is_file():
            raise FileNotFoundError(f"{RESULTS_PATH} does not exist yet")
        existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        expected = serialized(build_results(inputs, existing["generated_at"]))
        actual = RESULTS_PATH.read_text(encoding="utf-8")
        if expected != actual:
            print(f"{repository_path(RESULTS_PATH)} is stale", file=sys.stderr)
            return 1
        print(f"{repository_path(RESULTS_PATH)} is internally consistent")
        return 0

    generated_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    RESULTS_PATH.write_text(
        serialized(build_results(inputs, generated_at)), encoding="utf-8"
    )
    print(f"wrote {repository_path(RESULTS_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
