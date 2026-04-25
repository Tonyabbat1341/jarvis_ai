"""
Lightweight eval hooks: perplexity placeholder and simple generation checks.

Full HELM-style suites require pinned model checkpoints on GCS.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def fake_perplexity(loss: float) -> float:
    return math.exp(loss)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--metrics-json", type=Path, help="Path to trainer metrics (loss)")
    args = p.parse_args()
    out: dict = {"note": "placeholder eval; wire to checkpoint + eval set on GCP"}
    if args.metrics_json and args.metrics_json.is_file():
        data = json.loads(args.metrics_json.read_text(encoding="utf-8"))
        loss = float(data.get("loss", 2.0))
        out["ppl"] = fake_perplexity(loss)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
