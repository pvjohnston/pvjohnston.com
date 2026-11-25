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

function build(generatedAt) {
  if (!existsSync(resultsPath)) {
    throw new Error(
      `${relative(root, resultsPath)} does not exist yet; complete the Colab DFT run and thermo_analysis.py first.`,
    );
  }
  const result = JSON.parse(readFileSync(resultsPath, 'utf8'));
  const elec = result.single_surface_electronic_baseline;
  const rrho = result.primary_single_surface_analysis.rrho;
  const mrrho = result.primary_single_surface_analysis.mrrho50;
  const compRrho = result.secondary_source_plus_dft_thermo_diagnostic.rrho;
  const compMrrho = result.secondary_source_plus_dft_thermo_diagnostic.mrrho50;
  const metrics = {};

  for (const conformer of ['A', 'B', 'C', 'D']) {
    const key = conformer.toLowerCase();
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
