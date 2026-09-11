---
title: "Does a denser 90–105° same-geometry SF-TDA bracket keep the Hillel M4 sign change?"
date: 2026-09-09
author: Peter Johnston
tags: computational chemistry, azobenzene, SF-TDDFT, push-pull chromophores, intersystem crossing
description: A 5° fill of this site's 2026-08-28 same-geometry two-root rematch of Hillel, Rough, Barrett, Pietro, and Mermut (2024) SF-TDA on 4-dimethylamino-4′-nitroazobenzene. The parent note's both-family sign change sat on a 15° 90–105° pair. This note narrows that pair with new constrained optimizations and same-geometry two-root single points at 95° and 100°.
post-type: research
contribution: a 5° fill of constrained S0 and T1 optimizations at 95° and 100° plus same-geometry two-root SF-TDA single points on those new M4 geometries, which is not in the 2026-08-28 two-root note and is not in Hillel et al. 2024.
contribution-type: untested regime
experiment: hillel-m4-sft-dense-bracket
status: supported
og-image: /images/2026-09-09-does-a-denser-m4-bracket-keep-the-sign-change-figure1.png
---

## Abstract

Hillel, Rough, Barrett, Pietro, and Mermut (2024), in *A cautionary tale of basic azo photoswitching in dichloromethane finally explained*, computed 4-phenylazopyridine (AzPy) and its N-protonated form (AzPyH+) with spin-flip time-dependent density functional theory (SF-TDDFT, Tamm–Dancoff) at BH&HLYP-D3(BJ)/def2-QZVPP in ORCA.[@Hillel2024] A prior note on this site rematched that electronic-structure level on 4-dimethylamino-4′-nitroazobenzene (M4) as a same-geometry two-root evaluation and found that ΔE = E(T1)−E(S0) changed sign between 90° and 105° on both constrained-CNNC geometry families ([2026-08-28 two-root note](/posts/2026-08-28-does-the-m4-sf-profile-gap-survive-same-geometry-two-root.html)). Those zeros were linear interpolants of a 15° pair. This note is an independent 5° fill of that rematch: new constrained optimizations and same-geometry two-root single points at 95° and 100°, with the published 90° and 105° two-root points reused.

It is not a rebuttal of the 2024 paper, and it does not reopen the published both-family 90–105° two-root verdict. The registered hypothesis, frozen 2026-09-02 15:30 PDT before any 95° or 100° energy was seen, is that ΔE still changes sign between neighboring both-assigned points inside 90–105° on both families when S0 and T1 are taken from the same SF manifold on one structure.

On both constrained-CNNC geometry families, the same-geometry SF-TDA gap $E(\mathrm{T1})-E(\mathrm{S0})$ changes sign between [flip_phi_lo_deg]{.metric}° and [flip_phi_hi_deg]{.metric}°. On the S0-relaxed family the gap is [deltae_kjmol_s0_100]{.metric} kJ/mol at 100° and [deltae_kjmol_s0_105]{.metric} kJ/mol at 105°; the linear interpolant of that pair is [crossing_phi_deg_s0]{.metric}°. On the T1-relaxed family the gap is [deltae_kjmol_t1_100]{.metric} kJ/mol at 100° and [deltae_kjmol_t1_105]{.metric} kJ/mol at 105°; the linear interpolant of that pair is [crossing_phi_deg_t1]{.metric}°. Those interpolants are linear estimates from the 5° pair. The registered hypothesis was **supported**.

## Introduction

Azobenzene and its derivatives change shape around the N=N azo bond. The **CNNC dihedral** is the torsion that takes the trans isomer (rings opposite, CNNC near 180°) toward the cis isomer (rings on the same side, near 0°). Two electronic states sit on that path. The **electronic ground state (S0)** is the closed-shell singlet. The **lowest triplet (T1)** is the lowest state with two unpaired electrons of the same spin. Hillel *et al.* discuss a crossing as a geometry on the CNNC path where those two states have the same energy.[@Hillel2024]

Hillel, Rough, Barrett, Pietro, and Mermut computed AzPy and AzPyH+ with SF-TDDFT (Tamm–Dancoff) at BH&HLYP-D3(BJ)/def2-QZVPP in ORCA and found that protonation removes that crossing.[@Hillel2024] A later note on this site asked whether M4 still shows a same-geometry two-root sign change of $E(\mathrm{T1})-E(\mathrm{S0})$ when both roots come from one SF-TDA calculation on one structure ([2026-08-28 two-root note](/posts/2026-08-28-does-the-m4-sf-profile-gap-survive-same-geometry-two-root.html)). On that window both geometry families changed sign between 90° and 105°. The stored zeros were linear interpolants of those 15° pairs.

The 15° 90–105° pair leaves a wide interval between the last negative and first positive ΔE. This note fills that interval at 5° with new constrained optimizations and same-geometry two-root single points at 95° and 100°, reusing the published 90° and 105° points. We could not find a published 95°/100° same-geometry two-root SF-TDA evaluation of those M4 families. The hypothesis, frozen 2026-09-02 15:30 PDT before any 95° or 100° energy was seen and not rewritten afterward: **ΔE still changes sign between neighboring both-assigned points inside 90–105° on both families when S0 and T1 are taken from the same SF manifold on one structure.** Three falsifiers were fixed at the same time. (1) Neither family has a both-assigned sign change of same-geometry ΔE on a neighboring pair in 90–105°. (2) A family has a sign change whose interpolant lies outside 90–105°. (3) A family has no neighboring both-assigned pair. The published verdict requires a sign change on both families. If exactly one family changes sign, registered (1) stays false and the both-family hypothesis is not supported; that one-family outcome is scored separately. Either outcome of (1), (2), or (3), or a one-family miss, is publishable. A both-family sign change on a neighboring 5° pair would put the 2026-08-28 zeros on a narrower bracket; a miss would leave the sign change as a property of the 15° pair.

## Computational Methods

This is an independent fill of this site's own published same-geometry rematch. The Hillel *et al.* 2024 geometries, orbitals, and energy tables were not imported.[@Hillel2024] The 90° and 105° single points are the already-published two-root evaluations from the 2026-08-28 note; they were reused and were not re-run. New constrained-CNNC optimizations were run at 95° and 100° on the S0-relaxed family and on the T1-relaxed family, and each new geometry received one SF-TDA single point.

The run uses ORCA 6.1.1; Hillel *et al.* 2024 used ORCA 5.0.3.[@Hillel2024; @Neese2025ORCA6] Each geometry received one SF-TDDFT single point (Tamm–Dancoff). **S0** is the lowest SF root with $\langle S^2\rangle\le 0.5$. **T1** is the lowest SF root with $1.5\le\langle S^2\rangle\le 2.5$. Roots outside those bins are unused. Those cuts are the lab operationalization of the freeze’s $\langle S^2\rangle\approx 0$ / $\approx 2$ / not-near-1 rule. Assignments follow $\langle S^2\rangle$, not IROOT. The single-point inputs contain no IROOT keyword. The functional, dispersion, and basis are LibXC(BHANDHLYP) with D3(BJ) and def2-QZVPP.[@Grimme2011; @Weigend2005Balanced] The Coulomb fit is RIJCOSX with def2/J. The SCF is TightSCF. The run is gas-phase; no polarizable continuum was applied. Charge 0. The SF reference multiplicity is 3. NROOTS is 3. Jobs used `%pal nprocs 4` and were started as `orca input.inp`, never `mpirun`. No minimum-energy crossing point was located.

$\Delta E(\varphi,\mathrm{geom})=E(\mathrm{T1})-E(\mathrm{S0})$ is the gap between the two assigned roots on that one structure. Conversion is 1 Eh = 2625.49963831 kJ/mol. A same-geometry sign change is a sign change of ΔE on a neighboring both-assigned pair in 90–105°, scored separately on the S0-relaxed family and on the T1-relaxed family. The linear interpolant of a sign-change pair is recorded. The two family interpolants are not averaged.

The scored dump, conversions, signs, interpolants, and contamination flags were checked against the 2026-09-02 freeze. The committed evidence is `research/hillel-m4-sft-dense-bracket/results/dense_bracket_metrics.json`. The environment record is `research/hillel-m4-sft-dense-bracket/environment.md`. Assigned S0 and T1 totals for the new 95° and 100° points are copied from that dump; ΔE on those points is $E(\mathrm{T1})-E(\mathrm{S0})$ of the assigned roots.

Raw ORCA `.out` files stay in the private Molecules lab. They are large and carry host paths, and they are treated as scratch in the same way as the 2026-08-28 SF logs. What is committed is the scored dump with pack-relative filenames. The reproducibility label this directory has earned is **analysis-reproducible**. It is not end-to-end reproducible from this public repository.

## Results

[both_assigned_point_count]{.metric} same-geometry points are both-assigned. Table 1 lists same-geometry ΔE on the S0-relaxed geometries. Table 2 lists the same quantity on the T1-relaxed geometries. The 90° and 105° rows reuse the published two-root single points.

**Table 1.** Same-geometry SF-TDA gap $\Delta E = E(\mathrm{T1})-E(\mathrm{S0})$ on each S0-relaxed constrained-CNNC geometry. Both roots come from one SF-TDA single point. LibXC(BHANDHLYP)-D3(BJ)/def2-QZVPP, SF-TDA, RIJCOSX, gas phase.

| CNNC (deg) | $\Delta E$ (Eh) | $\Delta E$ (kJ/mol) | Source |
| ---: | ---: | ---: | --- |
| 90 | [deltae_eh_s0_90]{.metric} | [deltae_kjmol_s0_90]{.metric} | reused |
| 95 | [deltae_eh_s0_95]{.metric} | [deltae_kjmol_s0_95]{.metric} | new |
| 100 | [deltae_eh_s0_100]{.metric} | [deltae_kjmol_s0_100]{.metric} | new |
| 105 | [deltae_eh_s0_105]{.metric} | [deltae_kjmol_s0_105]{.metric} | reused |

**Table 2.** Same-geometry SF-TDA gap $\Delta E = E(\mathrm{T1})-E(\mathrm{S0})$ on each T1-relaxed constrained-CNNC geometry. Both roots come from one SF-TDA single point. Same method as Table 1.

| CNNC (deg) | $\Delta E$ (Eh) | $\Delta E$ (kJ/mol) | Source |
| ---: | ---: | ---: | --- |
| 90 | [deltae_eh_t1_90]{.metric} | [deltae_kjmol_t1_90]{.metric} | reused |
| 95 | [deltae_eh_t1_95]{.metric} | [deltae_kjmol_t1_95]{.metric} | new |
| 100 | [deltae_eh_t1_100]{.metric} | [deltae_kjmol_t1_100]{.metric} | new |
| 105 | [deltae_eh_t1_105]{.metric} | [deltae_kjmol_t1_105]{.metric} | reused |

<figure>
  <img src="/images/2026-09-09-does-a-denser-m4-bracket-keep-the-sign-change-figure1.png" alt="Same-geometry SF-TDA gap ΔE versus constrained CNNC angle φ for S0-relaxed (solid blue circles) and T1-relaxed (dashed orange squares) M4 geometries. Open markers are reused published two-root points; filled markers are new points. Plus marks on the zero line are stored linear interpolants, labeled lin.">
</figure>

**Figure 1.** Same-geometry SF-TDA $\Delta E = E(\mathrm{T1})-E(\mathrm{S0})$ versus CNNC $\varphi$ on the denser bracket for the S0-relaxed and T1-relaxed families. Open markers are reused published two-root points; filled markers are new points. Plus marks are stored linear estimates of the neighboring sign-change pair spanning [flip_phi_lo_deg]{.metric}°–[flip_phi_hi_deg]{.metric}°, at [crossing_phi_deg_s0]{.metric}° (S0-relaxed) and [crossing_phi_deg_t1]{.metric}° (T1-relaxed). Those interpolants are not MECPs.

On both constrained-CNNC geometry families, the same-geometry SF-TDA gap $E(\mathrm{T1})-E(\mathrm{S0})$ changes sign between [flip_phi_lo_deg]{.metric}° and [flip_phi_hi_deg]{.metric}° (Figure 1). The linear interpolant of the S0-relaxed 100°/105° pair is [crossing_phi_deg_s0]{.metric}°. The linear interpolant of the T1-relaxed 100°/105° pair is [crossing_phi_deg_t1]{.metric}°. The 90°/95° pair does not change sign on the S0-relaxed family ([deltae_kjmol_s0_90]{.metric} and [deltae_kjmol_s0_95]{.metric} kJ/mol) or on the T1-relaxed family ([deltae_kjmol_t1_90]{.metric} and [deltae_kjmol_t1_95]{.metric} kJ/mol). The 95°/100° pair does not change sign on either family ([deltae_kjmol_s0_95]{.metric} and [deltae_kjmol_s0_100]{.metric} kJ/mol; [deltae_kjmol_t1_95]{.metric} and [deltae_kjmol_t1_100]{.metric} kJ/mol).

At φ = 100° both families have an unused SF root ([unused_sf_root_near_s2_1_phi100_both_families]{.metric}). On the S0-relaxed family that unused root sits near $\langle S^2\rangle\approx 1$. On the T1-relaxed family unused root 1 lies outside the singlet bin $\langle S^2\rangle\le 0.5$. Assigned T1 $\langle S^2\rangle$ at 100° is [assigned_t1_s2_s0_100]{.metric} on the S0-relaxed family and [assigned_t1_s2_t1_100]{.metric} on the T1-relaxed family ([assigned_t1_s2_phi100_outside_published_residual]{.metric}). At 95° on the S0-relaxed family the assigned S0 $\langle S^2\rangle$ is [assigned_s0_s2_s0_95]{.metric} ([assigned_s0_s2_phi95_s0_outside_published_residual]{.metric}). The S0-relaxed family has [both_assigned_neighbor_pair_count_s0]{.metric} both-assigned neighboring pairs; the T1-relaxed family has [both_assigned_neighbor_pair_count_t1]{.metric}.

## Discussion

The registered hypothesis was **supported**. Falsifier 1 is [falsifier_1_no_sign_change]{.metric}. Falsifier 2 is [falsifier_2_crossing_outside_90_105]{.metric}. Falsifier 3 is [falsifier_3_no_neighboring_pair]{.metric}. The S0-relaxed family flag is [hypothesis_supported_s0_family]{.metric}. The T1-relaxed family flag is [hypothesis_supported_t1_family]{.metric}. One-family-only sign change is [one_family_only_sign_change]{.metric}. On both constrained-CNNC geometry families, the same-geometry SF-TDA gap $E(\mathrm{T1})-E(\mathrm{S0})$ changes sign between [flip_phi_lo_deg]{.metric}° and [flip_phi_hi_deg]{.metric}°. Those interpolants are linear estimates from a 5° pair.

That is as far as the verdict goes. It is a verdict on our hypothesis and this window. The 2026-08-28 both-family 90–105° two-root result stays as published. This note narrows that 15° pair with a 5° fill. The 2024 calculation remains SF-TDDFT on AzPy and AzPyH+.[@Hillel2024] If a knowledgeable reader has already seen this denser same-geometry sign change on M4 at a comparable SF-TDDFT level, we would rather be told.

Assigned T1 $\langle S^2\rangle$ at 100° is [assigned_t1_s2_s0_100]{.metric} (S0-relaxed) and [assigned_t1_s2_t1_100]{.metric} (T1-relaxed). Those values sit in the triplet assignment bin used here ($1.5\le\langle S^2\rangle\le 2.5$) and outside the 2026-08-28 published residual 2.19–2.29. Assigned S0 $\langle S^2\rangle$ at 95° on the S0-relaxed family is [assigned_s0_s2_s0_95]{.metric}, in the singlet bin $\langle S^2\rangle\le 0.5$ and outside the published residual 0.14–0.31. At 100° the S0-relaxed unused root sits near $\langle S^2\rangle\approx 1$; the T1-relaxed unused root 1 lies outside the singlet bin. The 100° assignments still follow $\langle S^2\rangle$. Residual SF contamination on those new points is larger than the eight-point window published in 2026-08-28.

The limits that would overturn or shrink this reading are mostly on our side. The program is ORCA 6.1.1, not 5.0.3. The functional is LibXC(BHANDHLYP). The run is gas-phase; dichloromethane, the solvent of the 2024 experiments, is absent. Residual SF contamination is larger at 95° and 100° than on the reused 90° and 105° points. The zeros are linear interpolants of a 5° pair. An MECP search on the same SF surfaces, a solvent model, or a native-functional repair could move or remove those interpolants. We would treat a discrepancy as something to chase through our own setup first.

## Conclusion

Under ORCA 6.1.1 SF-TDA LibXC(BHANDHLYP) D3BJ/def2-QZVPP (RIJCOSX, gas phase), the same-geometry SF-TDA gap $E(\mathrm{T1})-E(\mathrm{S0})$ of constrained-CNNC M4 changes sign between [flip_phi_lo_deg]{.metric}° and [flip_phi_hi_deg]{.metric}° on both geometry families after a 5° fill of the 90–105° window. On the S0-relaxed family the gap is [deltae_kjmol_s0_100]{.metric} kJ/mol at 100° and [deltae_kjmol_s0_105]{.metric} kJ/mol at 105°, with linear interpolant [crossing_phi_deg_s0]{.metric}°. On the T1-relaxed family the gap is [deltae_kjmol_t1_100]{.metric} kJ/mol at 100° and [deltae_kjmol_t1_105]{.metric} kJ/mol at 105°, with linear interpolant [crossing_phi_deg_t1]{.metric}°.

The next experiment is an MECP search on the same SF surfaces near those interpolants. Keep S0 and T1 as two roots from one SF manifold, and ask whether a located crossing sits near [crossing_phi_deg_s0]{.metric}° on the S0-relaxed family and near [crossing_phi_deg_t1]{.metric}° on the T1-relaxed family.

## References
