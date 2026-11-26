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
  'research/batch-size-divergence-onset/PREREGISTRATION.md',
  'research/batch-size-divergence-onset/inputs.json',
  'research/batch-size-divergence-onset/analyze_divergence.py',
  'research/batch-size-divergence-onset/results.json',
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

function build(generatedAt) {
  if (!existsSync(resultsPath)) {
    throw new Error(`${relative(root, resultsPath)} does not exist yet.`);
  }
  const result = JSON.parse(readFileSync(resultsPath, 'utf8'));
  const sum = result.summary;
  const anova = sum.two_way_anova_all_prompts;
  const mm = result.smoke_and_mm_check;
  const metrics = {
    n_prompts_total: integer(sum.n_prompts_total, 'Total preregistered prompts evaluated', 'prompts'),
    n_diverging_prompts: integer(sum.n_diverging_prompts, 'Prompts that diverged from B=1 within 256 tokens at one or more B >= 2', 'prompts'),
    median_within_prompt_censored_range_tokens: fixed(
      sum.median_within_prompt_censored_range_tokens,
      1,
      'Median within-prompt onset range across B >= 2 for diverging prompts (with non-diverging cells censored at 257)',
      'tokens',
    ),
    median_within_prompt_uncensored_range_tokens: fixed(
      sum.median_within_prompt_uncensored_range_tokens,
      1,
      'Median within-prompt onset range across uncensored diverging batch sizes',
      'tokens',
    ),
    min_unique_completions_per_prompt: integer(
      sum.min_unique_completions_per_prompt,
      'Minimum distinct 256-token completions observed across the 14 batch sizes for a single prompt',
      'completions',
    ),
    max_unique_completions_per_prompt: integer(
      sum.max_unique_completions_per_prompt,
      'Maximum distinct 256-token completions observed across the 14 batch sizes for a single prompt',
      'completions',
    ),
    median_unique_completions_per_prompt: fixed(
      sum.median_unique_completions_per_prompt,
      1,
      'Median distinct 256-token completions observed across the 14 batch sizes',
      'completions',
    ),
    batch_to_prompt_variance_ratio: fixed(
      anova.batch_to_prompt_variance_ratio,
      3,
      'Ratio of batch-size main-effect variance to prompt main-effect variance on onset token',
    ),
    prompt_share_of_total_variance_pct: fixed(
      100.0 * anova.prompt_share_of_total,
      1,
      'Share of total onset-token variance explained by prompt main effects',
      'percent',
    ),
    batch_share_of_total_variance_pct: fixed(
      100.0 * anova.batch_share_of_total,
      1,
      'Share of total onset-token variance explained by batch-size main effects',
      'percent',
    ),
    residual_share_of_total_variance_pct: fixed(
      100.0 * anova.residual_share_of_total,
      1,
      'Share of total onset-token variance in prompt-by-batch interaction residual',
      'percent',
    ),
    torch_mm_fp32_max_diff: fixed(
      mm.torch_mm_fp32_max_abs_diff,
      2,
      'Maximum absolute difference between B=1 and B=2048 float32 torch.mm on row 0',
    ),
    torch_mm_bf16_max_diff: fixed(
      mm.torch_mm_bf16_max_abs_diff,
      1,
      'Maximum absolute difference between B=1 and B=2048 bfloat16 torch.mm on row 0',
    ),
    all_intra_batch_rows_identical: boolean(
      sum.all_intra_batch_rows_identical,
      'Whether all B identical rows inside every homogeneous batch produced identical 256-token sequences',
    ),
    method_fidelity_passed: boolean(
      result.fidelity.passed,
      'Whether run-to-run determinism, matmul non-invariance, KV equivalence, and signal floor gates passed',
    ),
    hypothesis_supported: boolean(
      result.verdict.hypothesis_supported,
      'Whether the preregistered batch-size-graded onset hypothesis was supported',
    ),
    hypothesis_falsified: boolean(
      result.verdict.hypothesis_falsified,
      'Whether the preregistered batch-size-graded onset hypothesis was falsified',
    ),
    result_inconclusive: boolean(
      result.verdict.result_inconclusive,
      'Whether the preregistered result was inconclusive',
    ),
  };

  if (sum.median_b1_margin_at_flip_steps !== null) {
    metrics.median_b1_margin_at_flip_steps = fixed(
      sum.median_b1_margin_at_flip_steps,
      4,
      'Median B=1 top-1 minus top-2 logit margin at token steps where batch divergence occurred',
      'logit units',
    );
  }
  if (sum.median_b1_margin_at_nonflip_steps !== null) {
    metrics.median_b1_margin_at_nonflip_steps = fixed(
      sum.median_b1_margin_at_nonflip_steps,
      2,
      'Median across prompts of the median B=1 top-1 minus top-2 logit margin at non-flipping steps',
      'logit units',
    );
  }

  return {
    schema_version: 1,
    experiment: 'batch-size-divergence-onset',
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
