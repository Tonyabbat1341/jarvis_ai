"""
Emit Megatron-LM CLI tokens from a Jarvis model YAML (one token per line for bash mapfile).

Requires Megatron-LM `pretrain_gpt.py` flags compatible with recent NVIDIA/Megatron-LM.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def _append_flag(out: list[str], name: str, value: Any) -> None:
    if value is None:
        return
    out.append(name)
    out.append(str(value))


def jarvis_config_to_megatron_tokens(cfg: dict[str, Any]) -> list[str]:
    t = cfg["training"]
    tokens: list[str] = []

    _append_flag(tokens, "--num-layers", cfg["num_layers"])
    _append_flag(tokens, "--hidden-size", cfg["hidden_size"])
    _append_flag(tokens, "--num-attention-heads", cfg["num_attention_heads"])
    _append_flag(tokens, "--ffn-hidden-size", cfg["intermediate_size"])
    _append_flag(tokens, "--max-position-embeddings", cfg["max_position_embeddings"])
    _append_flag(tokens, "--seq-length", t["sequence_length"])
    _append_flag(tokens, "--micro-batch-size", t["micro_batch_size"])
    _append_flag(tokens, "--global-batch-size", t["global_batch_size"])
    _append_flag(tokens, "--train-iters", t["train_steps"])
    _append_flag(tokens, "--lr", t["lr"])
    _append_flag(tokens, "--min-lr", t["min_lr"])
    _append_flag(tokens, "--lr-warmup-iters", t["warmup_steps"])
    _append_flag(tokens, "--weight-decay", t["weight_decay"])
    _append_flag(tokens, "--clip-grad", t["grad_clip"])
    _append_flag(tokens, "--adam-beta1", t["beta1"])
    _append_flag(tokens, "--adam-beta2", t["beta2"])

    decay = t.get("lr_decay_style", "cosine")
    _append_flag(tokens, "--lr-decay-style", decay)

    if t.get("bf16"):
        tokens.append("--bf16")
    elif t.get("fp16"):
        tokens.append("--fp16")

    if not cfg.get("tie_word_embeddings", True):
        tokens.append("--untie-embeddings-and-output-weights")

    return tokens


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "config",
        type=Path,
        help="Path to Jarvis model YAML (e.g. configs/model_jarvis_mini_1_0.yaml)",
    )
    args = p.parse_args()
    with args.config.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    tokens = jarvis_config_to_megatron_tokens(cfg)
    sys.stdout.write("\n".join(tokens) + "\n")


if __name__ == "__main__":
    main()
