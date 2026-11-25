# Preregistration: SMX single-surface hybrid-DFT thermochemistry

Frozen before the first sulfamethoxazole `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` calculation.

## Source relationship

This experiment is the direct single-surface follow-up named in the Conclusion of
`/posts/2026-08-03-does-the-near-uniform-smx-ensemble-survive-thermal-correction.html`
(`research/smx-conformer-thermochemistry/`) and logged on the research shelf under
*"Does the SMX ensemble concentrate under a same-level thermal correction?"*.

The primary literature source is Hannah Blackmon and Kristina D. Closser,
"Determination of ground-state structure and electronic excitations of
sulfamethoxazole using density functional theory," *Computational and
Theoretical Chemistry* **1264** (2026) 115931,
https://doi.org/10.1016/j.comptc.2026.115931.

Blackmon and Closser report four aqueous ground-state sulfamethoxazole (SMX)
minima, A–D, spanning 0.202 kJ/mol in electronic energy, and assign 298 K
Boltzmann populations of roughly one quarter each from electronic energies
alone. Their paper states that harmonic frequency calculations confirmed all
four structures as minima, but neither the frequencies nor thermally corrected
free energies appear in the paper or its supplement.

Our earlier note tested robustness using a two-level composite free energy
(`source_DFT_electronic + GFN2-xTB/ALPB_thermal_correction`) and falsified
near-uniformity in both registered rotor-cutoff arms (`rrho` and `mrrho50`),
concentrating the ensemble onto conformer A. Because a composite construction
mixes two potential energy surfaces, it could not separate a genuine thermal
concentration from an artifact of surface mixing.

This experiment eliminates the two-surface mixing by re-optimizing conformers
A–D and computing analytical harmonic Hessians on **one consistent hybrid-DFT +
implicit-water surface**: `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` in
PySCF/GPU4PySCF. It does not run Q-Chem or claim exact numerical equivalence
with the source authors' unreported PCM cavity discretization or integration
grid.

## Question, hypothesis, and falsifier

Question: Does the concentration of the sulfamethoxazole A–D conformer ensemble
survive when the electronic energies and the 298.15 K harmonic thermochemical
corrections come from the same hybrid-DFT + implicit-water surface?

Hypothesis: **Concentration survives on a single surface.** Relative to this
surface's own 298.15 K electronic-energy Boltzmann baseline, under **both**
registered thermochemistry arms (`rrho` and `mrrho50`):

1. the maximum absolute conformer-population shift from this surface's
   electronic-energy baseline is **at least 10.0 percentage points**
   (`max_i |p_free(i) - p_elec(i)| >= 10.0 pp`), **or**
2. the thermally corrected effective conformer count, `1 / sum_i p_free(i)^2`,
   is **strictly less than 3.5**.

Note that this concentration domain is the exact logical complement of the
near-uniform robustness domain (`max shift < 10.0 pp` **and** `N_eff >= 3.5`)
registered in `research/smx-conformer-thermochemistry/PREREGISTRATION.md`, so no
threshold was moved between the two notes.

Decision rule:

- **Supported** if every method-fidelity check passes and **both** `rrho` and
  `mrrho50` satisfy the concentration criterion above;
- **Falsified** if every method-fidelity check passes and **both** `rrho` and
  `mrrho50` remain inside the near-uniform region (`max shift < 10.0 pp` **and**
  `N_eff >= 3.5` relative to this surface's electronic baseline);
- **Inconclusive** if any method-fidelity check fails or if `rrho` and `mrrho50`
  fall on opposite sides of the boundary.

## Frozen computational protocol

Inputs are the four canonicalized 28-atom neutral singlet Cartesian geometries
(A–D) transcribed from the Blackmon and Closser supplement in
`research/smx-conformer-thermochemistry/inputs.json` (unchanged coordinates,
common atom order).

For each starting conformer A, B, C, and D:

1. Construct a conventional (exact 4-center integral, no density fitting)
   restricted Kohn–Sham object in GPU4PySCF/PySCF:
   - functional: `xc = 'b3lypg'` (Q-Chem/Gaussian B3LYP VWN1RPA convention);
   - empirical dispersion: `disp = 'd3bj'` (Becke–Johnson damped D3);
   - orbital basis: `def2-tzvp`;
   - XC quadrature grid: `grids.level = 4`;
   - implicit solvent: `IEF-PCM` water (`eps = 78.3553`, cavity surface
     `lebedev_order = 29`);
   - SCF convergence: `conv_tol = 1.0e-10` Eh, `conv_tol_grad = 1.0e-7` Eh/Bohr,
     `max_cycle = 200`.
2. Optimize the geometry from the published starting structure using `geomeTRIC`
   (`pyscf.geomopt.geometric_solver.optimize`) with tight convergence settings:
   `convergence_energy = 1.0e-6` Eh, `convergence_grms = 1.0e-4` Eh/Bohr,
   `convergence_gmax = 3.0e-4` Eh/Bohr, `convergence_drms = 4.0e-4` Bohr,
   `convergence_dmax = 1.2e-3` Bohr, `maxsteps = 150`.
3. Rebuild a fresh mean-field object at the converged geometry, converge SCF,
   evaluate the analytical nuclear gradient to verify stationarity, and compute
   the analytical nuclear Hessian (`mf.Hessian().kernel()`) on the same
   `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` surface.
4. Project out overall translation and rotation from the mass-weighted Hessian
   using standard isotope-averaged atomic weights (`pyscf` default) to obtain
   the 78 harmonic vibrational frequencies at 298.15 K and 101325 Pa
   (rotational symmetry number `1`, frequency scale factor `1.0`). Modes between
   `-20.0 cm^-1` and `0.0 cm^-1`, if any arise from numerical PCM cavity/grid
   discretization, are inverted in sign (`|nu|`), matching the `-20.0 cm^-1`
   `imagthr` convention of the first note; any mode below `-20.0 cm^-1` fails
   the method-fidelity gate.
5. Evaluate 298.15 K free-energy corrections `dG_corr(i)` under two registered
   rotor-cutoff arms:
   - `rrho`: standard rigid-rotor harmonic-oscillator (`w0 = 0.0 cm^-1`);
   - `mrrho50`: Grimme's modified-RRHO (`w0 = 50.0 cm^-1`, `alpha = 4`,
     `B_av = 1.0e-44 kg m^2`; Grimme, *Chem. Eur. J.* **18**, 2012, 9955–9964),
     damping low-frequency vibrational entropies toward a 1D free rotor while
     retaining harmonic zero-point energy and thermal enthalpy.
6. Compute single-surface total free energies
   `G_single(i) = E_single_DFT(i) + dG_corr(i)` and normalized 298.15 K
   Boltzmann populations `p_free(i)`, alongside this surface's electronic-only
   298.15 K Boltzmann baseline `p_elec(i)` from `E_single_DFT(i)`.

## Method-fidelity gate

The primary verdict is automatically **inconclusive** if any of the following
occur:

1. SCF, `geomeTRIC` optimization, or the analytical Hessian fails or does not
   converge for any of A–D;
2. at the optimized geometry, the analytical Cartesian gradient exceeds
   `3.0e-4` Eh/Bohr RMS or `1.0e-3` Eh/Bohr maximum component;
3. any optimized conformer has a projected vibrational frequency strictly below
   `-20.0 cm^-1`, or the pure-Python normal-mode analysis disagrees with PySCF's
   `harmonic_analysis` / `thermo.thermo` RRHO free energy by more than
   `1.0e-5` Eh;
4. any pair of optimized conformers A–D has heavy-atom aligned Kabsch RMSD
   below `0.10` angstrom (basin collapse); or
5. any optimized conformer drifts by more than `0.50` angstrom heavy-atom
   aligned Kabsch RMSD from its published starting geometry (basin escape).

## Primary and secondary outputs

Primary outputs (governing the verdict):

- single-surface `B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water)` electronic energies
  and 298.15 K electronic-only Boltzmann populations `p_elec(A..D)` and `N_eff`;
- single-surface `rrho` and `mrrho50` thermochemical corrections `dG_corr(A..D)`,
  relative free energies, and 298.15 K Boltzmann populations `p_free(A..D)`;
- maximum absolute shift `max_i |p_free(i) - p_elec(i)|` (in percentage points)
  and effective conformer count `N_eff` in each arm; and
- pass/fail of the method-fidelity gate, per-arm concentration gates, and the
  supported / falsified / inconclusive verdict.

Secondary diagnostic outputs (reported for physical interpretation; do not
determine the primary verdict):

- comparison of this surface's electronic-only relative energies and populations
  against Blackmon and Closser's published electronic baseline (isolating how
  much D3(BJ) dispersion and IEF-PCM cavity settings shift the bare electronic
  spread before thermal corrections are added);
- a hybrid diagnostic adding this surface's DFT/IEF-PCM `dG_corr(A..D)` to
  Blackmon and Closser's published electronic energies (directly isolating the
  DFT/IEF-PCM Hessian vs. the first note's GFN2-xTB/ALPB Hessian on identical
  electronic energies);
- lowest harmonic frequencies, zero-point energies, thermal enthalpies, and
  vibrational entropies per conformer; and
- heavy-atom Kabsch RMSDs (start-to-optimized and all six pairwise A–D pairs).

No outcome will be used to claim an error in Q-Chem, infer experimental aqueous
populations beyond implicit-solvent DFT, or extrapolate to excited-state
branching yields.

## Stopping rule

The canonical GPU run executes conformers A, B, C, and D once under the frozen
settings above (preceded only by an `H2O` pipeline smoke test that touches no
SMX structure). Completed conformer checkpoints are immutable on resume. No
functional, basis set, dispersion model, PCM parameter, rotor cutoff, or
decision threshold will be added or tuned after inspecting any SMX output.
