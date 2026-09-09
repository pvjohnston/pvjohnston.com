#!/usr/bin/env node

// Publication metrics for the Hillel M4 denser 90–105° same-geometry
// SF-TDA bracket. Numbers are flattened from the committed scored dump.
// Do not hand-author metrics.json. Do not invent energies: 95°/100°
// contribute ΔE only; 90°/105° reuse published tworoot totals.

import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const experimentDir = dirname(fileURLToPath(import.meta.url));
const root = resolve(experimentDir, '../..');
const outputPath = resolve(experimentDir, 'metrics.json');
const dumpInput = 'research/hillel-m4-sft-dense-bracket/results/dense_bracket_metrics.json';
const checkOnly = process.argv.includes('--check');

const REQUIRED_PHIS = [90, 95, 100, 105];
const FAMILIES = [
  { id: 's0_relaxed', key: 's0', label: 'S0-relaxed' },
  { id: 't1_relaxed', key: 't1', label: 'T1-relaxed' },
];
const REUSED_PHIS = [90, 105];
const NEW_PHIS = [95, 100];

const sha256 = (path) => createHash('sha256')
  .update(readFileSync(resolve(root, path)))
  .digest('hex');

const num = (value, digits, description, unit) => ({
  type: 'number',
  value,
  format: { style: 'fixed', digits },
  description,
  ...(unit ? { unit } : {}),
});

const raw = (value, description, unit) => ({
  type: 'number',
  value,
  format: { style: 'raw' },
  description,
  ...(unit ? { unit } : {}),
});

const integer = (value, description, unit) => ({
  type: 'integer',
  value,
  description,
  ...(unit ? { unit } : {}),
});

const boolean = (value, description) => ({
  type: 'boolean',
  value,
  description,
});

function assertClose(actual, expected, label, tol = 1e-9) {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)
      || Math.abs(actual - expected) > tol) {
    throw new Error(`${label}: ${actual} !== ${expected}`);
  }
}

function requireFinite(value, label) {
  if (!Number.isFinite(value)) {
    throw new Error(`${label} is not finite: ${value}`);
  }
  return value;
}

function requireBool(value, label) {
  if (typeof value !== 'boolean') {
    throw new Error(`${label} must be boolean, got ${value}`);
  }
  return value;
}

function linearZero(x0, y0, x1, y1) {
  if (y0 === 0) return x0;
  if (y1 === 0) return x1;
  if (y0 * y1 > 0) return null;
  return x0 - (y0 * (x1 - x0)) / (y1 - y0);
}

function pairEnds(pair) {
  if (Array.isArray(pair.pair) && pair.pair.length === 2) {
    return [Number(pair.pair[0]), Number(pair.pair[1])];
  }
  return [Number(pair.phi_a), Number(pair.phi_b)];
}

function expectedPointFile(familyId, phi) {
  const surf = familyId === 's0_relaxed' ? 's0' : familyId === 't1_relaxed' ? 't1' : null;
  if (!surf) {
    throw new Error(`no expected output filename for geom_family ${familyId}`);
  }
  return `m4_${surf}_phi_${String(phi).padStart(3, '0')}.out`;
}

function pairInterpolantOf(pair) {
  if (typeof pair.interpolated_crossing_phi_deg === 'number') {
    return pair.interpolated_crossing_phi_deg;
  }
  return null;
}

function build(generatedAt) {
  const dump = JSON.parse(readFileSync(resolve(root, dumpInput), 'utf8'));
  const experimentId = dump.experiment ?? dump.slug;
  if (experimentId !== 'hillel-m4-sft-dense-bracket') {
    throw new Error(`${dumpInput}: experiment/slug must be hillel-m4-sft-dense-bracket`);
  }

  const conversion = requireFinite(
    dump.conversion_Eh_to_kJmol,
    'conversion_Eh_to_kJmol',
  );
  assertClose(conversion, 2625.49963831, 'conversion_Eh_to_kJmol', 0);

  if (dump.overall_verdict !== 'supported') {
    throw new Error(`${dumpInput}: overall_verdict must be supported, got ${dump.overall_verdict}`);
  }

  const points = Array.isArray(dump.points) ? dump.points : [];
  const byFamily = {};
  for (const family of FAMILIES) {
    byFamily[family.id] = {};
  }
  for (const point of points) {
    const family = point?.geom_family;
    const phi = point?.phi_deg;
    if (!byFamily[family]) {
      throw new Error(`${dumpInput}: unexpected geom_family ${family}`);
    }
    if (!REQUIRED_PHIS.includes(Number(phi))) {
      throw new Error(`${dumpInput}: unexpected phi_deg ${phi}`);
    }
    if (byFamily[family][String(phi)]) {
      throw new Error(`${dumpInput}: duplicate ${family} ${phi}°`);
    }
    byFamily[family][String(phi)] = point;
  }

  const familyData = {};
  let bothAssignedPointCount = 0;
  for (const family of FAMILIES) {
    const slots = {};
    for (const phi of REQUIRED_PHIS) {
      const point = byFamily[family.id][String(phi)];
      if (!point) {
        throw new Error(`${dumpInput}: missing ${family.id} point at ${phi}°`);
      }
      const expectedFile = expectedPointFile(family.id, phi);
      const pointFile = point.file;
      if (typeof pointFile !== 'string' || pointFile.includes('/') || pointFile.includes('\\')) {
        throw new Error(`${family.id} ${phi}°: file must be a filename only`);
      }
      if (pointFile !== expectedFile) {
        throw new Error(`${family.id} ${phi}°: file ${pointFile} !== ${expectedFile}`);
      }
      if (point.both_assigned === true) {
        bothAssignedPointCount += 1;
      }
      if (point.both_assigned !== true) {
        throw new Error(`${family.id} ${phi}°: required window point must be both-assigned`);
      }
      const reused = point.reused_from_tworoot === true;
      if (REUSED_PHIS.includes(phi) && !reused) {
        throw new Error(`${family.id} ${phi}°: must be reused from tworoot`);
      }
      if (NEW_PHIS.includes(phi) && reused) {
        throw new Error(`${family.id} ${phi}°: new fill point must not be marked reused`);
      }
      const deltaEh = requireFinite(point.deltaE_Eh, `${family.id} ${phi} deltaE_Eh`);
      const deltaE = requireFinite(point.deltaE_kJmol, `${family.id} ${phi} deltaE_kJmol`);
      assertClose(deltaEh * conversion, deltaE, `${family.id} ${phi} ΔE from Eh`, 1e-8);
      if (reused) {
        const s0E = requireFinite(point.s0?.E_Eh, `${family.id} ${phi} s0.E_Eh`);
        const t1E = requireFinite(point.t1?.E_Eh, `${family.id} ${phi} t1.E_Eh`);
        assertClose(t1E - s0E, deltaEh, `${family.id} ${phi} reused energy difference`, 1e-12);
        slots[phi] = {
          reused,
          deltaEh,
          deltaE,
          s0E,
          t1E,
          s0s2: requireFinite(point.s0?.S2, `${family.id} ${phi} s0.S2`),
          t1s2: requireFinite(point.t1?.S2, `${family.id} ${phi} t1.S2`),
        };
      } else {
        if (point.s0?.E_Eh != null || point.t1?.E_Eh != null) {
          throw new Error(`${family.id} ${phi}°: new-point absolute energies are not in the scored dump`);
        }
        slots[phi] = { reused, deltaEh, deltaE };
      }
    }
    familyData[family.id] = slots;
  }

  const pairs = Array.isArray(dump.neighboring_pairs) ? dump.neighboring_pairs : [];
  const familyFlags = {};
  for (const family of FAMILIES) {
    const slots = familyData[family.id];
    const familyPairs = pairs.filter((pair) => pair.geom_family === family.id);
    const claimPair = familyPairs.find((pair) => {
      const [a, b] = pairEnds(pair);
      return a === 100 && b === 105;
    });
    if (!claimPair) {
      throw new Error(`${dumpInput}: missing ${family.id} neighboring_pairs 100/105 entry`);
    }
    const pairInterpolant = pairInterpolantOf(claimPair);
    const derivedZero = linearZero(
      100, slots[100].deltaEh, 105, slots[105].deltaEh,
    );
    if (derivedZero === null) {
      throw new Error(`${family.id} 100/105 pair has no ΔE sign change`);
    }
    if (pairInterpolant === null) {
      throw new Error(`${family.id} 100/105 sign change missing interpolant`);
    }
    assertClose(derivedZero, pairInterpolant, `${family.id} 100/105 derived interpolant`, 1e-8);
    const storedRaw = dump[`crossing_phi_deg_${family.key}`];
    const storedCrossing = requireFinite(storedRaw, `crossing_phi_deg_${family.key}`);
    assertClose(storedCrossing, pairInterpolant, `${family.id} stored crossing vs 100/105 interpolant`, 1e-8);

    const usablePairs = familyPairs.filter((pair) => pair.both_assigned === true);
    const neighborSteps = [[90, 95], [95, 100], [100, 105]];
    const signChangePairs = neighborSteps.filter(([a, b]) => slots[a].deltaEh * slots[b].deltaEh < 0);
    if (signChangePairs.length !== 1 || signChangePairs[0][0] !== 100 || signChangePairs[0][1] !== 105) {
      throw new Error(`${family.id}: expected a single 100/105 sign change, got ${JSON.stringify(signChangePairs)}`);
    }
    const familySupported = requireBool(
      dump[`hypothesis_supported_${family.key}_family`],
      `hypothesis_supported_${family.key}_family`,
    );
    const derivedFamilySupported = signChangePairs.length > 0
      && storedCrossing >= 90
      && storedCrossing <= 105
      && usablePairs.length > 0;
    if (familySupported !== derivedFamilySupported) {
      throw new Error(`hypothesis_supported_${family.key}_family ${familySupported} !== ${derivedFamilySupported}`);
    }
    familyFlags[family.id] = {
      storedCrossing,
      signChangeCount: signChangePairs.length,
      usablePairCount: usablePairs.length,
      familySupported,
    };
  }

  const s0Flags = familyFlags.s0_relaxed;
  const t1Flags = familyFlags.t1_relaxed;
  const falsifier1 = requireBool(dump.falsifier_1_no_sign_change, 'falsifier_1_no_sign_change');
  const falsifier2 = requireBool(dump.falsifier_2_crossing_outside_90_105, 'falsifier_2_crossing_outside_90_105');
  const falsifier3 = requireBool(dump.falsifier_3_no_neighboring_pair, 'falsifier_3_no_neighboring_pair');
  const hypothesisSupported = requireBool(dump.hypothesis_supported, 'hypothesis_supported');

  const derivedF1 = s0Flags.signChangeCount === 0 && t1Flags.signChangeCount === 0;
  const derivedF2 = (s0Flags.storedCrossing < 90 || s0Flags.storedCrossing > 105)
    || (t1Flags.storedCrossing < 90 || t1Flags.storedCrossing > 105);
  const derivedF3 = s0Flags.usablePairCount === 0 || t1Flags.usablePairCount === 0;
  if (falsifier1 !== derivedF1) {
    throw new Error(`falsifier_1_no_sign_change ${falsifier1} !== ${derivedF1}`);
  }
  if (falsifier2 !== derivedF2) {
    throw new Error(`falsifier_2_crossing_outside_90_105 ${falsifier2} !== ${derivedF2}`);
  }
  if (falsifier3 !== derivedF3) {
    throw new Error(`falsifier_3_no_neighboring_pair ${falsifier3} !== ${derivedF3}`);
  }
  const derivedSupported = s0Flags.familySupported && t1Flags.familySupported
    && !falsifier1 && !falsifier2 && !falsifier3;
  if (hypothesisSupported !== derivedSupported) {
    throw new Error(`hypothesis_supported ${hypothesisSupported} !== ${derivedSupported}`);
  }
  const oneFamilyOnlySignChange = s0Flags.familySupported !== t1Flags.familySupported;

  const flags = dump.contamination_flags ?? {};
  const t1s2_100_s0 = requireFinite(flags.assigned_t1_s2_phi100_s0_relaxed, 'assigned_t1_s2_phi100_s0_relaxed');
  const t1s2_100_t1 = requireFinite(flags.assigned_t1_s2_phi100_t1_relaxed, 'assigned_t1_s2_phi100_t1_relaxed');
  const s0s2_95_s0 = requireFinite(flags.assigned_s0_s2_phi95_s0_relaxed, 'assigned_s0_s2_phi95_s0_relaxed');
  assertClose(t1s2_100_s0, 1.636, 'assigned_t1_s2_phi100_s0_relaxed', 0);
  assertClose(t1s2_100_t1, 1.837, 'assigned_t1_s2_phi100_t1_relaxed', 0);
  assertClose(s0s2_95_s0, 0.437935, 'assigned_s0_s2_phi95_s0_relaxed', 0);
  if (!(t1s2_100_s0 > 1.5 && t1s2_100_s0 < 2.8)) {
    throw new Error(`S0-relaxed 100° T1 ⟨S²⟩=${t1s2_100_s0} is not in the triplet bin`);
  }
  if (!(t1s2_100_t1 > 1.5 && t1s2_100_t1 < 2.8)) {
    throw new Error(`T1-relaxed 100° T1 ⟨S²⟩=${t1s2_100_t1} is not in the triplet bin`);
  }
  if (!(s0s2_95_s0 < 0.8)) {
    throw new Error(`S0-relaxed 95° S0 ⟨S²⟩=${s0s2_95_s0} is not in the singlet bin`);
  }
  const unusedBoth = requireBool(
    flags.unused_sf_root_near_s2_1_at_phi100_both_families,
    'unused_sf_root_near_s2_1_at_phi100_both_families',
  );
  if (unusedBoth !== true) {
    throw new Error('expected unused SF root near ⟨S²⟩≈1 at φ=100° on both families');
  }

  const metrics = {
    crossing_phi_deg_s0: num(s0Flags.storedCrossing, 2,
      'Linear interpolant of same-geometry ΔE=E(T1)−E(S0) on the S0-relaxed 100°/105° pair',
      'deg'),
    crossing_phi_deg_t1: num(t1Flags.storedCrossing, 2,
      'Linear interpolant of same-geometry ΔE=E(T1)−E(S0) on the T1-relaxed 100°/105° pair',
      'deg'),
    hypothesis_supported: boolean(hypothesisSupported,
      'Registered hypothesis supported: both families have a both-assigned same-geometry ΔE sign change inside 90–105°'),
    hypothesis_supported_s0_family: boolean(s0Flags.familySupported,
      'S0-relaxed family has a both-assigned same-geometry ΔE sign change inside 90–105°'),
    hypothesis_supported_t1_family: boolean(t1Flags.familySupported,
      'T1-relaxed family has a both-assigned same-geometry ΔE sign change inside 90–105°'),
    one_family_only_sign_change: boolean(oneFamilyOnlySignChange,
      'Exactly one geometry family has a both-assigned same-geometry ΔE sign change inside 90–105°'),
    both_assigned_point_count: integer(bothAssignedPointCount,
      'Number of denser-bracket same-geometry points that are both-assigned'),
    both_assigned_neighbor_pair_count: integer(
      s0Flags.usablePairCount + t1Flags.usablePairCount,
      'Number of neighboring pairs that are both-assigned, both families'),
    both_assigned_neighbor_pair_count_s0: integer(s0Flags.usablePairCount,
      'Number of both-assigned neighboring pairs on the S0-relaxed family'),
    both_assigned_neighbor_pair_count_t1: integer(t1Flags.usablePairCount,
      'Number of both-assigned neighboring pairs on the T1-relaxed family'),
    falsifier_1_no_sign_change: boolean(falsifier1,
      'Falsifier 1: neither family has a both-assigned same-geometry ΔE sign change on a neighboring pair in 90–105°'),
    falsifier_2_crossing_outside_90_105: boolean(falsifier2,
      'Falsifier 2: a family has a sign change whose interpolant lies outside 90–105°'),
    falsifier_3_no_neighboring_pair: boolean(falsifier3,
      'Falsifier 3: a family has no neighboring both-assigned pair'),
    flip_phi_lo_deg: integer(100,
      'Lower endpoint of the neighboring pair that changes sign of ΔE on both families',
      'deg'),
    flip_phi_hi_deg: integer(105,
      'Upper endpoint of the neighboring pair that changes sign of ΔE on both families',
      'deg'),
    unused_sf_root_near_s2_1_phi100_both_families: boolean(true,
      'At φ=100° both families have an unused SF root near ⟨S²⟩≈1'),
    assigned_t1_s2_s0_100: num(t1s2_100_s0, 3,
      'Assigned SF-T1 ⟨S²⟩ on the S0-relaxed geometry at CNNC 100°'),
    assigned_t1_s2_t1_100: num(t1s2_100_t1, 3,
      'Assigned SF-T1 ⟨S²⟩ on the T1-relaxed geometry at CNNC 100°'),
    assigned_s0_s2_s0_95: num(s0s2_95_s0, 6,
      'Assigned SF-S0 ⟨S²⟩ on the S0-relaxed geometry at CNNC 95°'),
    assigned_t1_s2_phi100_outside_published_residual: boolean(true,
      'Assigned T1 ⟨S²⟩ at 100° sits in the triplet bin and outside the 2026-08-28 published residual 2.19–2.29 on both families'),
    assigned_s0_s2_phi95_s0_outside_published_residual: boolean(true,
      'Assigned S0 ⟨S²⟩ at 95° on the S0-relaxed family sits in the singlet bin and outside the 2026-08-28 published residual 0.14–0.31'),
  };

  for (const family of FAMILIES) {
    for (const phi of REQUIRED_PHIS) {
      const point = familyData[family.id][phi];
      metrics[`deltae_eh_${family.key}_${phi}`] = raw(point.deltaEh,
        `Same-geometry ΔE=E(T1)−E(S0) on the ${family.label} geometry at CNNC ${phi}°`,
        'Eh');
      metrics[`deltae_kjmol_${family.key}_${phi}`] = num(point.deltaE, 2,
        `Same-geometry ΔE=E(T1)−E(S0) on the ${family.label} geometry at CNNC ${phi}°`,
        'kJ/mol');
      if (point.reused) {
        metrics[`s0_e_eh_${family.key}_${phi}`] = raw(point.s0E,
          `Assigned SF-S0 total energy reused from the published two-root rematch on the ${family.label} geometry at CNNC ${phi}°`,
          'Eh');
        metrics[`t1_e_eh_${family.key}_${phi}`] = raw(point.t1E,
          `Assigned SF-T1 total energy reused from the published two-root rematch on the ${family.label} geometry at CNNC ${phi}°`,
          'Eh');
      }
    }
  }

  return {
    schema_version: 1,
    experiment: 'hillel-m4-sft-dense-bracket',
    provenance: {
      generated_at: generatedAt,
      generator: relative(root, fileURLToPath(import.meta.url)),
      inputs: [{ path: dumpInput, sha256: sha256(dumpInput) }],
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
