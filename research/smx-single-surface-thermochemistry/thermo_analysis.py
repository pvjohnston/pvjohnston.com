#!/usr/bin/env python3
"""Deterministic normal-mode, RRHO / mRRHO-50, and verdict analysis for SMX.

Runs in pure Python + NumPy (no PySCF or GPU required) from the committed
Cartesian Hessians and optimized geometries in `runs/<A..D>/dft_result.json`.

Usage:
    python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --preflight
    python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --analyze
    python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INPUTS_PATH = HERE / "inputs.json"
PREREG_PATH = HERE / "PREREGISTRATION.md"
RESULTS_PATH = HERE / "results.json"
RUNS_DIR = HERE / "runs"
CONFORMER_NAMES = ("A", "B", "C", "D")
ARM_NAMES = ("rrho", "mrrho50")


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
    if tuple(inputs["conformers"]) != CONFORMER_NAMES:
        raise ValueError(f"conformers must be ordered {CONFORMER_NAMES}")
    if tuple(inputs["thermochemistry_arms"]) != ARM_NAMES:
        raise ValueError(f"arms must be ordered {ARM_NAMES}")
    orders = {
        tuple(atom[0] for atom in spec["atoms"])
        for spec in inputs["conformers"].values()
    }
    if len(orders) != 1 or len(next(iter(orders))) != 28:
        raise ValueError("all four SMX conformers must share one 28-atom ordering")
    return inputs


def boltzmann_populations(
    energies_hartree: dict[str, float],
    temperature_k: float,
    boltzmann_hartree_per_k: float,
) -> dict[str, float]:
    minimum = min(energies_hartree.values())
    weights = {
        name: math.exp(-(energy - minimum) / (boltzmann_hartree_per_k * temperature_k))
        for name, energy in energies_hartree.items()
    }
    total = sum(weights.values())
    return {name: weight / total for name, weight in weights.items()}


def effective_count(populations: dict[str, float]) -> float:
    return 1.0 / sum(value * value for value in populations.values())


def kabsch_rmsd(
    elements: list[str],
    coords_a: list[list[float]] | np.ndarray,
    coords_b: list[list[float]] | np.ndarray,
) -> float:
    heavy = np.asarray([el != "H" for el in elements], dtype=bool)
    a = np.asarray(coords_a, dtype=float)[heavy]
    b = np.asarray(coords_b, dtype=float)[heavy]
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    cov = a.T @ b
    left, _, right_t = np.linalg.svd(cov)
    sign = -1.0 if np.linalg.det(left @ right_t) < 0.0 else 1.0
    rot = left @ np.diag([1.0, 1.0, sign]) @ right_t
    aligned = a @ rot
    return float(np.sqrt(np.mean(np.sum((aligned - b) ** 2, axis=1))))


def harmonic_frequencies_from_hessian(
    coords_angstrom: np.ndarray,
    masses_amu: np.ndarray,
    hessian_3n_eh_bohr2: np.ndarray,
    constants: dict,
) -> list[float]:
    """Project out 3 translations and 3 rotations and return 3N-6 frequencies in cm^-1."""
    natm = len(masses_amu)
    coords_bohr = np.asarray(coords_angstrom, dtype=float) / constants["bohr_to_angstrom"]
    masses = np.asarray(masses_amu, dtype=float)
    hess = 0.5 * (hessian_3n_eh_bohr2 + hessian_3n_eh_bohr2.T)

    sqrt_m = np.repeat(np.sqrt(masses), 3)
    mw_hess = hess / np.outer(sqrt_m, sqrt_m)

    total_mass = float(np.sum(masses))
    com = np.sum(masses[:, None] * coords_bohr, axis=0) / total_mass
    rel = coords_bohr - com

    tr_vectors = []
    for axis in range(3):
        vec = np.zeros((natm, 3), dtype=float)
        vec[:, axis] = np.sqrt(masses)
        tr_vectors.append(vec.reshape(-1))
    unit_axes = np.eye(3, dtype=float)
    for axis in range(3):
        rot_disp = np.cross(unit_axes[axis], rel) * np.sqrt(masses)[:, None]
        tr_vectors.append(rot_disp.reshape(-1))

    tr_mat = np.column_stack(tr_vectors)
    u_tr, s_tr, _ = np.linalg.svd(tr_mat, full_matrices=True)
    n_tr = int(np.sum(s_tr > 1.0e-6))
    if n_tr != 6:
        raise ValueError(f"expected 6 translation/rotation modes for nonlinear SMX, got {n_tr}")
    vib_basis = u_tr[:, n_tr:]  # shape (3N, 3N - 6)

    vib_hess = 0.5 * (vib_basis.T @ mw_hess @ vib_basis + (vib_basis.T @ mw_hess @ vib_basis).T)
    eigvals = np.linalg.eigvalsh(vib_hess)

    conv = constants["hartree_to_j"] / (
        (constants["bohr_to_m"] ** 2) * constants["amu_to_kg"]
    )
    two_pi_c = 2.0 * math.pi * constants["speed_of_light_cm_s"]
    freqs_cm = [
        float(math.copysign(math.sqrt(abs(val) * conv) / two_pi_c, val))
        for val in eigvals
    ]
    freqs_cm.sort()
    return freqs_cm


def compute_thermo_from_modes(
    coords_angstrom: np.ndarray,
    masses_amu: np.ndarray,
    frequencies_cm: list[float],
    conditions: dict,
    constants: dict,
    rotor_cutoff_cm: float,
) -> dict:
    """Compute 298.15 K RRHO or Grimme-2012 mRRHO thermochemistry in Hartree."""
    t_k = float(conditions["temperature_k"])
    p_pa = float(conditions["pressure_pa"])
    sigma_r = float(conditions["rotational_symmetry_number"])
    scale = float(conditions["frequency_scale"])
    imag_thr = float(conditions["imaginary_threshold_cm"])
    b_av = float(conditions["grimme_b_av_kg_m2"])
    alpha = int(conditions["grimme_alpha"])

    h = constants["planck_j_s"]
    hbar = h / (2.0 * math.pi)
    kb = constants["boltzmann_j_per_k"]
    c_cm = constants["speed_of_light_cm_s"]
    eh_j = constants["hartree_to_j"]
    amu_kg = constants["amu_to_kg"]

    masses = np.asarray(masses_amu, dtype=float)
    coords_m = np.asarray(coords_angstrom, dtype=float) * 1.0e-10
    total_mass_kg = float(np.sum(masses)) * amu_kg
    com_m = np.sum((masses * amu_kg)[:, None] * coords_m, axis=0) / total_mass_kg
    rel_m = coords_m - com_m

    r2 = np.sum(rel_m ** 2, axis=1)
    inertia = np.zeros((3, 3), dtype=float)
    for idx in range(len(masses)):
        m_i = masses[idx] * amu_kg
        inertia += m_i * (r2[idx] * np.eye(3) - np.outer(rel_m[idx], rel_m[idx]))
    i_vals = np.linalg.eigvalsh(inertia)
    if np.any(i_vals <= 0.0):
        raise ValueError(f"non-positive principal moments of inertia: {i_vals}")

    q_trans_over_n = ((2.0 * math.pi * total_mass_kg * kb * t_k) / (h ** 2)) ** 1.5 * (
        kb * t_k / p_pa
    )
    u_trans_j = 1.5 * kb * t_k
    s_trans_j_k = kb * (2.5 + math.log(q_trans_over_n))

    theta_rot = (hbar ** 2) / (2.0 * i_vals * kb)
    q_rot = (math.sqrt(math.pi) / sigma_r) * math.sqrt(
        (t_k ** 3) / float(np.prod(theta_rot))
    )
    u_rot_j = 1.5 * kb * t_k
    s_rot_j_k = kb * (1.5 + math.log(q_rot))

    scaled = [freq * scale for freq in frequencies_cm]
    below_imag_thr = [freq for freq in scaled if freq < imag_thr]
    inverted_soft_modes = [freq for freq in scaled if imag_thr <= freq < 0.0]

    eff_freqs = []
    for freq in scaled:
        if freq < imag_thr:
            continue
        eff_freqs.append(abs(freq))

    zpe_j = 0.0
    u_vib_j = 0.0
    s_vib_j_k = 0.0
    for nu_cm in eff_freqs:
        if nu_cm <= 0.0:
            continue
        hv = h * c_cm * nu_cm
        x = hv / (kb * t_k)
        zpe_j += 0.5 * hv
        exp_x = math.exp(x) if x < 500.0 else float("inf")
        u_vib_j += hv / (exp_x - 1.0) if math.isfinite(exp_x) else 0.0
        s_ho = (
            kb * (x / (exp_x - 1.0) - math.log(1.0 - math.exp(-x)))
            if x < 500.0
            else 0.0
        )
        if rotor_cutoff_cm > 0.0:
            weight = 1.0 / (1.0 + (rotor_cutoff_cm / nu_cm) ** alpha)
            mu = h / (8.0 * (math.pi ** 2) * c_cm * nu_cm)
            mu_eff = (mu * b_av) / (mu + b_av)
            s_fr = kb * (
                0.5
                + math.log(
                    math.sqrt((8.0 * (math.pi ** 3) * mu_eff * kb * t_k) / (h ** 2))
                )
            )
            s_vib_j_k += weight * s_ho + (1.0 - weight) * s_fr
        else:
            s_vib_j_k += s_ho

    h_corr_j = zpe_j + u_trans_j + u_rot_j + u_vib_j + kb * t_k
    s_tot_j_k = s_trans_j_k + s_rot_j_k + s_vib_j_k
    g_corr_j = h_corr_j - t_k * s_tot_j_k

    return {
        "rotor_cutoff_cm": rotor_cutoff_cm,
        "zpe_hartree": zpe_j / eh_j,
        "enthalpy_correction_hartree": h_corr_j / eh_j,
        "entropy_total_eh_per_k": s_tot_j_k / eh_j,
        "ts_total_hartree": (t_k * s_tot_j_k) / eh_j,
        "ts_vibrational_hartree": (t_k * s_vib_j_k) / eh_j,
        "thermochemical_correction_hartree": g_corr_j / eh_j,
        "imaginary_modes_below_threshold_cm": below_imag_thr,
        "n_imaginary_modes_below_threshold": len(below_imag_thr),
        "soft_inverted_modes_cm": inverted_soft_modes,
    }


def preflight_check(inputs: dict) -> dict:
    """Validate source baseline and cross-check mRRHO math against Post 1 xTB output."""
    t_k = inputs["conditions"]["temperature_k"]
    kb_eh = inputs["constants"]["boltzmann_hartree_per_k"]
    source_energies = {
        name: spec["source_electronic_energy_hartree"]
        for name, spec in inputs["conformers"].items()
    }
    source_pops = boltzmann_populations(source_energies, t_k, kb_eh)
    max_diff_pp = max(
        abs(100.0 * source_pops[name] - spec["source_reported_population_percent"])
        for name, spec in inputs["conformers"].items()
    )
    if max_diff_pp > 0.15:
        raise ValueError(f"source Boltzmann baseline mismatch: {max_diff_pp:.3f} pp")

    xtb_rrho_log = ROOT / "research/smx-conformer-thermochemistry/runs/A/rrho/xtb.out"
    xtb_mrrho_log = ROOT / "research/smx-conformer-thermochemistry/runs/A/mrrho50/xtb.out"
    xtb_geom = ROOT / "research/smx-conformer-thermochemistry/runs/A/rrho/xtbopt.xyz"
    xtb_cross_check = None
    if xtb_rrho_log.is_file() and xtb_mrrho_log.is_file() and xtb_geom.is_file():
        lines = xtb_geom.read_text(encoding="utf-8").splitlines()
        natm = int(lines[0].strip())
        symbols = [ln.split()[0] for ln in lines[2 : 2 + natm]]
        coords = np.asarray(
            [[float(x) for x in ln.split()[1:4]] for ln in lines[2 : 2 + natm]],
            dtype=float,
        )
        masses = np.asarray(
            [inputs["standard_atomic_masses_amu"][el] for el in symbols], dtype=float
        )
        rrho_txt = xtb_rrho_log.read_text(encoding="utf-8", errors="replace")
        mrrho_txt = xtb_mrrho_log.read_text(encoding="utf-8", errors="replace")
        sec = rrho_txt[rrho_txt.rfind("|               Frequency Printout") :]
        sec = sec[: sec.find("reduced masses")]
        freqs = []
        for ln in sec.splitlines():
            if "eigval :" in ln:
                freqs.extend(
                    float(v)
                    for v in re.findall(r"[-+]?(?:\d+\.\d+|\d+)", ln.split("eigval :", 1)[1])
                )
        freqs_pos = [f for f in freqs if f > 0.01]
        our_rrho = compute_thermo_from_modes(
            coords, masses, freqs_pos, inputs["conditions"], inputs["constants"], 0.0
        )
        our_mrrho = compute_thermo_from_modes(
            coords, masses, freqs_pos, inputs["conditions"], inputs["constants"], 50.0
        )
        xtb_g_rrho = float(
            re.findall(r":: G\(RRHO\) contrib\.\s+(-?\d+\.\d+)\s+Eh", rrho_txt)[-1]
        )
        xtb_g_mrrho = float(
            re.findall(r":: G\(RRHO\) contrib\.\s+(-?\d+\.\d+)\s+Eh", mrrho_txt)[-1]
        )
        our_mrrho_shift_eh = (
            our_mrrho["thermochemical_correction_hartree"]
            - our_rrho["thermochemical_correction_hartree"]
        )
        xtb_mrrho_shift_eh = xtb_g_mrrho - xtb_g_rrho
        xtb_cross_check = {
            "n_vibrational_modes": len(freqs_pos),
            "our_rrho_g_corr_eh": our_rrho["thermochemical_correction_hartree"],
            "xtb_rrho_g_corr_eh": xtb_g_rrho,
            "rrho_abs_diff_eh": abs(
                our_rrho["thermochemical_correction_hartree"] - xtb_g_rrho
            ),
            "our_mrrho50_minus_rrho_eh": our_mrrho_shift_eh,
            "xtb_mrrho50_minus_rrho_eh": xtb_mrrho_shift_eh,
            "mrrho50_shift_diff_kj_mol": abs(our_mrrho_shift_eh - xtb_mrrho_shift_eh)
            * inputs["constants"]["hartree_to_kj_per_mol"],
        }

    return {
        "source_electronic_energies_hartree": source_energies,
        "source_electronic_populations": source_pops,
        "source_effective_conformer_count": effective_count(source_pops),
        "source_max_rounding_diff_pp": max_diff_pp,
        "xtb_thermo_cross_check": xtb_cross_check,
    }


def evaluate_distribution(
    energies_eh: dict[str, float],
    baseline_pops: dict[str, float],
    inputs: dict,
) -> dict:
    t_k = inputs["conditions"]["temperature_k"]
    kb_eh = inputs["constants"]["boltzmann_hartree_per_k"]
    h2kj = inputs["constants"]["hartree_to_kj_per_mol"]
    decision = inputs["decision"]

    min_e = min(energies_eh.values())
    rel_kj = {name: (energies_eh[name] - min_e) * h2kj for name in CONFORMER_NAMES}
    pops = boltzmann_populations(energies_eh, t_k, kb_eh)
    shifts_pp = {
        name: 100.0 * (pops[name] - baseline_pops[name]) for name in CONFORMER_NAMES
    }
    max_shift_pp = max(abs(val) for val in shifts_pp.values())
    n_eff = effective_count(pops)

    shift_concentrated = (
        max_shift_pp >= decision["concentration_min_population_shift_pp"]
    )
    count_concentrated = (
        n_eff < decision["concentration_max_effective_conformer_count"]
    )
    concentrated = shift_concentrated or count_concentrated
    lowest = min(CONFORMER_NAMES, key=lambda k: energies_eh[k])

    return {
        "energies_hartree": energies_eh,
        "relative_energies_kj_per_mol": rel_kj,
        "span_kj_per_mol": max(rel_kj.values()),
        "lowest_conformer": lowest,
        "populations": pops,
        "population_shifts_from_baseline_pp": shifts_pp,
        "maximum_absolute_population_shift_pp": max_shift_pp,
        "effective_conformer_count": n_eff,
        "shift_concentration_criterion_met": shift_concentrated,
        "count_concentration_criterion_met": count_concentrated,
        "concentration_criterion_met": concentrated,
    }


def build_results(inputs: dict, generated_at: str) -> dict:
    preflight = preflight_check(inputs)
    conditions = inputs["conditions"]
    constants = inputs["constants"]
    decision = inputs["decision"]

    elements = [atom[0] for atom in inputs["conformers"]["A"]["atoms"]]
    runs_summary = {}
    run_artifacts = []
    run_checks = {}

    for name in CONFORMER_NAMES:
        dft_json_path = RUNS_DIR / name / "dft_result.json"
        opt_xyz_path = RUNS_DIR / name / "opt.xyz"
        if not dft_json_path.is_file() or not opt_xyz_path.is_file():
            raise FileNotFoundError(
                f"missing completed GPU DFT artifacts for conformer {name} in {RUNS_DIR / name}"
            )
        raw = json.loads(dft_json_path.read_text(encoding="utf-8"))
        coords_opt = np.asarray(raw["optimized_coordinates_angstrom"], dtype=float)
        masses = np.asarray(raw["atom_masses_amu"], dtype=float)
        hess_3n = np.asarray(raw["hessian_3n_hartree_per_bohr2"], dtype=float)

        freqs_cm = harmonic_frequencies_from_hessian(
            coords_opt, masses, hess_3n, constants
        )
        arm_thermo = {
            arm: compute_thermo_from_modes(
                coords_opt,
                masses,
                freqs_cm,
                conditions,
                constants,
                inputs["thermochemistry_arms"][arm]["rotor_cutoff_cm"],
            )
            for arm in ARM_NAMES
        }

        pyscf_g_tot = raw.get("pyscf_rrho_g_tot_hartree")
        our_rrho_g_tot = (
            float(raw["electronic_energy_hartree"])
            + arm_thermo["rrho"]["thermochemical_correction_hartree"]
        )
        pyscf_thermo_diff = (
            abs(our_rrho_g_tot - float(pyscf_g_tot))
            if pyscf_g_tot is not None
            else 0.0
        )

        start_coords = np.asarray(
            [atom[1:4] for atom in inputs["conformers"][name]["atoms"]], dtype=float
        )
        start_opt_rmsd = kabsch_rmsd(elements, start_coords, coords_opt)

        grad_rms = float(raw["post_opt_grad_rms_eh_bohr"])
        grad_max = float(raw["post_opt_grad_max_eh_bohr"])
        normal = bool(
            raw.get("opt_converged")
            and raw.get("final_scf_converged")
            and raw.get("hessian_completed")
        )

        run_checks[name] = {
            "normal_convergence": normal,
            "post_opt_grad_rms_ok": grad_rms <= decision["max_post_opt_grad_rms_eh_bohr"],
            "post_opt_grad_max_ok": grad_max <= decision["max_post_opt_grad_max_eh_bohr"],
            "no_modes_below_imaginary_threshold": (
                arm_thermo["rrho"]["n_imaginary_modes_below_threshold"] == 0
            ),
            "pyscf_thermo_agreement_ok": (
                pyscf_thermo_diff <= decision["max_pyscf_thermo_discrepancy_eh"]
            ),
            "start_to_opt_rmsd_ok": (
                start_opt_rmsd <= decision["start_to_opt_max_heavy_atom_rmsd_angstrom"]
            ),
        }

        run_artifacts.extend(
            [
                {"path": repository_path(dft_json_path), "sha256": sha256(dft_json_path)},
                {"path": repository_path(opt_xyz_path), "sha256": sha256(opt_xyz_path)},
            ]
        )

        runs_summary[name] = {
            "electronic_energy_hartree": float(raw["electronic_energy_hartree"]),
            "post_opt_grad_rms_eh_bohr": grad_rms,
            "post_opt_grad_max_eh_bohr": grad_max,
            "start_to_opt_heavy_atom_rmsd_angstrom": start_opt_rmsd,
            "lowest_six_frequencies_cm": freqs_cm[:6],
            "highest_frequency_cm": freqs_cm[-1],
            "frequencies_cm": freqs_cm,
            "pyscf_rrho_g_tot_discrepancy_eh": pyscf_thermo_diff,
            "timings_seconds": raw.get("timings_seconds", {}),
            "optimized_coordinates_angstrom": coords_opt.tolist(),
            "thermochemistry": arm_thermo,
        }

    pairwise_rmsd = {}
    for first, second in combinations(CONFORMER_NAMES, 2):
        pairwise_rmsd[f"{first}-{second}"] = kabsch_rmsd(
            elements,
            runs_summary[first]["optimized_coordinates_angstrom"],
            runs_summary[second]["optimized_coordinates_angstrom"],
        )
    distinct_ok = all(
        val >= decision["distinct_conformer_min_heavy_atom_rmsd_angstrom"]
        for val in pairwise_rmsd.values()
    )
    all_run_checks_ok = all(all(chk.values()) for chk in run_checks.values())
    fidelity_passed = all_run_checks_ok and distinct_ok

    single_elec_eh = {
        name: runs_summary[name]["electronic_energy_hartree"] for name in CONFORMER_NAMES
    }
    single_elec_eval = evaluate_distribution(
        single_elec_eh, preflight["source_electronic_populations"], inputs
    )
    single_elec_pops = single_elec_eval["populations"]

    primary_arms = {}
    secondary_source_composite_arms = {}
    for arm in ARM_NAMES:
        single_free_eh = {
            name: single_elec_eh[name]
            + runs_summary[name]["thermochemistry"][arm]["thermochemical_correction_hartree"]
            for name in CONFORMER_NAMES
        }
        primary_arms[arm] = evaluate_distribution(
            single_free_eh, single_elec_pops, inputs
        )

        comp_eh = {
            name: preflight["source_electronic_energies_hartree"][name]
            + runs_summary[name]["thermochemistry"][arm]["thermochemical_correction_hartree"]
            for name in CONFORMER_NAMES
        }
        secondary_source_composite_arms[arm] = evaluate_distribution(
            comp_eh, preflight["source_electronic_populations"], inputs
        )

    concentrated_arms = [
        arm for arm in ARM_NAMES if primary_arms[arm]["concentration_criterion_met"]
    ]
    if not fidelity_passed:
        verdict = "inconclusive"
        reason = "method-fidelity gate failed"
    elif len(concentrated_arms) == len(ARM_NAMES):
        verdict = "supported"
        reason = "both registered rotor arms concentrated the single-surface ensemble beyond the near-uniform region"
    elif len(concentrated_arms) == 0:
        verdict = "falsified"
        reason = "both registered rotor arms remained inside the near-uniform region on the single surface"
    else:
        verdict = "inconclusive"
        reason = "registered rotor arms disagreed across the concentration boundary"

    return {
        "schema_version": 1,
        "experiment": inputs["experiment"],
        "generated_at": generated_at,
        "provenance": {
            "inputs": {"path": repository_path(INPUTS_PATH), "sha256": sha256(INPUTS_PATH)},
            "preregistration": {
                "path": repository_path(PREREG_PATH),
                "sha256": sha256(PREREG_PATH),
            },
            "run_artifacts": run_artifacts,
        },
        "protocol": {
            "conditions": conditions,
            "thermochemistry_arms": inputs["thermochemistry_arms"],
            "decision": decision,
        },
        "source_preflight": preflight,
        "single_surface_electronic_baseline": single_elec_eval,
        "primary_single_surface_analysis": primary_arms,
        "secondary_source_plus_dft_thermo_diagnostic": secondary_source_composite_arms,
        "runs": runs_summary,
        "fidelity": {
            "run_checks": run_checks,
            "distinct_conformer_pair_rmsd_angstrom": pairwise_rmsd,
            "distinct_conformers_passed": distinct_ok,
            "all_run_checks_passed": all_run_checks_ok,
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


def rounded(value, significant: int = 10, clamp_tiny: bool = True):
    """Round floats to 10 significant digits so eigensolver last-ulp differences
    between linux-x86_64 OpenBLAS and osx-arm64 Accelerate serialize identically."""
    if isinstance(value, bool) or not isinstance(value, float):
        if isinstance(value, dict):
            return {
                k: rounded(v, significant, clamp_tiny=(clamp_tiny and k != "protocol"))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [rounded(v, significant, clamp_tiny=clamp_tiny) for v in value]
        return value
    if value == 0.0 or not math.isfinite(value):
        return value
    if clamp_tiny and abs(value) < 1.0e-12:
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
