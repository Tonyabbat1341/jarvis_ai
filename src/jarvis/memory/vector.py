from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np


def _hash_embedding(text: str, dim: int = 256) -> np.ndarray:
    """Deterministic pseudo-embedding for tests and environments without torch/ST."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "little")
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    n = np.linalg.norm(v) + 1e-8
    return (v / n).astype(np.float32)


@dataclass
class ScoredDocument:
    doc_id: str
    text: str
    score: float
    metadata: dict


class LocalVectorIndex:
    """Simple in-memory cosine index; swap for Vertex Vector Search in production."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._meta: list[dict] = []
        self._vectors: np.ndarray | None = None

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        emb = _hash_embedding(text, self.dim)
        if self._vectors is None:
            self._vectors = emb.reshape(1, -1)
        else:
            self._vectors = np.vstack([self._vectors, emb.reshape(1, -1)])
        self._ids.append(doc_id)
        self._texts.append(text)
        self._meta.append(metadata or {})

    def search(self, query: str, top_k: int = 8) -> list[ScoredDocument]:
        if not self._ids or self._vectors is None:
            return []
        q = _hash_embedding(query, self.dim)
        sims = self._vectors @ q
        order = np.argsort(-sims)[:top_k]
        out: list[ScoredDocument] = []
        for i in order:
            idx = int(i)
            out.append(
                ScoredDocument(
                    doc_id=self._ids[idx],
                    text=self._texts[idx],
                    score=float(sims[idx]),
                    metadata=dict(self._meta[idx]),
                )
            )
        return out

    def __len__(self) -> int:
        return len(self._ids)
