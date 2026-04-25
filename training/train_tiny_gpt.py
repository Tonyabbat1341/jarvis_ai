"""
Minimal decoder-only LM for pipeline validation (local or single GPU).
Not a replacement for Megatron at 7B+; use `training/megatron/` workflow for scale.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset


@dataclass
class TrainConfig:
    vocab_size: int = 256
    hidden_size: int = 256
    num_layers: int = 4
    num_heads: int = 4
    seq_len: int = 128
    batch_size: int = 8
    steps: int = 100
    lr: float = 3e-4
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


class TextShardDataset(Dataset):
    def __init__(self, path: Path, seq_len: int) -> None:
        raw = path.read_bytes()
        self.data = torch.tensor(list(raw), dtype=torch.long)
        self.seq_len = seq_len

    def __len__(self) -> int:
        return max(0, (len(self.data) - 1) // self.seq_len)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        start = idx * self.seq_len
        chunk = self.data[start : start + self.seq_len + 1]
        x = chunk[:-1]
        y = chunk[1:]
        return x, y


class CausalBlock(nn.Module):
    def __init__(self, d_model: int, nhead: int) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(
            d_model, nhead, batch_first=True, dropout=0.0
        )
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )

    def forward(self, x: torch.Tensor, attn_mask: torch.Tensor) -> torch.Tensor:
        h = self.ln1(x)
        a, _ = self.attn(h, h, h, attn_mask=attn_mask, need_weights=False)
        x = x + a
        h = self.ln2(x)
        x = x + self.mlp(h)
        return x


class TinyGPT(nn.Module):
    def __init__(self, cfg: TrainConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Embedding(cfg.vocab_size, cfg.hidden_size)
        self.pos = nn.Embedding(cfg.seq_len, cfg.hidden_size)
        self.blocks = nn.ModuleList(
            [CausalBlock(cfg.hidden_size, cfg.num_heads) for _ in range(cfg.num_layers)]
        )
        self.ln_f = nn.LayerNorm(cfg.hidden_size)
        self.head = nn.Linear(cfg.hidden_size, cfg.vocab_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t = x.shape
        pos = torch.arange(t, device=x.device).unsqueeze(0).expand(b, -1)
        h = self.embed(x) + self.pos(pos)
        causal = torch.triu(
            torch.ones(t, t, device=x.device, dtype=torch.bool), diagonal=1
        )
        attn_mask = torch.zeros(t, t, device=x.device)
        attn_mask = attn_mask.masked_fill(causal, float("-inf"))
        for blk in self.blocks:
            h = blk(h, attn_mask)
        h = self.ln_f(h)
        return self.head(h)


def run_train(cfg: TrainConfig, data_path: Path, ckpt_dir: Path | None) -> dict:
    ds = TextShardDataset(data_path, cfg.seq_len)
    if len(ds) == 0:
        raise SystemExit("dataset empty: provide a larger text file")
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True, drop_last=True)
    device = torch.device(cfg.device)
    model = TinyGPT(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
    loss_fn = nn.CrossEntropyLoss()
    it = iter(dl)
    losses: list[float] = []
    for step in range(cfg.steps):
        try:
            x, y = next(it)
        except StopIteration:
            it = iter(dl)
            x, y = next(it)
        x, y = x.to(device), y.to(device)
        logits = model(x)
        loss = loss_fn(logits.view(-1, cfg.vocab_size), y.view(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss.item()))
    out = {
        "loss": sum(losses) / len(losses),
        "ppl": math.exp(sum(losses) / len(losses)),
    }
    if ckpt_dir:
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), ckpt_dir / "tiny_gpt.pt")
        (ckpt_dir / "metrics.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True, help="Text or binary shard path")
    ap.add_argument("--ckpt-dir", type=Path, default=None)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()
    cfg = TrainConfig(steps=args.steps, device=args.device)
    metrics = run_train(cfg, args.data, args.ckpt_dir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
