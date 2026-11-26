# Environment

The `bfloat16` greedy decoding sweep runs on a Google Colab NVIDIA GPU runtime
(`linux-x86_64`), while onset statistics, two-way variance decomposition,
logit-perturbation summaries, and publication metric generation run
deterministically in pure Python + NumPy (`analyze_divergence.py`) on any
platform without GPU or PyTorch dependencies.

## GPU inference stage (Google Colab)

`run_colab_batch_divergence.py` writes the exact runtime provenance (`nvidia-smi`,
CPU model, kernel, Python, `torch`, CUDA runtime, cuBLAS/cuDNN backends,
`transformers`, `accelerate`, exact Hugging Face `Qwen/Qwen3-4B-Instruct-2507`
commit hash, and frozen file SHA-256 digests) to `runs/environment_colab.json`
during execution.

- Operating system and kernel: pending Colab run (`runs/environment_colab.json`)
- Architecture: `x86_64` + NVIDIA CUDA GPU (L4 or A100 recommended; fits in <15 GiB VRAM)
- Model: `Qwen/Qwen3-4B-Instruct-2507` in `torch.bfloat16`
- Required environment variables: none (ungated Apache-2.0 model; no secrets)

## Deterministic local analysis stage

- Interpreter: Python >= 3.10 with `numpy`
- Metric generator: Node.js >= 20 (`generate-metrics.mjs`)
- Canonical float serialization: 10 significant digits for architecture-invariant
  `--check` verification across `linux-x86_64` and `osx-arm64`.
