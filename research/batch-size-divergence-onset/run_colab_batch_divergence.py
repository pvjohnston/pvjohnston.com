#!/usr/bin/env python3
"""Google Colab GPU runner for temperature-zero batch-size divergence onset.

Sweeps `B in {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128}` on
`Qwen/Qwen3-4B-Instruct-2507` in `bfloat16` across 8 prompts (256 greedy tokens),
checkpointing each prompt immediately to Google Drive.

Usage on Colab:
    python3 research/batch-size-divergence-onset/run_colab_batch_divergence.py --smoke-test
    python3 research/batch-size-divergence-onset/run_colab_batch_divergence.py \
        --checkpoint-dir /content/drive/MyDrive/pvjohnston-colab/batch-size-divergence-onset
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import inspect
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INPUTS_PATH = HERE / "inputs.json"
PREREG_PATH = HERE / "PREREGISTRATION.md"
RUNS_DIR = HERE / "runs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shell_capture(cmd: list[str]) -> str:
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
        )
        return res.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def pkg_ver(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def record_environment(
    model_id: str,
    model_commit: str | None,
    attn_impl: str | None,
    checkpoint_dir: Path | None,
) -> Path:
    import torch

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    props = torch.cuda.get_device_properties(0)
    env_info = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "git_head": shell_capture(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
        "gpu_name": props.name,
        "gpu_compute_capability": f"{props.major}.{props.minor}",
        "gpu_multi_processor_count": int(props.multi_processor_count),
        "gpu_total_memory_mib": round(props.total_memory / (1024 * 1024), 1),
        "cuda_runtime_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "torch_backends": {
            "matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
            "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
            "flash_sdp_enabled": bool(torch.backends.cuda.flash_sdp_enabled()),
            "mem_efficient_sdp_enabled": bool(torch.backends.cuda.mem_efficient_sdp_enabled()),
            "math_sdp_enabled": bool(torch.backends.cuda.math_sdp_enabled()),
        },
        "model_id": model_id,
        "model_hub_commit_sha": model_commit,
        "attn_implementation": attn_impl,
        "nvidia_smi": shell_capture(["nvidia-smi"]),
        "lscpu": shell_capture(["lscpu"]),
        "packages": {
            p: pkg_ver(p)
            for p in ("torch", "transformers", "accelerate", "tokenizers", "safetensors", "numpy")
        },
        "frozen_sha256": {
            "PREREGISTRATION.md": sha256(PREREG_PATH),
            "inputs.json": sha256(INPUTS_PATH),
            "run_colab_batch_divergence.py": sha256(Path(__file__).resolve()),
            "analyze_divergence.py": sha256(HERE / "analyze_divergence.py"),
        },
    }
    out_path = RUNS_DIR / "environment_colab.json"
    out_path.write_text(json.dumps(env_info, indent=2) + "\n", encoding="utf-8")
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, checkpoint_dir / "environment_colab.json")
    return out_path


def run_mm_noninvariance_check(b_dim: int, d_dim: int) -> dict:
    import torch

    res = {}
    for label, dtype in (("fp32", torch.float32), ("bf16", torch.bfloat16)):
        a = torch.linspace(-1000.0, 1000.0, b_dim * d_dim, device="cuda", dtype=torch.float32).reshape(b_dim, d_dim).to(dtype)
        b = torch.linspace(-1000.0, 1000.0, d_dim * d_dim, device="cuda", dtype=torch.float32).reshape(d_dim, d_dim).to(dtype)
        out1 = torch.mm(a[:1], b)
        out2 = torch.mm(a, b)[:1]
        out1_rep = torch.mm(a[:1], b)
        max_diff = float((out1.float() - out2.float()).abs().max().item())
        rep_diff = float((out1.float() - out1_rep.float()).abs().max().item())
        res[f"torch_mm_{label}_max_abs_diff"] = max_diff
        res[f"torch_mm_{label}_repeat_diff"] = rep_diff
        del a, b, out1, out2, out1_rep
    torch.cuda.empty_cache()
    return res


def load_model_and_tokenizer(model_id: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=torch.bfloat16,
            device_map="cuda",
        )
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
        )
    model.eval()
    commit_sha = getattr(model.config, "_commit_hash", None)
    attn_impl = getattr(model.config, "_attn_implementation", None)
    supports_logits_to_keep = "logits_to_keep" in inspect.signature(model.forward).parameters
    return model, tokenizer, commit_sha, attn_impl, supports_logits_to_keep


def greedy_decode_batch(
    model,
    input_ids,
    max_new_tokens: int,
    supports_logits_to_keep: bool,
):
    import torch

    with torch.inference_mode():
        b_size = int(input_ids.shape[0])
        generated = torch.empty((b_size, max_new_tokens), dtype=torch.long, device=input_ids.device)
        slot0_top1_logits = []
        slot0_top2_logits = []
        slot0_top2_ids = []

        fwd_kwargs = {"use_cache": True}
        if supports_logits_to_keep:
            fwd_kwargs["logits_to_keep"] = 1

        out = model(input_ids=input_ids, **fwd_kwargs)
        past_key_values = out.past_key_values
        next_logits = out.logits[:, -1, :]
        step1_slot0_f32 = next_logits[0].detach().to(torch.float32).cpu()

        top2_vals, top2_idx = torch.topk(next_logits[0], k=2, dim=-1)
        slot0_top1_logits.append(float(top2_vals[0].item()))
        slot0_top2_logits.append(float(top2_vals[1].item()))
        slot0_top2_ids.append([int(top2_idx[0].item()), int(top2_idx[1].item())])

        next_tokens = torch.argmax(next_logits, dim=-1, keepdim=True)
        generated[:, 0] = next_tokens[:, 0]

        for step in range(1, max_new_tokens):
            out = model(input_ids=next_tokens, past_key_values=past_key_values, **fwd_kwargs)
            past_key_values = out.past_key_values
            next_logits = out.logits[:, -1, :]

            top2_vals, top2_idx = torch.topk(next_logits[0], k=2, dim=-1)
            slot0_top1_logits.append(float(top2_vals[0].item()))
            slot0_top2_logits.append(float(top2_vals[1].item()))
            slot0_top2_ids.append([int(top2_idx[0].item()), int(top2_idx[1].item())])

            next_tokens = torch.argmax(next_logits, dim=-1, keepdim=True)
            generated[:, step] = next_tokens[:, 0]

        gen_cpu = generated.cpu()
        del past_key_values, out, next_logits, next_tokens, generated
    torch.cuda.synchronize()
    return gen_cpu, step1_slot0_f32, slot0_top1_logits, slot0_top2_logits, slot0_top2_ids


def run_smoke_and_mm(
    model,
    tokenizer,
    supports_logits_to_keep: bool,
    conditions: dict,
    checkpoint_dir: Path | None,
) -> dict:
    import torch

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    smoke_path = RUNS_DIR / "smoke_and_mm_check.json"

    t0 = time.time()
    mm_res = run_mm_noninvariance_check(
        int(conditions["mm_check_b"]), int(conditions["mm_check_d"])
    )

    # Verify explicit KV-cache loop equals HF model.generate(do_sample=False) on a toy string
    toy_text = tokenizer.apply_chat_template(
        [{"role": "user", "content": "Count from one to five."}],
        tokenize=False,
        add_generation_prompt=True,
    )
    toy_ids = tokenizer(toy_text, return_tensors="pt").input_ids.to("cuda")
    kv_gen, _, _, _, _ = greedy_decode_batch(model, toy_ids, 16, supports_logits_to_keep)
    with torch.inference_mode():
        hf_out = model.generate(
            toy_ids,
            max_new_tokens=16,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None,
        )
    hf_gen = hf_out[:, toy_ids.shape[1] :].cpu()
    kv_matches_hf = bool(torch.equal(kv_gen, hf_gen))
    if not kv_matches_hf:
        raise RuntimeError(
            f"KV loop mismatch vs HF generate: {kv_gen.tolist()} vs {hf_gen.tolist()}"
        )

    payload = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        **mm_res,
        "kv_loop_matches_hf_generate": kv_matches_hf,
        "toy_decoded_preview": tokenizer.decode(kv_gen[0].tolist(), skip_special_tokens=False),
        "elapsed_seconds": round(time.time() - t0, 3),
    }
    smoke_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if checkpoint_dir is not None:
        (checkpoint_dir / "runs").mkdir(parents=True, exist_ok=True)
        shutil.copy2(smoke_path, checkpoint_dir / "runs" / smoke_path.name)
    print(
        f"Smoke + torch.mm check passed in {payload['elapsed_seconds']:.1f}s | "
        f"mm fp32 diff = {payload['torch_mm_fp32_max_abs_diff']:.4f} | "
        f"mm bf16 diff = {payload['torch_mm_bf16_max_abs_diff']:.4f} | "
        f"KV==HF generate: {kv_matches_hf}",
        flush=True,
    )
    return payload


def build_divergence_snippet(tokenizer, b1_ids: list[int], b_ids: list[int], onset_1idx: int) -> dict:
    idx0 = onset_1idx - 1
    ctx_start = max(0, idx0 - 8)
    shared_suffix = tokenizer.decode(b1_ids[ctx_start:idx0], skip_special_tokens=False)
    b1_cont = tokenizer.decode(b1_ids[idx0 : min(len(b1_ids), idx0 + 8)], skip_special_tokens=False)
    b_cont = tokenizer.decode(b_ids[idx0 : min(len(b_ids), idx0 + 8)], skip_special_tokens=False)
    return {
        "onset_token_1indexed": onset_1idx,
        "shared_context_tail": shared_suffix,
        "b1_token_id": b1_ids[idx0],
        "b1_token_str": tokenizer.decode([b1_ids[idx0]], skip_special_tokens=False),
        "b1_continuation": b1_cont,
        "b_token_id": b_ids[idx0],
        "b_token_str": tokenizer.decode([b_ids[idx0]], skip_special_tokens=False),
        "b_continuation": b_cont,
    }


def run_prompt_sweep(
    model,
    tokenizer,
    supports_logits_to_keep: bool,
    p_spec: dict,
    conditions: dict,
) -> dict:
    import torch

    t_prompt0 = time.time()
    max_tokens = int(conditions["max_new_tokens"])
    batch_sizes = conditions["batch_sizes"]

    formatted = tokenizer.apply_chat_template(
        [{"role": "user", "content": p_spec["text"]}],
        tokenize=False,
        add_generation_prompt=True,
    )
    base_ids = tokenizer(formatted, return_tensors="pt").input_ids.to("cuda")
    prompt_len = int(base_ids.shape[1])

    # 1. Run-to-run determinism checks at B=1 and B=32
    det_checks = {}
    b1_cached = None
    b32_cached = None
    for det_b in conditions["determinism_check_batch_sizes"]:
        batch_in = base_ids.expand(int(det_b), -1).contiguous()
        gen_a, s1_a, t1_a, t2_a, ids2_a = greedy_decode_batch(
            model, batch_in, max_tokens, supports_logits_to_keep
        )
        gen_b, s1_b, _, _, _ = greedy_decode_batch(
            model, batch_in, max_tokens, supports_logits_to_keep
        )
        mismatches = int((gen_a != gen_b).sum().item())
        s1_diff = float((s1_a - s1_b).abs().max().item())
        det_checks[str(det_b)] = {
            "batch_size": int(det_b),
            "token_mismatches": mismatches,
            "step1_logit_max_abs_diff": s1_diff,
        }
        if det_b == 1:
            b1_cached = (gen_a, s1_a, t1_a, t2_a, ids2_a)
        elif det_b == 32:
            b32_cached = (gen_a, s1_a, t1_a, t2_a, ids2_a)
        del batch_in
        gc.collect()
        torch.cuda.empty_cache()

    b1_gen, b1_s1, b1_t1, b1_t2, b1_ids2 = b1_cached
    b1_slot0_list = b1_gen[0].tolist()

    batches_out = {}
    for b in batch_sizes:
        t_b0 = time.time()
        if b == 1:
            gen_cpu, s1_f32, t1_l, t2_l, ids2_l = b1_cached
        elif b == 32 and b32_cached is not None:
            gen_cpu, s1_f32, t1_l, t2_l, ids2_l = b32_cached
        else:
            batch_in = base_ids.expand(int(b), -1).contiguous()
            gen_cpu, s1_f32, t1_l, t2_l, ids2_l = greedy_decode_batch(
                model, batch_in, max_tokens, supports_logits_to_keep
            )
            del batch_in
            gc.collect()
            torch.cuda.empty_cache()

        slot0_list = gen_cpu[0].tolist()
        unique_rows = len({tuple(row) for row in gen_cpu.tolist()})
        s1_diff_vs_b1 = float((s1_f32 - b1_s1).abs().max().item())

        onset_1idx = None
        for idx, (tok1, tokb) in enumerate(zip(b1_slot0_list, slot0_list, strict=True)):
            if tok1 != tokb:
                onset_1idx = idx + 1
                break

        snippet = (
            build_divergence_snippet(tokenizer, b1_slot0_list, slot0_list, onset_1idx)
            if onset_1idx is not None
            else None
        )

        entry = {
            "batch_size": int(b),
            "elapsed_seconds": round(time.time() - t_b0, 3),
            "intra_batch_unique_sequences": unique_rows,
            "step1_logit_max_abs_diff_vs_b1": s1_diff_vs_b1,
            "onset_token_1indexed": onset_1idx,
            "slot0_token_ids": slot0_list,
            "divergence_snippet": snippet,
        }
        if b == 1:
            entry["slot0_top1_logits"] = t1_l
            entry["slot0_top2_logits"] = t2_l
            entry["slot0_top2_token_ids"] = ids2_l
            entry["slot0_decoded_text"] = tokenizer.decode(slot0_list, skip_special_tokens=False)
        batches_out[str(b)] = entry

    # Secondary control on source anchor prompt: neighbor count vs neighbor content
    neighbor_control = None
    if p_spec.get("source_anchor"):
        neighbor_control = {}
        # Build deterministic distinct token rows of exact same length `prompt_len`
        vocab_Check = 1000
        for cb in conditions["neighbor_content_control_batch_sizes"]:
            cb_int = int(cb)
            het_ids = base_ids.expand(cb_int, -1).clone()
            # Replace interior content tokens in rows 1..B-1 while keeping chat-Wrapper framing & exact length
            for r in range(1, cb_int):
                for col in range(min(4, prompt_len), max(min(4, prompt_len), prompt_len - 5)):
                    het_ids[r, col] = int(vocab_Check + ((r * 131 + col * 17) % 5000))
            het_gen, het_s1, _, _, _ = greedy_decode_batch(
                model, het_ids, max_tokens, supports_logits_to_keep
            )
            hom_tokens = batches_out[str(cb_int)]["slot0_token_ids"]
            het_tokens = het_gen[0].tolist()
            mismatches_vs_hom = sum(1 for a, b in zip(hom_tokens, het_tokens, strict=True) if a != b)
            onset_vs_b1 = None
            for idx, (tok1, tokh) in enumerate(zip(b1_slot0_list, het_tokens, strict=True)):
                if tok1 != tokh:
                    onset_vs_b1 = idx + 1
                    break
            # Compute step1 diff vs homogeneous batch
            hom_in = base_ids.expand(cb_int, -1).contiguous()
            _, hom_s1, _, _, _ = greedy_decode_batch(model, hom_in, 1, supports_logits_to_keep)
            s1_diff_hom_vs_het = float((het_s1 - hom_s1).abs().max().item())
            neighbor_control[str(cb_int)] = {
                "batch_size": cb_int,
                "token_mismatches_vs_homogeneous_same_b": mismatches_vs_hom,
                "step1_logit_max_abs_diff_vs_homogeneous_same_b": s1_diff_hom_vs_het,
                "onset_token_vs_b1": onset_vs_b1,
            }
            del het_ids, hom_in
            gc.collect()
            torch.cuda.empty_cache()

    return {
        "prompt_id": p_spec["id"],
        "label": p_spec["label"],
        "prompt_text": p_spec["text"],
        "prompt_token_length": prompt_len,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_elapsed_seconds": round(time.time() - t_prompt0, 3),
        "determinism_checks": det_checks,
        "neighbor_content_control": neighbor_control,
        "batches": batches_out,
    }


def sync_prompt_from_ckpt(pid: str, ckpt_dir: Path | None) -> bool:
    local_file = RUNS_DIR / f"{pid}.json"
    if local_file.is_file():
        return True
    if ckpt_dir is None:
        return False
    ckpt_file = ckpt_dir / "runs" / f"{pid}.json"
    if ckpt_file.is_file():
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ckpt_file, local_file)
        print(f"Restored completed prompt {pid} from {ckpt_file}", flush=True)
        return True
    return False


def sync_prompt_to_ckpt(pid: str, ckpt_dir: Path | None) -> None:
    if ckpt_dir is None:
        return
    (ckpt_dir / "runs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNS_DIR / f"{pid}.json", ckpt_dir / "runs" / f"{pid}.json")


def package_bundle(ckpt_dir: Path | None) -> Path:
    bundle_path = HERE / "batch_size_divergence_colab_artifacts.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        if RUNS_DIR.is_dir():
            tar.add(RUNS_DIR, arcname="runs")
        results_json = HERE / "results.json"
        if results_json.is_file():
            tar.add(results_json, arcname="results.json")
    if ckpt_dir is not None:
        shutil.copy2(bundle_path, ckpt_dir / bundle_path.name)
        if (HERE / "results.json").is_file():
            shutil.copy2(HERE / "results.json", ckpt_dir / "results.json")
    return bundle_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--prompt", action="append")
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    inputs = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    conditions = inputs["conditions"]

    model, tokenizer, commit_sha, attn_impl, supports_l2k = load_model_and_tokenizer(
        conditions["model_id"]
    )
    record_environment(conditions["model_id"], commit_sha, attn_impl, args.checkpoint_dir)
    run_smoke_and_mm(model, tokenizer, supports_l2k, conditions, args.checkpoint_dir)

    if args.smoke_test:
        return 0

    selected_ids = set(args.prompt) if args.prompt else {p["id"] for p in inputs["prompts"]}
    for p_spec in inputs["prompts"]:
        pid = p_spec["id"]
        if pid not in selected_ids:
            continue
        local_file = RUNS_DIR / f"{pid}.json"
        if not args.force and sync_prompt_from_ckpt(pid, args.checkpoint_dir):
            print(f"Skipping already-completed prompt {pid}", flush=True)
            continue

        print(f"\n=== Sweeping {pid} ({p_spec['text']!r}) across 14 batch sizes ===", flush=True)
        pdata = run_prompt_sweep(model, tokenizer, supports_l2k, p_spec, conditions)
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        local_file.write_text(json.dumps(pdata, indent=2) + "\n", encoding="utf-8")
        sync_prompt_to_ckpt(pid, args.checkpoint_dir)

        onsets = {
            b: pdata["batches"][str(b)]["onset_token_1indexed"]
            for b in conditions["batch_sizes"]
            if b >= 2
        }
        print(
            f"Finished {pid} in {pdata['total_elapsed_seconds']:.1f}s | onsets(B>=2) = {onsets}",
            flush=True,
        )

    if all((RUNS_DIR / f"{p['id']}.json").is_file() for p in inputs["prompts"]):
        subprocess.run(
            [sys.executable, str(HERE / "analyze_divergence.py"), "--analyze"],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(HERE / "analyze_divergence.py"), "--check"],
            check=True,
        )
        bundle = package_bundle(args.checkpoint_dir)
        print(f"\nAll 8 prompts analyzed and packaged -> {bundle}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
