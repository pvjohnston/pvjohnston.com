# PREREGISTRATION — denser 90–105° same-geometry SF-TDA bracket

Frozen 2026-09-02 15:30 PDT, before any 95° or 100° energy is seen.
Amendment to `hillel-m4-sft-tworoot`; the 2026-08-27 two-root freeze is
unchanged and is not reopened.

## Question
Does a denser 90–105° same-geometry SF-TDA bracket keep the M4 sign change?

## Hypothesis
ΔE still changes sign between neighboring both-assigned points inside
90–105° on both families when S0 and T1 are taken from the same SF
manifold on one structure.

## Crossing definition
On each constrained-CNNC geometry family (S0-relaxed and T1-relaxed),
evaluate same-geometry ΔE = E(T1) − E(S0) at 90°, 95°, 100°, and 105°.
The 90° and 105° points are the already-published two-root single points;
they are reused and not re-run. The 95° and 100° points are new
constrained optimizations on that family, then one SF-TDA single point
per new geometry. S0 = lowest SF root ⟨S²⟩≈0; T1 = lowest ⟨S²⟩≈2; both
from that one calculation. A same-geometry sign change is a sign change
of ΔE on a neighboring both-assigned pair inside 90–105°, scored
separately on each family. The linear interpolant of a sign-change pair
is recorded; it is not an MECP.

## Falsifiers
1. Neither family has a both-assigned sign change of same-geometry ΔE
   on a neighboring pair in 90–105°.
2. A family has a sign change whose interpolant lies outside 90–105°.
3. A family has no neighboring both-assigned pair.

The published verdict requires a sign change on both families. A
one-family miss fails that verdict without firing (1).

## Method (binding)
ORCA 6.1.1, `$ORCA`. `%pal nprocs 4`; never `mpirun`. SF-TDA,
LibXC(BHANDHLYP) D3(BJ)/def2-QZVPP, RIJCOSX, def2/J, TightSCF, gas,
charge 0, SF ref mult 3, NROOTS 3. No IROOT on the single points. New
constrained S0 and T1 optimizations at 95° and 100° only. No MECP search.

## Publication boundary

- Rights, privacy, secrets, and public-file review: no credentials
  or private data. Raw ORCA `.out` files stay in the private
  Molecules lab (large, machine paths), the same pattern as
  `research/hillel-m4-sft-tworoot`.
- Reproducibility level this design can earn: analysis-reproducible
  from the committed scored dump. Not end-to-end in this public
  repository.
- Archived-evidence or future-rerun constraints: the ORCA 6.1.1
  executable used for the canonical run lives on the private-lab
  host. This public repo does not rerun ORCA.

## Amendments

None at freeze.
