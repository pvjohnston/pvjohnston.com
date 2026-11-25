# SMX single-surface hybrid-DFT thermochemistry

Tests whether the thermal concentration of Blackmon and Closser's four aqueous
sulfamethoxazole (SMX) minima (A–D) onto conformer A survives when both the
electronic energies and the 298.15 K harmonic thermochemical corrections are
computed on one consistent hybrid-DFT + implicit-water surface
(`B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)`), removing the two-surface composite
approximation of `research/smx-conformer-thermochemistry/`.

## Question and boundary

- Post type: research
- Question: does the concentration of the SMX A–D conformer ensemble survive
  when electronic energies and 298.15 K harmonic free-energy corrections come
  from the same `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` surface?
- Research falsifier: [PREREGISTRATION.md](PREREGISTRATION.md) — falsified if
  both `rrho` and `mrrho50` remain inside the near-uniform region
  (`max shift < 10.0 pp` and `N_eff >= 3.5` relative to this surface's
  electronic baseline).
- What this experiment can establish: single-surface `B3LYPG-D3(BJ)/def2-TZVP +
  IEF-PCM(water)` relative electronic energies, harmonic frequencies, `rrho` and
  `mrrho50` 298.15 K populations, and a secondary diagnostic adding those same
  DFT/IEF-PCM thermal corrections to Blackmon and Closser's published electronic
  energies.
- What it cannot establish: Blackmon and Closser's unreported Q-Chem frequencies,
  explicit-solvent or pH dynamics, experimental aqueous conformer populations, or
  excited-state photochemistry.
- Traceability: not yet established (awaiting canonical Colab GPU run)
- Highest reproduction level: none yet (designed for analysis-reproducible
  locally from committed Cartesian Hessians, and end-to-end reproducible on a
  CUDA 12 GPU with GPU4PySCF)

## Stage 1: Preflight check (local, no GPU required)

```sh
python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --preflight
```

## Stage 2: GPU optimization and analytical Hessians (Google Colab)

Open `colab_runner.ipynb` in Google Colab on an **L4** or **A100** GPU runtime
(or run directly from the cloned `post/smx-single-surface-thermochemistry`
branch):

```sh
python3 research/smx-single-surface-thermochemistry/run_colab_dft.py \
  --smoke-test \
  --checkpoint-dir /content/drive/MyDrive/pvjohnston-colab/smx-single-surface-thermochemistry

python3 research/smx-single-surface-thermochemistry/run_colab_dft.py \
  --checkpoint-dir /content/drive/MyDrive/pvjohnston-colab/smx-single-surface-thermochemistry
```

Each conformer (`A`, `B`, `C`, `D`) is checkpointed immediately after its
Hessian completes (`runs/<X>/dft_result.json`, `runs/<X>/opt.xyz`,
`runs/<X>/pyscf.log`). When all four complete, `run_colab_dft.py` runs
`thermo_analysis.py --analyze` and packages
`smx_single_surface_colab_artifacts.tar.gz`.

## Stage 3: Unpack locally and generate publication metrics

Unpack `smx_single_surface_colab_artifacts.tar.gz` into this directory in the
`post/smx-single-surface-thermochemistry` worktree, then verify:

```sh
tar -xzf ~/Downloads/smx_single_surface_colab_artifacts.tar.gz \
  -C research/smx-single-surface-thermochemistry
python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --check
node research/smx-single-surface-thermochemistry/generate-metrics.mjs
node research/smx-single-surface-thermochemistry/generate-metrics.mjs --check
node scripts/verify-metrics.mjs
```

## Data and publication

`PUBLIC_FILES.txt` is added once the canonical outputs are reviewed for
publication (`scripts/verify-site.mjs` checks every path listed in any active
`PUBLIC_FILES.txt`). Raw multi-megabyte `pyscf.log` files may remain outside the
website routing table if oversized while `dft_result.json` and `opt.xyz`
preserve complete analysis reproducibility.
