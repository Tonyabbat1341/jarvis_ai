"""
Prepare text shards for training: read lines, filter, deduplicate, emit JSONL manifest.

Example:
  python -m data.prepare_shards raw/en.txt --out processed/en --shard-lines 10000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def normalize_line(line: str) -> str:
    line = line.replace("\u200b", "").strip()
    line = re.sub(r"\s+", " ", line)
    return line


def min_length_ok(text: str, min_chars: int) -> bool:
    return len(text) >= min_chars


def hash_dedup_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_input_lines(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return [ln for ln in raw.splitlines() if ln.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare English (or any) text shards + manifest")
    ap.add_argument("input", type=Path, help="Input .txt (one doc per line or paragraph)")
    ap.add_argument("--out", type=Path, required=True, help="Output directory for shards")
    ap.add_argument("--shard-lines", type=int, default=10_000, help="Lines per shard file")
    ap.add_argument("--min-chars", type=int, default=32, help="Minimum characters per line")
    ap.add_argument(
        "--lang",
        default="en",
        help="Language tag stored in manifest (default en)",
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    lines = iter_input_lines(args.input)
    seen: set[str] = set()
    kept: list[str] = []
    stats: defaultdict[str, int] = defaultdict(int)

    for line in lines:
        stats["raw"] += 1
        t = normalize_line(line)
        if not min_length_ok(t, args.min_chars):
            stats["too_short"] += 1
            continue
        key = hash_dedup_key(t)
        if key in seen:
            stats["dup"] += 1
            continue
        seen.add(key)
        kept.append(t)
        stats["kept"] += 1

    manifest: list[dict] = []
    shard_idx = 0
    buf: list[str] = []

    def flush() -> None:
        nonlocal shard_idx, buf
        if not buf:
            return
        name = f"shard_{shard_idx:05d}.txt"
        p = args.out / name
        p.write_text("\n".join(buf) + "\n", encoding="utf-8")
        manifest.append(
            {
                "path": str(p.resolve()),
                "lines": len(buf),
                "bytes": p.stat().st_size,
                "language": args.lang,
            }
        )
        shard_idx += 1
        buf = []

    for line in kept:
        buf.append(line)
        if len(buf) >= args.shard_lines:
            flush()
    flush()

    man_path = args.out / "manifest.jsonl"
    with man_path.open("w", encoding="utf-8") as f:
        for row in manifest:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    stats_path = args.out / "stats.json"
    stats_path.write_text(json.dumps(dict(stats), indent=2), encoding="utf-8")
    print(f"Wrote {len(manifest)} shards under {args.out}")
    print(f"Stats: {dict(stats)}")


if __name__ == "__main__":
    main()
