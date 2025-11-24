"""Simple in-memory embedding store with cosine similarity search."""
from __future__ import annotations

import math
from typing import Dict, List

from .finacle_utils import tokenize


class EmbeddingStore:
    """Stores lightweight embeddings for script chunks."""

    def __init__(self) -> None:
        self._vectors: Dict[str, Dict[str, float]] = {}
        self._metadata: Dict[str, Dict[str, object]] = {}

    def add(self, chunk_id: str, text: str, metadata: Dict[str, object]) -> None:
        vector = self._embed(text)
        self._vectors[chunk_id] = vector
        self._metadata[chunk_id] = {"content": text, **metadata}

    def similarity_search(self, text: str, top_k: int = 5) -> List[Dict[str, object]]:
        if not self._vectors:
            return []
        query_vector = self._embed(text)
        scores: List[tuple[str, float]] = []
        for chunk_id, vector in self._vectors.items():
            score = self._cosine_similarity(query_vector, vector)
            scores.append((chunk_id, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        results = []
        for chunk_id, score in scores[:top_k]:
            metadata = {**self._metadata[chunk_id]}
            metadata["chunk_id"] = chunk_id
            metadata["score"] = score
            results.append(metadata)
        return results

    def _embed(self, text: str) -> Dict[str, float]:
        tokens = tokenize(text)
        counts: Dict[str, float] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0.0) + 1.0
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {token: value / norm for token, value in counts.items()}

    @staticmethod
    def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        if len(vec_a) > len(vec_b):
            vec_a, vec_b = vec_b, vec_a
        dot = 0.0
        for token, value in vec_a.items():
            dot += value * vec_b.get(token, 0.0)
        return dot
