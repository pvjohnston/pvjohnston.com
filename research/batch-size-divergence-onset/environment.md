# Environment

The `bfloat16` greedy decoding sweep ran on Google Colab (`linux-x86_64`), while
onset statistics, two-way variance decomposition, logit-perturbation summaries,
figure rendering, and publication metric generation run deterministically in
pure Python + NumPy (`analyze_divergence.py`) on both `linux-x86_64` and
`osx-arm64` without GPU or PyTorch dependencies.

## GPU inference stage (Google Colab)

Executed `2026-11-26T23:17:35Z` to `2026-11-26T23:50:00Z` (~32.4 min total wall
time across smoke test, determinism repeats, 8 × 14 batch sweep, and neighbor
content controls) under commit `483ef01` (`runs/environment_colab.json`):

- Operating system and kernel: `Linux-6.6.159+-x86_64-with-glibc2.39`
- CPU: Intel Xeon @ 2.20 GHz (`12` vCPUs)
- GPU: **NVIDIA L4** (`22563.1 MiB` VRAM, Ada Lovelace `SM 8.9`, `58` SMs,
  NVIDIA driver `580.82.07`, CUDA runtime `13.0`, cuDNN `92800`)
- Python version: `3.13.16`
- Packages:
  - `torch == 2.14.1+cu130` (`matmul_allow_tf32 = False`, `sdpa` Flash /
    Mem-Efficient / Math enabled)
  - `transformers == 5.24.1` (`attn_implementation = "sdpa"`)
  - `accelerate == 1.16.0`, `tokenizers == 0.23.3`, `safetensors == 0.8.0`,
    `numpy == 2.4.6`
- Model: `Qwen/Qwen3-4B-Instruct-2507` in native `torch.bfloat16` (`eval()`,
  `torch.inference_mode()`, strict greedy `argmax`)
- Random seeds and nondeterministic operations: none; back-to-back repeats at
  `B = 1` and `B = 32` returned `0.0` step-1 logit difference and `0` token
  mismatches across all eight prompts
- Required environment variables: none (ungated Apache-2.0 model; no secrets)

## Deterministic local analysis and figure stage

- Verified byte-identical on `osx-arm64` (`analyze_divergence.py --check`,
  `generate-metrics.mjs --check`, `make-figure.py --check`).
