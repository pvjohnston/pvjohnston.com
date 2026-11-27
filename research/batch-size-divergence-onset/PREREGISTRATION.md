# Preregistration: Divergence onset vs. batch size in temperature-zero LLM inference

Frozen before executing any `Qwen/Qwen3-4B-Instruct-2507` sweep on GPU.

## Source relationship

This experiment answers the open question logged on `notes/questions.md` under
*"The unplotted line: divergence rate vs batch size"* and directly extends our
earlier note `/posts/2026-07-16-temperature-zero-is-not-determinism.html`, which
measured CPU floating-point summation non-associativity first-hand while citing
GPU batch-invariance results from Horace He and Thinking Machines Lab,
"Defeating Nondeterminism in LLM Inference," *Thinking Machines Lab:
Connectionism* (September 2025), https://doi.org/10.64434/tml.20250910.

He and Thinking Machines Lab report a single headline point for greedy decoding
(`temperature = 0`): sending `"Tell me about Richard Feynman"` 1,000 times to
`Qwen3-235B-A22B-Instruct-2507` under variable server load produced 80 unique
completions that stayed identical through token 102 and first diverged at token
103 (`"Queens, New York"` vs. `"New York City"`). Their article identifies the
lack of **batch invariance** in GPU reduction kernels (matrix multiplication,
RMSNorm, and attention) as the causal mechanism, yet never plots how divergence
onset behaves as a controlled function of batch size `B`.

Here we measure that unplotted curve directly on an NVIDIA GPU using an
open-weights model from the same `Qwen3` `Instruct-2507` family
(`Qwen/Qwen3-4B-Instruct-2507` in native `bfloat16`), sweeping batch size `B`
from `1` to `128` across an eight-prompt panel anchored by He's exact Richard
Feynman prompt.

## Question, hypothesis, and falsifier

Question: In greedy (`temperature = 0`) `bfloat16` Transformer decoding on a
standard PyTorch CUDA stack, how does the token position of first divergence
from an isolated (`B = 1`) request vary with batch size `B`, and is onset
governed primarily by batch size or by prompt-specific near-ties?

For each prompt `p` in `P1..P8` and each multi-request batch size
`B in {2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128}` (`13` multi-request
batch sizes), define `t_onset(p, B)` in `{1, ..., 256}` as the 1-indexed
generated token position where slot `0` at batch size `B` first differs from
the isolated `B = 1` completion of length `T = 256` tokens (or the right-censored
value `T + 1 = 257` if all `256` generated tokens match `B = 1`).

Hypothesis (**batch-size-graded onset**): Batch size systematically grades when
greedy completions diverge across `B >= 2`:

1. **Non-flat across `B >= 2`:** Across prompts that diverge from `B = 1` at one
   or more `B >= 2`, the median within-prompt onset range
   `max_{B >= 2} t_onset(p, B) - min_{B >= 2} t_onset(p, B)` is **at least 5
   tokens**; **and**
2. **Not dominated by prompt identity:** In a two-way additive decomposition of
   `t_onset(p, B)` over the `8 x 13` grid (`p in P1..P8`, `B >= 2`), the
   variance of the batch-size main effects `Var_B(mean_p t_onset(p, B))` is **at
   least 25%** of the variance of the prompt main effects
   `Var_p(mean_B t_onset(p, B))` (`Var_B / Var_p >= 0.25`).

Falsifier (matching the shelf entry's stated falsifier — *"onset is flat in
batch size, or dominated by prompt rather than batch"*):

- **Falsified** if every method-fidelity gate passes and either:
  1. the median within-prompt onset range across `B >= 2` for diverging prompts
     is **strictly less than 5 tokens** (e.g., once `B >= 2` leaves the `B = 1`
     kernel regime, nearly all `B >= 2` flip at the same prompt-determined
     near-tie token), **or**
  2. `Var_B / Var_p < 0.25` across the `8 x 13` grid (when divergence happens is
     dominated by where each prompt encounters a lexical near-tie rather than by
     batch size).
- **Supported** if every method-fidelity gate passes and both (1) and (2) hold.
- **Inconclusive** if any method-fidelity gate fails.

## Frozen computational protocol

1. **Model and precision:** `Qwen/Qwen3-4B-Instruct-2507` loaded via Hugging
   Face `transformers` (`AutoModelForCausalLM`, `torch_dtype = torch.bfloat16`,
   default PyTorch CUDA `sdpa` attention backend, `eval()` mode,
   `torch.inference_mode()`). No quantization, sampling, top-k/top-p filtering,
   or repetition penalty is applied; token selection at every step `t = 1..256`
   is strict greedy `argmax` over vocabulary logits (`do_sample = False`).
2. **Prompt panel (`8` prompts):** Formatted with the model's chat template
   (`apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True)`):
   - `P1_feynman`: `"Tell me about Richard Feynman"` (He 2025 benchmark prompt)
   - `P2_noether`: `"Tell me about Emmy Noether"`
   - `P3_lavoisier`: `"Tell me about Antoine Lavoisier"`
   - `P4_turing`: `"Tell me about Alan Turing"`
   - `P5_curie`: `"Tell me about Marie Curie"`
   - `P6_boltzmann`: `"Tell me about Ludwig Boltzmann"`
   - `P7_maxwell`: `"Explain Maxwell's equations and their physical meaning"`
   - `P8_thermodynamics`: `"Explain the second law of thermodynamics"`
3. **Batch-size grid (`14` sizes):**
   `B in [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128]`, spanning powers
   of two and `3 * 2^k` midpoints across two orders of magnitude.
4. **Padding-free batch construction:** For each `(p, B)`, the input tensor has
   shape `(B, L_p)` consisting of `B` unpadded copies of prompt `p` (`attention_mask = None`).
   This eliminates any padding-mask or sequence-length confound so that 100% of
   any difference in slot `0` between `B = 1` and `B > 1` arises purely from
   batch-dimension kernel selection in matrix multiplication, RMSNorm, and
   attention. Every run decodes exactly `256` tokens using explicit KV caching.

## Method-fidelity gate

The primary verdict is automatically **inconclusive** if any of the following
occur:

1. **Run-to-run determinism failure:** Repeating `B = 1` twice and `B = 32`
   twice back-to-back on every prompt fails to produce bitwise-identical step-1
   logits (`max_abs_diff == 0.0`) and identical 256-token sequences (`0` token
   mismatches);
2. **Matmul batch non-invariance sanity gate:** Reproducing He's `torch.mm`
   test (`B = 1` vs `B = 2048` at `D = 4096` in `float32` and `bfloat16`)
   returns zero difference, indicating batch-invariant kernels were somehow
   enabled;
3. **Signal floor:** Fewer than `4` of the `8` prompts diverge from `B = 1`
   within `256` tokens at any `B >= 2` (insufficient divergence events within a
   256-token horizon to resolve the shape of `t_onset` vs. `B`).

## Primary and secondary outputs

Primary outputs:

- `t_onset(p, B)` across all `8` prompts and `13` multi-request batch sizes;
- number of diverging prompts (out of `8`), median within-prompt onset range
  across `B >= 2`, and two-way variance ratio `Var_B / Var_p` (both on the full
  `8 x 13` grid with censored `257` and on the uncensored diverging-prompts
  subset as a sensitivity check);
- number of distinct 256-token completions observed per prompt across the `14`
  batch sizes; and
- the supported / falsified / inconclusive verdict.

Secondary diagnostic outputs (for mechanistic interpretation; do not govern the
primary verdict):

- **Continuous prefill logit perturbation vs. `B`:** `max_v |logit_1(B)[v] - logit_1(1)[v]|`
  at token step `1` (before any token can flip), exposing the discrete CUDA
  kernel-transition regimes across `B in 1..128`;
- **Near-tie margin gating:** the `B = 1` top-1 minus top-2 logit margin
  `logit_(1) - logit_(2)` at each observed divergence step `t_onset`, compared
  against the median margin across non-flipping steps;
- **Intra-batch slot check:** whether all `B` identical rows `0..B-1` inside a
  single `(B, L_p)` call produce identical 256-token sequences; and
- **Neighbor-count vs. neighbor-content control on `P1_feynman` (`B = 8, 32`):**
  comparing slot `0` when rows `1..B-1` are copies of `P1_feynman` versus
  distinct token sequences of the exact same token length `L_{P1}`.

## Stopping rule

The canonical GPU run executes the smoke test (`torch.mm` check plus a `B = 1`
equivalence check between the explicit KV-cache loop and `model.generate` on a
non-registered string `"Count from one to five."`), followed by a single pass
through `P1..P8` across the 14 frozen batch sizes. No prompt, batch size, model,
horizon, or decision threshold will be added or modified after viewing any `P1..P8`
output.
