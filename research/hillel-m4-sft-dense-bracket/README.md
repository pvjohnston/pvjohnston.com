# Hillel M4 SF-TDA: denser 90–105° same-geometry bracket

Publication projection of a private-lab ORCA 6.1.1 denser-bracket
same-geometry two-root SF-TDA experiment. This directory does not
contain the raw ORCA `.out` files and does not rerun ORCA. It binds
the research note
`posts/2026-09-09-does-a-denser-m4-bracket-keep-the-sign-change.md`.

## Question and boundary

- Post type: research
- Question: does a denser 90–105° same-geometry SF-TDA bracket keep
  the M4 sign change?
- Research falsifier: (1) neither family has a both-assigned
  same-geometry ΔE sign change on a neighboring pair in 90–105°;
  (2) a family has a sign change whose interpolant lies outside
  90–105°; (3) a family has no neighboring both-assigned pair.
  Registered falsifier (1) fires only if neither family changes
  sign. A one-family miss fails the published both-family verdict
  without firing (1); that outcome is `one_family_only_sign_change`.
- What this experiment can establish: the sign of same-geometry
  ΔE = E(T1) − E(S0) on a 5° fill of the 90–105° window, scored
  separately on the S0-relaxed and T1-relaxed families, and the
  stored linear interpolant of each 100°/105° pair.
- What it cannot establish: a located MECP, an evaluated degeneracy,
  PCM, or a reopening of the published 2026-08-28 two-root verdict.
- Traceability: traceable
- Highest reproduction level: analysis-reproducible from the
  committed scored dump. Not end-to-end in this public repository.
- Archived-evidence or rerun constraints: raw ORCA output stays in
  the private Molecules lab (large, host paths), the same scratch
  convention as `research/hillel-m4-sft-tworoot`. Absolute host
  paths were replaced by pack-relative filenames. 90° and 105°
  ΔE values are reused from the published two-root rematch; 95°
  and 100° are new jobs whose assigned S0/T1 totals are copied
  from the lab scored dump.

## Molecule

| ID | Species | Charge / multiplicity |
|----|---------|------------------------|
| M4 | 4-dimethylamino-4′-nitroazobenzene | 0 / SF-TDA manifold |

Required CNNC window: 90°, 95°, 100°, 105°. Two geometry families:
S0-relaxed and T1-relaxed constrained-CNNC opts. One SF-TDA SP per
geometry. New opts only at 95° and 100°. The named next experiment
is an MECP search on the same SF surfaces near the stored
interpolants.

## Generate publication metrics

```sh
node research/hillel-m4-sft-dense-bracket/generate-metrics.mjs
node research/hillel-m4-sft-dense-bracket/generate-metrics.mjs --check
node scripts/verify-metrics.mjs
```

`generate-metrics.mjs` flattens the committed scored dump into
`metrics.json`. It checks that each point's ΔE matches
ΔE(Eh) × conversion_Eh_to_kJmol and that each family's 100°/105°
pair interpolant matches the stored neighboring-pair value. The
site interpolant metrics are the stored `crossing_phi_deg_s0` and
`crossing_phi_deg_t1`. Reused 90°/105° records and the published
⟨S²⟩ residual ranges are compared to
`research/hillel-m4-sft-tworoot/metrics.json`, which is
fingerprinted in provenance. `both_assigned` is true only when both
assignment objects include iroot, ⟨S²⟩, and E_Eh, and those ⟨S²⟩
values sit in the singlet/triplet bins. Assigned ΔE must equal
E(T1)−E(S0) on every point.

## Regenerate Figure 1

```sh
python3 -m pip install -r research/hillel-m4-sft-dense-bracket/requirements-figure.txt
python3 research/hillel-m4-sft-dense-bracket/analysis/make_deltaE_figure.py
```

The renderer loads `analysis/points.json` for the two-decimal ΔE
labels, open/filled reuse flags, and the stored 100–105 linear
zeros (103.43° S0-relaxed, 104.34° T1-relaxed). Before drawing, it
checks every plotted gap and stored zero against
`results/dense_bracket_metrics.json`. Those zeros are
not recomputed from the rounded ΔE values. Fonts are the committed
`analysis/hanken-grotesk.ttf` via Pillow `ImageFont.truetype` for
Latin ticks and numbers. Axis Δ and φ come from the committed
`analysis/dejavu-sans.ttf` at the same pixel size. Coverage is
checked from each TTF cmap before drawing. The renderer does not
look up a host font path. Lab-side molecular stills are optional
and are not in this repository. The same command writes the data
plot and exits 0 when frames are absent.

The command updates:

- `images/2026-09-09-does-a-denser-m4-bracket-keep-the-sign-change-figure1.png`

Point labels on the plot are the `points.json` ΔE values. Open
markers are the reused 90° and 105° published two-root points;
filled markers are the new 95° and 100° points. Linear
interpolants of the 100–105 pairs are plus marks on the ΔE = 0
line, labeled “lin.”

## Data and publication

`PUBLIC_FILES.txt` is the routing allowlist. Raw ORCA logs are
excluded. The Hillel papers are literature and are not
redistributed. Literature citations live in `bib/bibliography.bib`.
