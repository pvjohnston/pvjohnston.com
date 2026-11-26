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
- Traceability: not yet established (awaiting canonical Colab GPU run)
- Highest reproduction level: none yet

## Stage 1: Preflight check (local, no GPU required)

```sh
python3 research/batch-size-divergence-onset/analyze_divergence.py --preflight
```

## Stage 2: GPU sweep (Google Colab L4 or A100)

Open `colab_runner.ipynb` on Google Colab (`L4` or `A100` GPU) to run the smoke
test (`torch.mm` batch non-invariance + `model.generate` equivalence) and sweep
all 8 prompts across `B = 1..128`, checkpointing each prompt to Google Drive and
packaging `batch_size_divergence_colab_artifacts.tar.gz`.
