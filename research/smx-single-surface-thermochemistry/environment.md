# Environment

The single-surface `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` optimization and
analytical Hessian stage ran on Google Colab (`linux-x86_64`), while normal-mode
projection, `rrho` and `mrrho50` statistical thermodynamics, Kabsch RMSDs,
decision gates, and metric generation run deterministically in pure Python +
NumPy (`thermo_analysis.py`) on both `linux-x86_64` and `osx-arm64` without GPU
or PySCF dependencies.

## GPU quantum-chemistry stage (Google Colab)

All four sulfamethoxazole conformers (`A`, `B`, `C`, `D`) completed sequentially
between `2026-11-25T20:58:14Z` and `2026-11-26T17:24:43Z` (20.4 h wall time) on
a Google Colab **NVIDIA Tesla T4** GPU runtime (16 GiB GDDR6, Turing `sm_75`),
checkpointing `dft_result.json`, `opt.xyz`, and `pyscf.log` to Google Drive
after each conformer under frozen commit `f02a885`. On `2026-11-26T21:15:21Z`, a
follow-up Colab session (`138a3eb`, NVIDIA L4, `runs/environment_colab.json`)
restored those four immutable conformer checkpoints and packaged the archive.

- Operating system and kernel: `Linux-6.6.159+-x86_64-with-glibc2.39`
- Architecture: `x86_64` (Intel Xeon @ 2.20 GHz) + NVIDIA Tesla T4 GPU (quantum
  chemistry) / NVIDIA L4 GPU (checkpoint restore and packaging)
- Python version: `3.13` (`3.13.12` / `3.13.16`)
- Quantum-chemistry packages (recorded in `runs/*/pyscf.log` and
  `runs/environment_colab.json`):
  - `pyscf == 2.15.1`
  - `gpu4pyscf` (`PCMRKS`, `PCMGradients`, `PCMHessian`, CUDA LibXC `7.1.2`)
  - `pyscf-dispersion == 1.7.0` (`dftd3`, Becke–Johnson damping)
  - `geometric == 1.1.1`
  - `numpy == 2.4.6`, `scipy == 1.16.3`, `h5py == 3.14.0`
- Random seeds and nondeterministic operations: deterministic SCF and cavity
  quadrature (`grids.level = 4`, `lebedev_order = 29`); GPU floating-point
  reduction order is orders of magnitude below every decision gate
- Required environment variables: none (no API keys or secrets)

## Deterministic local analysis and figure stage

- Verified on `osx-arm64` (Python 3.15, NumPy, Pillow 13.0.0, Node.js)
- Canonical float serialization in `results.json` rounds floats to 10
  significant digits so `thermo_analysis.py --check` is byte-identical across
  `linux-x86_64` OpenBLAS and `osx-arm64` Accelerate.
