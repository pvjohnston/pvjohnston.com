#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const experimentDir = dirname(fileURLToPath(import.meta.url));
const root = resolve(experimentDir, '../..');
const outputPath = resolve(experimentDir, 'metrics.json');
const resultsPath = resolve(experimentDir, 'results.json');
const checkOnly = process.argv.includes('--check');
const inputPaths = [
  'research/smx-single-surface-thermochemistry/PREREGISTRATION.md',
  'research/smx-single-surface-thermochemistry/inputs.json',
  'research/smx-single-surface-thermochemistry/thermo_analysis.py',
  'research/smx-single-surface-thermochemistry/results.json',
];

const sha256 = (path) => createHash('sha256')
  .update(readFileSync(resolve(root, path)))
  .digest('hex');

const fixed = (value, digits, description, unit) => ({
  type: 'number',
  value,
  format: { style: 'fixed', digits },
  description,
  ...(unit ? { unit } : {}),
});

const percent = (value, digits, description) => ({
  type: 'number',
  value,
  format: { style: 'percent', digits },
  description,
  unit: 'ratio',
});

const boolean = (value, description) => ({
  type: 'boolean',
  value,
  description,
});

const H2KJ = 2625.4996394799;

function build(generatedAt) {
  if (!existsSync(resultsPath)) {
    throw new Error(
      `${relative(root, resultsPath)} does not exist yet; complete the Colab DFT run and thermo_analysis.py first.`,
    );
  }
  const result = JSON.parse(readFileSync(resultsPath, 'utf8'));
  const source = result.source_preflight;
  const elec = result.single_surface_electronic_baseline;
  const rrho = result.primary_single_surface_analysis.rrho;
  const mrrho = result.primary_single_surface_analysis.mrrho50;
  const compRrho = result.secondary_source_plus_dft_thermo_diagnostic.rrho;
  const compMrrho = result.secondary_source_plus_dft_thermo_diagnostic.mrrho50;
  const runs = result.runs;
  const metrics = {};

  const aGCorrRrho = runs.A.thermochemistry.rrho.thermochemical_correction_hartree;
  const aGCorrMrrho = runs.A.thermochemistry.mrrho50.thermochemical_correction_hartree;

  let totalWallSec = 0;
  let totalHessSec = 0;
  const lowestModes = [];
  const startRmsds = [];

  for (const conformer of ['A', 'B', 'C', 'D']) {
    const key = conformer.toLowerCase();
    const run = runs[conformer];
    totalWallSec += run.timings_seconds.total;
    totalHessSec += run.timings_seconds.hessian;
    lowestModes.push(run.lowest_six_frequencies_cm[0]);
    startRmsds.push(run.start_to_opt_heavy_atom_rmsd_angstrom);

    metrics[`source_population_${key}`] = percent(
      source.source_electronic_populations[conformer],
      1,
      `Source electronic-energy Boltzmann population of conformer ${conformer} at 298.15 K`,
    );
    metrics[`elec_population_${key}`] = percent(
      elec.populations[conformer],
      1,
      `Single-surface B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water) electronic Boltzmann population of conformer ${conformer} at 298.15 K`,
    );
    metrics[`elec_rel_energy_${key}_kj_mol`] = fixed(
      elec.relative_energies_kj_per_mol[conformer],
      2,
      `Single-surface relative electronic energy of conformer ${conformer}`,
      'kJ/mol',
    );
    metrics[`abs_energy_diff_from_source_${key}_meh`] = fixed(
      Math.abs(run.electronic_energy_hartree - source.source_electronic_energies_hartree[conformer]) * 1000.0,
      2,
      `Absolute electronic-energy difference from the published Q-Chem value for conformer ${conformer}`,
      'mEh',
    );
    metrics[`rrho_population_${key}`] = percent(
      rrho.populations[conformer],
      1,
      `Single-surface pure-RRHO Boltzmann population of conformer ${conformer} at 298.15 K`,
    );
    metrics[`mrrho50_population_${key}`] = percent(
      mrrho.populations[conformer],
      1,
      `Single-surface 50 cm^-1 modified-RRHO Boltzmann population of conformer ${conformer} at 298.15 K`,
    );
    metrics[`rrho_rel_free_energy_${key}_kj_mol`] = fixed(
      rrho.relative_energies_kj_per_mol[conformer],
      2,
      `Single-surface pure-RRHO relative free energy of conformer ${conformer} at 298.15 K`,
      'kJ/mol',
    );
    metrics[`mrrho50_rel_free_energy_${key}_kj_mol`] = fixed(
      mrrho.relative_energies_kj_per_mol[conformer],
      2,
      `Single-surface 50 cm^-1 modified-RRHO relative free energy of conformer ${conformer} at 298.15 K`,
      'kJ/mol',
    );
    metrics[`ddg_corr_rrho_from_a_${key}_kj_mol`] = fixed(
      (run.thermochemistry.rrho.thermochemical_correction_hartree - aGCorrRrho) * H2KJ,
      2,
      `Pure-RRHO thermochemical free-energy correction of conformer ${conformer} relative to A`,
      'kJ/mol',
    );
    metrics[`ddg_corr_mrrho50_from_a_${key}_kj_mol`] = fixed(
      (run.thermochemistry.mrrho50.thermochemical_correction_hartree - aGCorrMrrho) * H2KJ,
      2,
      `50 cm^-1 modified-RRHO thermochemical free-energy correction of conformer ${conformer} relative to A`,
      'kJ/mol',
    );
    metrics[`lowest_freq_${key}_cm`] = fixed(
      run.lowest_six_frequencies_cm[0],
      1,
      `Lowest harmonic vibrational frequency of conformer ${conformer}`,
      'cm^-1',
    );
    metrics[`second_freq_${key}_cm`] = fixed(
      run.lowest_six_frequencies_cm[1],
      1,
      `Second-lowest harmonic vibrational frequency of conformer ${conformer}`,
      'cm^-1',
    );
    metrics[`third_freq_${key}_cm`] = fixed(
      run.lowest_six_frequencies_cm[2],
      1,
      `Third-lowest harmonic vibrational frequency of conformer ${conformer}`,
      'cm^-1',
    );
    metrics[`start_opt_rmsd_${key}_angstrom`] = fixed(
      run.start_to_opt_heavy_atom_rmsd_angstrom,
      3,
      `Heavy-atom Kabsch RMSD between published and re-optimized conformer ${conformer}`,
      'angstrom',
    );
    metrics[`source_plus_dft_rrho_population_${key}`] = percent(
      compRrho.populations[conformer],
      1,
      `Secondary composite (source electronic + single-surface DFT pure-RRHO) population of conformer ${conformer}`,
    );
    metrics[`source_plus_dft_mrrho50_population_${key}`] = percent(
      compMrrho.populations[conformer],
      1,
      `Secondary composite (source electronic + single-surface DFT mRRHO-50) population of conformer ${conformer}`,
    );
  }

  const pairValues = Object.values(result.fidelity.distinct_conformer_pair_rmsd_angstrom);
  const ddgRrhoVals = ['A', 'B', 'C', 'D'].map(
    (c) => (runs[c].thermochemistry.rrho.thermochemical_correction_hartree - aGCorrRrho) * H2KJ,
  );
  const ddgMrrhoVals = ['A', 'B', 'C', 'D'].map(
    (c) => (runs[c].thermochemistry.mrrho50.thermochemical_correction_hartree - aGCorrMrrho) * H2KJ,
  );

  metrics.ddg_corr_rrho_span_kj_mol = fixed(
    Math.max(...ddgRrhoVals) - Math.min(...ddgRrhoVals),
    2,
    'Conformer-to-conformer spread of pure-RRHO free-energy corrections across A-D',
    'kJ/mol',
  );
  metrics.ddg_corr_mrrho50_span_kj_mol = fixed(
    Math.max(...ddgMrrhoVals) - Math.min(...ddgMrrhoVals),
    2,
    'Conformer-to-conformer spread of 50 cm^-1 modified-RRHO free-energy corrections across A-D',
    'kJ/mol',
  );
  metrics.source_plus_dft_rrho_span_kj_mol = fixed(
    compRrho.span_kj_per_mol,
    2,
    'Free-energy span across A-D when single-surface DFT pure-RRHO corrections are added to source electronic energies',
    'kJ/mol',
  );
  metrics.source_plus_dft_mrrho50_span_kj_mol = fixed(
    compMrrho.span_kj_per_mol,
    2,
    'Free-energy span across A-D when single-surface DFT mRRHO-50 corrections are added to source electronic energies',
    'kJ/mol',
  );

  metrics.elec_span_kj_mol = fixed(
    elec.span_kj_per_mol,
    2,
    'Electronic-energy span across conformers A-D on the single B3LYPG-D3(BJ)/def2-TZVP + IEF-PCM(water) surface',
    'kJ/mol',
  );
  metrics.elec_effective_conformer_count = fixed(
    elec.effective_conformer_count,
    2,
    'Effective conformer count on the single-surface electronic baseline',
    'conformers',
  );
  metrics.elec_max_shift_from_source_pp = fixed(
    elec.maximum_absolute_population_shift_pp,
    1,
    'Maximum absolute electronic-only population difference between single-surface DFT and published Q-Chem baseline',
    'percentage points',
  );
  metrics.rrho_span_kj_mol = fixed(
    rrho.span_kj_per_mol,
    2,
    'Free-energy span across conformers A-D in the single-surface pure-RRHO arm',
    'kJ/mol',
  );
  metrics.mrrho50_span_kj_mol = fixed(
    mrrho.span_kj_per_mol,
    2,
    'Free-energy span across conformers A-D in the single-surface 50 cm^-1 modified-RRHO arm',
    'kJ/mol',
  );
  metrics.rrho_max_population_shift_pp = fixed(
    rrho.maximum_absolute_population_shift_pp,
    1,
    'Maximum absolute population shift from the single-surface electronic baseline in the pure-RRHO arm',
    'percentage points',
  );
  metrics.mrrho50_max_population_shift_pp = fixed(
    mrrho.maximum_absolute_population_shift_pp,
    1,
    'Maximum absolute population shift from the single-surface electronic baseline in the 50 cm^-1 modified-RRHO arm',
    'percentage points',
  );
  metrics.rrho_effective_conformer_count = fixed(
    rrho.effective_conformer_count,
    2,
    'Effective conformer count in the single-surface pure-RRHO arm',
    'conformers',
  );
  metrics.mrrho50_effective_conformer_count = fixed(
    mrrho.effective_conformer_count,
    2,
    'Effective conformer count in the single-surface 50 cm^-1 modified-RRHO arm',
    'conformers',
  );
  metrics.source_plus_dft_rrho_max_shift_pp = fixed(
    compRrho.maximum_absolute_population_shift_pp,
    1,
    'Maximum absolute population shift from source baseline when single-surface DFT pure-RRHO corrections are added to source electronic energies',
    'percentage points',
  );
  metrics.source_plus_dft_mrrho50_max_shift_pp = fixed(
    compMrrho.maximum_absolute_population_shift_pp,
    1,
    'Maximum absolute population shift from source baseline when single-surface DFT mRRHO-50 corrections are added to source electronic energies',
    'percentage points',
  );
  metrics.source_plus_dft_rrho_effective_count = fixed(
    compRrho.effective_conformer_count,
    2,
    'Effective conformer count when single-surface DFT pure-RRHO corrections are added to source electronic energies',
    'conformers',
  );
  metrics.source_plus_dft_mrrho50_effective_count = fixed(
    compMrrho.effective_conformer_count,
    2,
    'Effective conformer count when single-surface DFT mRRHO-50 corrections are added to source electronic energies',
    'conformers',
  );
  metrics.lowest_mode_min_cm = fixed(
    Math.min(...lowestModes),
    1,
    'Minimum lowest harmonic vibrational mode across conformers A-D',
    'cm^-1',
  );
  metrics.lowest_mode_max_cm = fixed(
    Math.max(...lowestModes),
    1,
    'Maximum lowest harmonic vibrational mode across conformers A-D',
    'cm^-1',
  );
  metrics.min_start_opt_rmsd_angstrom = fixed(
    Math.min(...startRmsds),
    3,
    'Minimum start-to-optimized heavy-atom Kabsch RMSD across conformers A-D',
    'angstrom',
  );
  metrics.max_start_opt_rmsd_angstrom = fixed(
    Math.max(...startRmsds),
    3,
    'Maximum start-to-optimized heavy-atom Kabsch RMSD across conformers A-D',
    'angstrom',
  );
  metrics.min_pairwise_rmsd_angstrom = fixed(
    Math.min(...pairValues),
    2,
    'Minimum heavy-atom Kabsch RMSD among the six optimized conformer pairs',
    'angstrom',
  );
  metrics.max_pairwise_rmsd_angstrom = fixed(
    Math.max(...pairValues),
    2,
    'Maximum heavy-atom Kabsch RMSD among the six optimized conformer pairs',
    'angstrom',
  );
  metrics.total_wall_hours = fixed(
    totalWallSec / 3600.0,
    1,
    'Total wall-clock execution time for all four conformer optimizations and analytical Hessians on Colab',
    'hours',
  );
  metrics.mean_hessian_minutes = fixed(
    (totalHessSec / 4.0) / 60.0,
    1,
    'Mean analytical PCM Hessian wall-clock runtime per conformer on the Tesla T4 GPU',
    'minutes',
  );
  metrics.method_fidelity_passed = boolean(
    result.fidelity.passed,
    'Whether every preregistered convergence, gradient, frequency, thermo cross-check, and RMSD gate passed',
  );
  metrics.hypothesis_supported = boolean(
    result.verdict.hypothesis_supported,
    'Whether the preregistered single-surface concentration hypothesis was supported',
  );
  metrics.hypothesis_falsified = boolean(
    result.verdict.hypothesis_falsified,
    'Whether the preregistered single-surface concentration hypothesis was falsified',
  );
  metrics.result_inconclusive = boolean(
    result.verdict.result_inconclusive,
    'Whether the preregistered result was inconclusive',
  );

  return {
    schema_version: 1,
    experiment: 'smx-single-surface-thermochemistry',
    provenance: {
      generated_at: generatedAt,
      generator: relative(root, fileURLToPath(import.meta.url)),
      inputs: inputPaths.map((path) => ({ path, sha256: sha256(path) })),
    },
    metrics,
  };
}

const existing = existsSync(outputPath)
  ? JSON.parse(readFileSync(outputPath, 'utf8'))
  : null;
const generatedAt = checkOnly && existing?.provenance?.generated_at
  ? existing.provenance.generated_at
  : new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
const expected = `${JSON.stringify(build(generatedAt), null, 2)}\n`;

if (checkOnly) {
  if (!existing || readFileSync(outputPath, 'utf8') !== expected) {
    console.error(`${relative(root, outputPath)} is missing or stale`);
    process.exit(1);
  }
} else {
  writeFileSync(outputPath, expected);
}
