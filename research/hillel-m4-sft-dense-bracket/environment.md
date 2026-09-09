# Environment

The canonical ORCA run was performed on a local Apple Silicon machine
in the private Molecules lab. This public repository records that
boundary and does not rerun ORCA. The analysis projection (sign
changes, interpolants, site metrics) is regenerated from the committed
scored dump on whatever host checks out the post branch.

- Operating system and version (canonical run): macOS on Apple Silicon
- Architecture (canonical run): arm64
- Quantum-chemistry executable: ORCA 6.1.1. Hillel et al. 2024 used
  ORCA 5.0.3. This repository does not pin a host path and does not
  run ORCA in CI.
- Method: SF-TDA LibXC(BHANDHLYP) D3BJ/def2-QZVPP, RIJCOSX, def2/J,
  TightSCF, gas phase, no PCM. Same-geometry two-root single points
  on S0-relaxed and T1-relaxed constrained-CNNC geometries at 90°,
  95°, 100°, and 105°. New Opt only at 95° and 100°. No IROOT on
  the single points. `%pal nprocs 4`. Jobs were run as
  `orca input.inp`, never `mpirun`.
- Hardware assumptions: laptop-scale single-molecule DFT; wall time
  is hours per constrained point, not a cluster job
- Locale/timezone: freeze recorded as 2026-09-02 15:30 PDT
- Random seeds and nondeterministic operations: none declared. SCF
  convergence is deterministic to the requested thresholds on one
  machine and one thread count; last digits can move with BLAS
- Required environment variables: none committed
- External services: none

## Analysis

Metrics are produced from the committed scored dump. This
directory does not rerun ORCA and does not pin an ORCA rerun path.

- Metrics generator: Node v22.14.0, `generate-metrics.mjs`; no extra
  packages. It fingerprints `results/dense_bracket_metrics.json` and
  `research/hillel-m4-sft-tworoot/metrics.json`.
- The Figure 1 renderer uses Python 3.12.3, NumPy 2.0.2, and Pillow
  11.3.0, pinned in `requirements-figure.txt`. Latin type is the
  committed `analysis/hanken-grotesk.ttf`. Axis Δ and φ come from
  the committed `analysis/dejavu-sans.ttf` at the same pixel size.
  Both load with Pillow `ImageFont.truetype`. No host font path and
  no platform-specific FreeType library name.
- The metrics generator has no lockfile. It reads the scored dump
  and the published two-root `metrics.json`.

## What is not in this repository

ORCA `.out` files and scratch from the private Molecules lab are
not committed. They are large and embed absolute machine paths. The
same choice is recorded in `research/hillel-m4-sft-tworoot`. The
committed evidence is `results/dense_bracket_metrics.json`.
