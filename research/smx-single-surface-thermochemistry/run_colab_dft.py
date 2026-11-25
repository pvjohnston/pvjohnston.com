#!/usr/bin/env python3
"""Google Colab GPU4PySCF runner for single-surface SMX conformer thermochemistry.

Executes tight `geomeTRIC` geometry optimization + analytical `IEF-PCM(water)`
nuclear Hessian on `B3LYPG-D3(BJ)/def2-TZVP` for conformers A, B, C, and D,
checkpointing each completed conformer immediately so ephemeral Colab sessions
can resume without losing progress.

Usage on Colab:
    python3 research/smx-single-surface-thermochemistry/run_colab_dft.py --smoke-test
    python3 research/smx-single-surface-thermochemistry/run_colab_dft.py \
        --checkpoint-dir /content/drive/MyDrive/pvjohnston-colab/smx-single-surface
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INPUTS_PATH = HERE / "inputs.json"
PREREG_PATH = HERE / "PREREGISTRATION.md"
RUNS_DIR = HERE / "runs"
CONFORMER_NAMES = ("A", "B", "C", "D")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def to_numpy(array_like) -> np.ndarray:
    if hasattr(array_like, "get"):
        array_like = array_like.get()
    return np.asarray(array_like, dtype=float)


def shell_capture(cmd: list[str]) -> str:
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
        )
        return res.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def package_version(dist_name: str) -> str:
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def record_colab_environment(checkpoint_dir: Path | None) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    packages = [
        "pyscf",
        "gpu4pyscf-cuda12x",
        "gpu4pyscf",
        "gpu4pyscf-libxc-cuda12x",
        "cupy-cuda12x",
        "cupy",
        "cutensor-cu12",
        "pyscf-dispersion",
        "geometric",
        "numpy",
        "scipy",
        "h5py",
    ]
    env_info = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "git_head": shell_capture(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
        "git_status": shell_capture(["git", "-C", str(ROOT), "status", "--short"]),
        "nvidia_smi": shell_capture(["nvidia-smi"]),
        "lscpu": shell_capture(["lscpu"]),
        "packages": {pkg: package_version(pkg) for pkg in packages},
        "frozen_sha256": {
            "PREREGISTRATION.md": sha256(PREREG_PATH),
            "inputs.json": sha256(INPUTS_PATH),
            "run_colab_dft.py": sha256(Path(__file__).resolve()),
            "thermo_analysis.py": sha256(HERE / "thermo_analysis.py"),
        },
    }
    out_path = RUNS_DIR / "environment_colab.json"
    out_path.write_text(json.dumps(env_info, indent=2) + "\n", encoding="utf-8")
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, checkpoint_dir / "environment_colab.json")
    return out_path


def build_mol(atoms: list, conditions: dict, log_path: Path | None = None):
    from pyscf import gto

    atom_spec = [( sym, tuple(coords) ) for sym, *coords in atoms]
    kwargs = {
        "atom": atom_spec,
        "basis": conditions["basis"],
        "unit": "Angstrom",
        "charge": int(conditions["charge"]),
        "spin": int(conditions["spin"]),
        "verbose": 4,
    }
    if log_path is not None:
        kwargs["output"] = str(log_path)
    return gto.M(**kwargs)


def build_gpu_mf(mol, conditions: dict):
    from gpu4pyscf.dft import rks

    mf = rks.RKS(mol, xc=conditions["xc"])
    if conditions.get("density_fit"):
        mf = mf.density_fit()
    mf.grids.level = int(conditions["grids_level"])
    mf.disp = conditions["dispersion"]
    mf = mf.PCM()
    mf.with_solvent.method = conditions["pcm_method"]
    mf.with_solvent.eps = float(conditions["pcm_eps"])
    mf.with_solvent.lebedev_order = int(conditions["pcm_lebedev_order"])
    mf.conv_tol = float(conditions["scf_conv_tol"])
    mf.conv_tol_grad = float(conditions["scf_conv_tol_grad"])
    mf.max_cycle = int(conditions["scf_max_cycle"])
    return mf


def write_xyz(path: Path, comment: str, symbols: list[str], coords_ang: np.ndarray) -> None:
    lines = [str(len(symbols)), comment]
    for sym, (x, y, z) in zip(symbols, coords_ang, strict=True):
        lines.append(f"{sym:<2} {x: .10f} {y: .10f} {z: .10f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_structure(
    label: str,
    atoms: list,
    conditions: dict,
    out_dir: Path,
) -> dict:
    from pyscf import dft as cpu_dft
    from pyscf.geomopt.geometric_solver import optimize
    from pyscf.hessian import thermo

    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "pyscf.log"
    opt_xyz_path = out_dir / "opt.xyz"
    dft_json_path = out_dir / "dft_result.json"

    t_start = time.time()
    mol_init = build_mol(atoms, conditions, log_path=log_path)
    mf_init = build_gpu_mf(mol_init, conditions)

    t_opt0 = time.time()
    conv_params = {
        "convergence_energy": float(conditions["opt_convergence_energy_eh"]),
        "convergence_grms": float(conditions["opt_convergence_grms_eh_bohr"]),
        "convergence_gmax": float(conditions["opt_convergence_gmax_eh_bohr"]),
        "convergence_drms": float(conditions["opt_convergence_drms_bohr"]),
        "convergence_dmax": float(conditions["opt_convergence_dmax_bohr"]),
    }
    mol_opt = optimize(
        mf_init,
        maxsteps=int(conditions["opt_maxsteps"]),
        **conv_params,
    )
    t_opt = time.time() - t_opt0

    # Rebuild a clean mean-field object on the optimized structure
    coords_opt_ang = to_numpy(mol_opt.atom_coords(unit="Angstrom"))
    symbols = [mol_opt.atom_symbol(i) for i in range(mol_opt.natm)]
    opt_atoms = [[sym, * row.tolist()] for sym, row in zip(symbols, coords_opt_ang, strict=True)]
    write_xyz(
        opt_xyz_path,
        f"{label} optimized on B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)",
        symbols,
        coords_opt_ang,
    )

    mol_final = build_mol(opt_atoms, conditions, log_path=log_path)
    mf_final = build_gpu_mf(mol_final, conditions)

    t_scf0 = time.time()
    e_tot = float(mf_final.kernel())
    scf_converged = bool(mf_final.converged)
    t_scf = time.time() - t_scf0
    if not scf_converged:
        raise RuntimeError(f"{label}: final SCF at optimized geometry did not converge")

    t_grad0 = time.time()
    grad = to_numpy(mf_final.nuc_grad_method().kernel())
    t_grad = time.time() - t_grad0
    grad_rms = float(np.sqrt(np.mean(grad ** 2)))
    grad_max = float(np.max(np.abs(grad)))

    t_hess0 = time.time()
    hess_obj = mf_final.Hessian()
    if conditions.get("density_fit"):
        hess_obj.auxbasis_response = 2
    hess_raw = to_numpy(hess_obj.kernel())
    t_hess = time.time() - t_hess0

    natm = mol_final.natm
    hess_3n = hess_raw.transpose(0, 2, 1, 3).reshape(3 * natm, 3 * natm)

    # PySCF reference harmonic analysis & 298.15 K RRHO cross-check
    mol_cpu = mol_final.copy()
    mol_cpu.output = None
    freq_info = thermo.harmonic_analysis(mol_cpu, hess_raw)
    mf_ref = cpu_dft.RKS(mol_cpu)
    mf_ref.e_tot = e_tot
    thermo_info = thermo.thermo(
        mf_ref,
        freq_info["freq_au"],
        float(conditions["temperature_k"]),
        float(conditions["pressure_pa"]),
    )
    freq_wavenumber = np.asarray(freq_info["freq_wavenumber"])
    if np.iscomplexobj(freq_wavenumber):
        pyscf_freqs_cm = [
            float(-abs(val.imag) if abs(val.imag) > abs(val.real) else val.real)
            for val in freq_wavenumber
        ]
    else:
        pyscf_freqs_cm = [float(val) for val in freq_wavenumber]

    payload = {
        "label": label,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "opt_converged": True,
        "final_scf_converged": scf_converged,
        "hessian_completed": True,
        "nao": int(mol_final.nao_nr()),
        "nelectron": int(mol_final.nelectron),
        "electronic_energy_hartree": e_tot,
        "post_opt_grad_rms_eh_bohr": grad_rms,
        "post_opt_grad_max_eh_bohr": grad_max,
        "elements": symbols,
        "atom_masses_amu": to_numpy(mol_final.atom_mass_list(isotope_avg=True)).tolist(),
        "optimized_coordinates_angstrom": coords_opt_ang.tolist(),
        "pyscf_frequencies_cm": pyscf_freqs_cm,
        "pyscf_rrho_zpe_hartree": float(thermo_info["ZPE"][0]),
        "pyscf_rrho_h_tot_hartree": float(thermo_info["H_tot"][0]),
        "pyscf_rrho_g_tot_hartree": float(thermo_info["G_tot"][0]),
        "hessian_3n_hartree_per_bohr2": hess_3n.tolist(),
        "pyscf_log_sha256": sha256(log_path),
        "opt_xyz_sha256": sha256(opt_xyz_path),
        "timings_seconds": {
            "opt": round(t_opt, 3),
            "final_scf": round(t_scf, 3),
            "final_grad": round(t_grad, 3),
            "hessian": round(t_hess, 3),
            "total": round(time.time() - t_start, 3),
        },
    }
    dft_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def smoke_test(conditions: dict, checkpoint_dir: Path | None) -> int:
    print("=== Running GPU4PySCF B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water) smoke test on H2O ===", flush=True)
    env_path = record_colab_environment(checkpoint_dir)
    print(f"Recorded runtime provenance -> {env_path}", flush=True)
    water_atoms = [
        ["O", 0.0000000, 0.0000000, 0.1173000],
        ["H", 0.0000000, 0.7572000, -0.4692000],
        ["H", 0.0000000, -0.7572000, -0.4692000],
    ]
    smoke_dir = Path("/tmp/smx_gpu4pyscf_smoke_h2o")
    if smoke_dir.exists():
        shutil.rmtree(smoke_dir)
    res = run_structure("H2O_smoke", water_atoms, conditions, smoke_dir)
    freqs = res["pyscf_frequencies_cm"]
    print(
        f"Smoke test passed in {res['timings_seconds']['total']:.1f}s | "
        f"E = {res['electronic_energy_hartree']:.8f} Eh | "
        f"grad_rms = {res['post_opt_grad_rms_eh_bohr']:.2e} | "
        f"freqs (cm^-1) = {[round(f, 1) for f in freqs]}",
        flush=True,
    )
    if len(freqs) != 3 or min(freqs) < 1000.0:
        raise RuntimeError(f"unexpected H2O vibrational frequencies: {freqs}")
    return 0


def sync_from_checkpoint(conformer: str, checkpoint_dir: Path | None) -> bool:
    local_dir = RUNS_DIR / conformer
    if (local_dir / "dft_result.json").is_file() and (local_dir / "opt.xyz").is_file():
        return True
    if checkpoint_dir is None:
        return False
    ckpt_conformer = checkpoint_dir / "runs" / conformer
    if (ckpt_conformer / "dft_result.json").is_file() and (ckpt_conformer / "opt.xyz").is_file():
        local_dir.mkdir(parents=True, exist_ok=True)
        for fname in ("dft_result.json", "opt.xyz", "pyscf.log"):
            src = ckpt_conformer / fname
            if src.is_file():
                shutil.copy2(src, local_dir / fname)
        print(f"Restored completed conformer {conformer} from checkpoint {ckpt_conformer}", flush=True)
        return True
    return False


def sync_to_checkpoint(conformer: str, checkpoint_dir: Path | None) -> None:
    if checkpoint_dir is None:
        return
    local_dir = RUNS_DIR / conformer
    ckpt_conformer = checkpoint_dir / "runs" / conformer
    ckpt_conformer.mkdir(parents=True, exist_ok=True)
    for fname in ("dft_result.json", "opt.xyz", "pyscf.log"):
        src = local_dir / fname
        if src.is_file():
            shutil.copy2(src, ckpt_conformer / fname)
    print(f"Checkpointed conformer {conformer} -> {ckpt_conformer}", flush=True)


def package_bundle(checkpoint_dir: Path | None) -> Path:
    bundle_path = HERE / "smx_single_surface_colab_artifacts.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        if RUNS_DIR.is_dir():
            tar.add(RUNS_DIR, arcname="runs")
        results_json = HERE / "results.json"
        if results_json.is_file():
            tar.add(results_json, arcname="results.json")
    if checkpoint_dir is not None:
        shutil.copy2(bundle_path, checkpoint_dir / bundle_path.name)
        results_json = HERE / "results.json"
        if results_json.is_file():
            shutil.copy2(results_json, checkpoint_dir / "results.json")
    return bundle_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--conformer", choices=CONFORMER_NAMES, action="append")
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    inputs = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    conditions = inputs["conditions"]

    if args.smoke_test:
        return smoke_test(conditions, args.checkpoint_dir)

    record_colab_environment(args.checkpoint_dir)
    selected = tuple(args.conformer or CONFORMER_NAMES)

    for name in selected:
        local_dir = RUNS_DIR / name
        if not args.force and sync_from_checkpoint(name, args.checkpoint_dir):
            print(f"Skipping already-completed conformer {name}", flush=True)
            continue
        if local_dir.exists() and args.force:
            shutil.rmtree(local_dir)

        print(f"\n=== Starting SMX conformer {name} (B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM water) ===", flush=True)
        res = run_structure(
            f"SMX_{name}",
            inputs["conformers"][name]["atoms"],
            conditions,
            local_dir,
        )
        sync_to_checkpoint(name, args.checkpoint_dir)
        print(
            f"Finished {name} in {res['timings_seconds']['total']:.1f}s "
            f"(opt {res['timings_seconds']['opt']:.1f}s, hess {res['timings_seconds']['hessian']:.1f}s) | "
            f"E = {res['electronic_energy_hartree']:.8f} Eh | "
            f"lowest 3 modes = {[round(x, 1) for x in res['pyscf_frequencies_cm'][:3]]} cm^-1",
            flush=True,
        )

    # If all four conformers are complete, run deterministic analysis and create download bundle
    if all((RUNS_DIR / c / "dft_result.json").is_file() for c in CONFORMER_NAMES):
        subprocess.run(
            [os.sys.executable, str(HERE / "thermo_analysis.py"), "--analyze"],
            check=True,
        )
        subprocess.run(
            [os.sys.executable, str(HERE / "thermo_analysis.py"), "--check"],
            check=True,
        )
        bundle = package_bundle(args.checkpoint_dir)
        print(f"\nAll four SMX conformers analyzed and packaged -> {bundle}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
