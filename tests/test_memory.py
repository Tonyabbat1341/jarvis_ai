from __future__ import annotations

from pathlib import Path

from jarvis.memory import MemoryStore


def test_memory_working_and_rag(tmp_path: Path) -> None:
    ep = tmp_path / "ep.jsonl"
    m = MemoryStore(episodic_path=ep)
    m.append_working("user", "hello")
    m.append_working("assistant", "hi")
    ctx = m.get_working_context()
    assert "user: hello" in ctx
    m.ingest_long_term("GCP Vertex training notes for Jarvis.")
    hits = m.search_long_term("Vertex", top_k=3)
    assert len(hits) >= 1
    ep_obj = m.new_episode("t1", [{"step": 1}], "ok")
    assert ep_obj.episode_id
    loaded = m.load_episodes()
    assert len(loaded) == 1
    assert loaded[0].task_id == "t1"
