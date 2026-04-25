"""CLI entry for quick agent smoke tests: python -m jarvis.agent.cli \"task text\""""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from jarvis.agent.loop import TaskAgent
from jarvis.memory.store import MemoryStore


def main() -> None:
    p = argparse.ArgumentParser(description="Jarvis TaskAgent (sandbox tools)")
    p.add_argument("task", help="Task description")
    p.add_argument("--episodes", type=Path, default=None, help="JSONL path for episodic memory")
    args = p.parse_args()

    ep_path = args.episodes
    if ep_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
        tmp.close()
        ep_path = Path(tmp.name)

    mem = MemoryStore(episodic_path=ep_path)
    mem.ingest_long_term("English documentation snippet about Jarvis training on GCP.")
    agent = TaskAgent(memory=mem)
    r = agent.run(args.task)
    print("success:", r.success)
    print("final:", r.final_message)


if __name__ == "__main__":
    main()
