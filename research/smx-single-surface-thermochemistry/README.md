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
- Verdict: **falsified** — every method-fidelity gate passed, and both `rrho`
  (`max shift = 7.5 pp`, `N_eff = 3.88`) and `mrrho50` (`max shift = 3.8 pp`,
  `N_eff = 3.97`) remained inside the near-uniform region.
- What this experiment can establish: single-surface `B3LYPG-D3(BJ)/def2-TZVP +
  IEF-PCM(water)` relative electronic energies, harmonic frequencies, `rrho` and
  `mrrho50` 298.15 K populations, and a secondary diagnostic adding those same
  DFT/IEF-PCM thermal corrections to Blackmon and Closser's published electronic
  energies.
- What it cannot establish: Blackmon and Closser's unreported Q-Chem frequencies,
  explicit-solvent or pH dynamics, experimental aqueous conformer populations, or
  excited-state photochemistry.
- Traceability: traceable
- Highest reproduction level: analysis-reproducible locally from committed
  Cartesian Hessians and geometries (`runs/*/dft_result.json`, `runs/*/opt.xyz`),
  and end-to-end reproducible on a CUDA GPU with PySCF 2.15.1 and GPU4PySCF.

## Regenerate analysis, metrics, and Figure 1 locally (no GPU required)

```sh
python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --preflight
python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --analyze
python3 research/smx-single-surface-thermochemistry/thermo_analysis.py --check
node research/smx-single-surface-thermochemistry/generate-metrics.mjs
node research/smx-single-surface-thermochemistry/generate-metrics.mjs --check
node scripts/verify-metrics.mjs
python3 research/smx-single-surface-thermochemistry/make-figure.py
python3 research/smx-single-surface-thermochemistry/make-figure.py --check
```

## Rerun GPU optimization and analytical Hessians (Google Colab)

Open `colab_runner.ipynb` in Google Colab on an NVIDIA GPU runtime:

```sh
python3 research/smx-single-surface-thermochemistry/run_colab_dft.py \
  --smoke-test \
  --checkpoint-dir /content/drive/MyDrive/pvjohnston-colab/smx-single-surface-thermochemistry

python3 research/smx-single-surface-thermochemistry/run_colab_dft.py \
  --force \
  --checkpoint-dir /content/drive/MyDrive/pvjohnston-colab/smx-single-surface-thermochemistry
```

## Data and publication

`PUBLIC_FILES.txt` routes the reviewed inputs, scripts, `results.json`,
`metrics.json`, `runs/environment_colab.json`, and all four `dft_result.json` +
`opt.xyz` conformer bundles onto the live site. The four 585 KB verbose
`runs/*/pyscf.log` files are committed in Git with SHA-256 digests recorded in
`dft_result.json`, and are omitted from live-site routing only for bundle size.
The Blackmon and Closser article and supplement are cited in `bib/bibliography.bib`
and documented in `sources.json` rather than redistributed.
