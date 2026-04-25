from __future__ import annotations

from pathlib import Path

from data.prepare_shards import main as prepare_main


def test_prepare_shards_dedup(tmp_path: Path, monkeypatch) -> None:
    inp = tmp_path / "in.txt"
    out = tmp_path / "out"
    inp.write_text(
        "This is a valid line for training purposes.\n"
        "This is a valid line for training purposes.\n"
        "short\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["prepare_shards", str(inp), "--out", str(out), "--shard-lines", "100", "--min-chars", "10"],
    )
    prepare_main()
    man = out / "manifest.jsonl"
    assert man.is_file()
    stats = out / "stats.json"
    assert stats.is_file()
