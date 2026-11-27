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

function median(arr) {
  const s = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 === 0 ? 0.5 * (s[mid - 1] + s[mid]) : s[mid];
}

function build(generatedAt) {
  if (!existsSync(resultsPath)) {
    throw new Error(`${relative(root, resultsPath)} does not exist yet.`);
  }
  const result = JSON.parse(readFileSync(resultsPath, 'utf8'));
  const sum = result.summary;
  const anova = sum.two_way_anova_all_prompts;
  const mm = result.smoke_and_mm_check;
  const curve = result.batch_size_curve;
  const prompts = result.prompts;

  const rhos = Object.values(prompts).map((p) => p.spearman_rho_batch_vs_censored_onset);

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
    grand_mean_censored_onset_tokens: fixed(
      anova.grand_mean_tokens,
      1,
      'Grand mean censored onset token across all 8 prompts and 13 multi-request batch sizes',
      'tokens',
    ),
    spearman_rho_min: fixed(
      Math.min(...rhos),
      2,
      'Minimum within-prompt Spearman rank correlation between batch size B and censored onset token',
    ),
    spearman_rho_max: fixed(
      Math.max(...rhos),
      2,
      'Maximum within-prompt Spearman rank correlation between batch size B and censored onset token',
    ),
    spearman_rho_median: fixed(
      median(rhos),
      2,
      'Median within-prompt Spearman rank correlation between batch size B and censored onset token',
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
    median_b1_margin_at_flip_steps: fixed(
      sum.median_b1_margin_at_flip_steps,
      3,
      'Median B=1 top-1 minus top-2 logit margin at token steps where batch divergence occurred',
      'logit units',
    ),
    max_b1_margin_at_flip_steps: fixed(
      sum.max_b1_margin_at_flip_steps,
      2,
      'Maximum B=1 top-1 minus top-2 logit margin at any token step where batch divergence occurred',
      'logit units',
    ),
    median_b1_margin_at_nonflip_steps: fixed(
      sum.median_b1_margin_at_nonflip_steps,
      2,
      'Median across prompts of the median B=1 top-1 minus top-2 logit margin at non-flipping steps',
      'logit units',
    ),
    feynman_neighbor_b8_mismatches: integer(
      prompts.P1_feynman.neighbor_content_control['8'].token_mismatches_vs_homogeneous_same_b,
      'Token mismatches in slot 0 at B=8 when rows 1..7 contain distinct tokens vs identical copies',
      'tokens',
    ),
    feynman_neighbor_b32_mismatches: integer(
      prompts.P1_feynman.neighbor_content_control['32'].token_mismatches_vs_homogeneous_same_b,
      'Token mismatches in slot 0 at B=32 when rows 1..31 contain distinct tokens vs identical copies',
      'tokens',
    ),
    feynman_neighbor_max_logit_diff: fixed(
      Math.max(
        prompts.P1_feynman.neighbor_content_control['8'].step1_logit_max_abs_diff_vs_homogeneous_same_b,
        prompts.P1_feynman.neighbor_content_control['32'].step1_logit_max_abs_diff_vs_homogeneous_same_b,
      ),
      1,
      'Maximum step-1 logit difference in slot 0 between heterogeneous and homogeneous co-batches at B=8 and B=32',
      'logit units',
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

  for (const [bStr, cRow] of Object.entries(curve)) {
    metrics[`b${bStr}_diverged_prompts`] = integer(
      cRow.n_prompts_diverged,
      `Number of prompts (out of 8) diverging from B=1 within 256 tokens at batch size ${bStr}`,
      'prompts',
    );
    metrics[`b${bStr}_mean_censored_onset`] = fixed(
      cRow.mean_censored_onset_tokens,
      1,
      `Mean censored onset token across 8 prompts at batch size ${bStr}`,
      'tokens',
    );
    metrics[`b${bStr}_mean_step1_logit_diff`] = fixed(
      cRow.mean_step1_logit_max_abs_diff,
      2,
      `Mean step-1 max absolute logit difference vs B=1 across 8 prompts at batch size ${bStr}`,
      'logit units',
    );
    metrics[`b${bStr}_max_step1_logit_diff`] = fixed(
      cRow.max_step1_logit_max_abs_diff,
      2,
      `Maximum step-1 max absolute logit difference vs B=1 across 8 prompts at batch size ${bStr}`,
      'logit units',
    );
  }

  for (const [pid, pRow] of Object.entries(prompts)) {
    const short = pid.toLowerCase();
    metrics[`${short}_unique_completions`] = integer(
      pRow.n_unique_completions_across_14_batches,
      `Distinct 256-token completions across the 14 batch sizes for ${pid}`,
      'completions',
    );
    metrics[`${short}_diverging_batches`] = integer(
      pRow.n_diverging_batch_sizes,
      `Number of multi-request batch sizes (out of 13) diverging from B=1 for ${pid}`,
      'batches',
    );
    metrics[`${short}_min_onset`] = integer(
      pRow.min_onset_token,
      `Earliest divergence token across B >= 2 for ${pid}`,
      'token',
    );
    metrics[`${short}_max_uncensored_onset`] = integer(
      pRow.max_onset_token_uncensored,
      `Latest uncensored divergence token across B >= 2 for ${pid}`,
      'token',
    );
    metrics[`${short}_spearman_rho`] = fixed(
      pRow.spearman_rho_batch_vs_censored_onset,
      2,
      `Spearman rank correlation between batch size and censored onset token for ${pid}`,
    );
  }

  // Feynman specific modal onset at token 69 (9 of 13 batch sizes)
  const feynman69Count = Object.values(prompts.P1_feynman.batches)
    .filter((b) => b.onset_token_1indexed === 69).length;
  metrics.p1_feynman_modal_onset_token = integer(
    69,
    'Modal divergence onset token on the Richard Feynman prompt',
    'token',
  );
  metrics.p1_feynman_modal_onset_batch_count = integer(
    feynman69Count,
    'Number of multi-request batch sizes (out of 13) that diverged at token 69 on the Richard Feynman prompt',
    'batches',
  );

  return {
    schema_version: 1,
    experiment: 'batch-size-divergence-onset',
    provenance: {
      generated_at: generatedAt,
      generator: relative(root, fileURLToPath(import.meta.url)),
      inputs: inputPaths.map((path, idx) => ({ path, sha256: sha256(path), index: idx })).map(({ path, sha256: h }) => ({ path, sha256: h })),
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
