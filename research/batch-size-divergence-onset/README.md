# Divergence onset vs. batch size in temperature-zero LLM inference

Measures the token position of first greedy (`temperature = 0`) completion
divergence from an isolated (`B = 1`) request across `14` batch sizes
`B in {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128}` and `8` prompts on
`Qwen/Qwen3-4B-Instruct-2507` in `bfloat16`, testing the unplotted curve behind
Horace He and Thinking Machines Lab's *Defeating Nondeterminism in LLM Inference*
(2025) and `/posts/2026-07-16-temperature-zero-is-not-determinism.html`.

## Question and boundary

- Post type: research
- Question: how does greedy `bfloat16` token-divergence onset vary with batch
  size `B`, and is onset graded across `B` or dominated by prompt-specific
  near-ties?
- Research falsifier: [PREREGISTRATION.md](PREREGISTRATION.md) — falsified if
  median within-prompt onset range across `B >= 2` is `< 5` tokens or
  `Var_B / Var_p < 0.25`.
- Verdict: **falsified** — all 8 prompts diverged from `B = 1` within 256 tokens
  (producing 4 to 14 distinct completions per prompt), and within-prompt onset
  ranges spanned a median of 196.5 censored / 122.0 uncensored tokens across
  discrete kernel regimes, yet batch-size main effects accounted for only `4.7%`
  of variance against `49.5%` for prompt identity (`Var_B / Var_p = 0.094 < 0.25`)
  and `45.8%` for prompt-by-kernel interaction.
- What this experiment can establish: token-divergence onset across `B in 1..128`
  in unpadded `bfloat16` PyTorch SDPA inference on NVIDIA L4 (`SM 8.9`), step-1
  logit drift, `B = 1` top-1/top-2 margins at flip steps, and invariance of slot
  `0` to co-batched token identities at fixed sequence length.
- What it cannot establish: continuous-batching ragged-prefix chunking in vLLM
  or SGLang, multi-GPU tensor-parallel all-reduce effects, or `Qwen3-235B` MoE
  routing flips.
- Traceability: traceable
- Highest reproduction level: analysis-reproducible locally from committed JSON
  run records (`runs/*.json`), and end-to-end reproducible on an NVIDIA L4 GPU
  with CUDA 13.0 and PyTorch `2.14.1+cu130`.

## Regenerate analysis, metrics, and Figure 1 locally (no GPU required)

```sh
python3 research/batch-size-divergence-onset/analyze_divergence.py --preflight
python3 research/batch-size-divergence-onset/analyze_divergence.py --analyze
python3 research/batch-size-divergence-onset/analyze_divergence.py --check
node research/batch-size-divergence-onset/generate-metrics.mjs
node research/batch-size-divergence-onset/generate-metrics.mjs --check
node scripts/verify-metrics.mjs
python3 research/batch-size-divergence-onset/make-figure.py
python3 research/batch-size-divergence-onset/make-figure.py --check
```

## Data and publication

`PUBLIC_FILES.txt` routes all reviewed inputs, scripts, `results.json`,
`metrics.json`, `runs/environment_colab.json`, `runs/smoke_and_mm_check.json`,
and all eight per-prompt `runs/P*.json` records onto the live site. The 8 GB
Apache-2.0 `Qwen/Qwen3-4B-Instruct-2507` checkpoint is fetched from Hugging Face
Hub (`sources.json`) rather than stored in Git.
