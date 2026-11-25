# Environment

The single-surface `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` optimization and
analytical Hessian stage runs on a Google Colab NVIDIA GPU runtime (`linux-x86_64`),
while normal-mode projection, `rrho` and `mrrho50` statistical thermodynamics,
Kabsch RMSDs, decision gates, and metric generation run deterministically in
pure Python + NumPy (`thermo_analysis.py`) on any platform without GPU or PySCF
dependencies.

## GPU quantum-chemistry stage (Google Colab)

`run_colab_dft.py` writes the exact runtime provenance (`nvidia-smi`, CPU model,
kernel, Python, `pyscf`, `gpu4pyscf`, `cupy`, `cutensor`, `geometric`,
`pyscf-dispersion`, and frozen file SHA-256 digests) to `runs/environment_colab.json`
during execution. Once the canonical Colab run completes, copy the recorded
versions here:

- Operating system and kernel: pending Colab run (`runs/environment_colab.json`)
- Architecture: `x86_64` + NVIDIA CUDA GPU
- Python version: pending Colab run
- Quantum-chemistry packages: `pyscf`, `gpu4pyscf-cuda12x`, `cutensor-cu12`,
  `cupy-cuda12x`, `pyscf-dispersion`, `geometric`
- Hardware assumptions: NVIDIA L4 or A100 GPU (CUDA 12.x) for analytical PCM
  Hessians; checkpointed per conformer to Google Drive
- Random seeds and nondeterministic operations: deterministic SCF/Hessian grids
  (`grids.level = 4`, `lebedev_order = 29`); floating-point reduction order on
  GPU can vary at ~`1e-10` Eh, orders of magnitude below every decision gate
- Required environment variables: none (no API keys or secrets)

## Deterministic local analysis stage

- Interpreter: Python >= 3.10 with `numpy`
- Metric generator: Node.js >= 20 (`generate-metrics.mjs`)
- Canonical float serialization: 12 significant digits (`< 1e-12` clamped to
  `0.0`) for architecture-independent `--check` verification across `linux-x86_64`
  and `osx-arm64`.
