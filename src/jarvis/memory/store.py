from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jarvis.memory.vector import LocalVectorIndex, ScoredDocument


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Episode:
    episode_id: str
    task_id: str
    created_at: str
    steps: list[dict[str, Any]]
    outcome: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryStore:
    """
    Hierarchical memory:
    - working: recent messages + optional rolling summary
    - long_term: RAG via LocalVectorIndex (pluggable)
    - episodic: append-only JSONL of Episode records
    """

    def __init__(
        self,
        vector_index: LocalVectorIndex | None = None,
        episodic_path: Path | None = None,
    ) -> None:
        self._vector = vector_index or LocalVectorIndex()
        self._episodic_path = episodic_path
        self._working_messages: list[dict[str, str]] = []
        self._working_summary: str = ""

    def append_working(self, role: str, content: str) -> None:
        self._working_messages.append({"role": role, "content": content})

    def set_working_summary(self, summary: str) -> None:
        self._working_summary = summary

    def clear_working(self) -> None:
        self._working_messages.clear()
        self._working_summary = ""

    def get_working_context(self, max_messages: int = 32) -> str:
        parts: list[str] = []
        if self._working_summary:
            parts.append(f"[summary]\n{self._working_summary}\n")
        tail = self._working_messages[-max_messages:]
        for m in tail:
            parts.append(f"{m['role']}: {m['content']}")
        return "\n".join(parts).strip()

    def ingest_long_term(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        doc_id = str(uuid.uuid4())
        self._vector.add(doc_id, text, metadata or {})
        return doc_id

    def search_long_term(self, query: str, top_k: int = 8) -> list[ScoredDocument]:
        return self._vector.search(query, top_k=top_k)

    def write_episode(self, episode: Episode) -> None:
        if self._episodic_path is None:
            return
        self._episodic_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(episode), ensure_ascii=False)
        with self._episodic_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def new_episode(
        self,
        task_id: str,
        steps: list[dict[str, Any]],
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> Episode:
        ep = Episode(
            episode_id=str(uuid.uuid4()),
            task_id=task_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            steps=steps,
            outcome=outcome,
            metadata=metadata or {},
        )
        self.write_episode(ep)
        return ep

    def load_episodes(self, limit: int = 100) -> list[Episode]:
        if self._episodic_path is None or not self._episodic_path.is_file():
            return []
        lines = self._episodic_path.read_text(encoding="utf-8").strip().splitlines()
        out: list[Episode] = []
        for line in lines[-limit:]:
            d = json.loads(line)
            out.append(
                Episode(
                    episode_id=d["episode_id"],
                    task_id=d["task_id"],
                    created_at=d["created_at"],
                    steps=d["steps"],
                    outcome=d["outcome"],
                    metadata=d.get("metadata", {}),
                )
            )
        return out
