"""Helpers for constructing script dependency relationships."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set


class DependencyGraph:
    """Simple adjacency list representation for script dependencies."""

    def __init__(self) -> None:
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse: Dict[str, Set[str]] = defaultdict(set)

    def add_dependencies(self, script: str, dependencies: Iterable[str]) -> None:
        normalized = {self._normalize(dep) for dep in dependencies if dep}
        if not normalized:
            self._ensure_node(script)
            return
        for dep in normalized:
            self._adjacency[script].add(dep)
            self._reverse[dep].add(script)

    def dependencies_of(self, script: str) -> Set[str]:
        return set(self._adjacency.get(script, set()))

    def dependents_of(self, script: str) -> Set[str]:
        return set(self._reverse.get(script, set()))

    def _ensure_node(self, script: str) -> None:
        self._adjacency.setdefault(script, set())
        self._reverse.setdefault(script, set())

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().upper()

    @staticmethod
    def normalize(name: str) -> str:
        return DependencyGraph._normalize(name)
