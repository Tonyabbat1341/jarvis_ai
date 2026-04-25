from __future__ import annotations

from pathlib import Path

from jarvis.agent import TaskAgent
from jarvis.memory import MemoryStore


def test_agent_runs_with_episode(tmp_path: Path) -> None:
    ep = tmp_path / "ep.jsonl"
    m = MemoryStore(episodic_path=ep)
    m.ingest_long_term("Memory search should find this line about English.")
    agent = TaskAgent(memory=m, max_steps=8)
    r = agent.run("demo task")
    assert r.task_id
    assert len(r.steps) >= 1
