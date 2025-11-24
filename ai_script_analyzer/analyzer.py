"""Core heuristics for extracting metadata from Finacle scripts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from .embedding_store import EmbeddingStore
from .ingestion import ScriptDocument, ScriptIngestionPipeline
from .dependency_graph import DependencyGraph
from .models import ScriptAnalysisResult, ScriptMetadata
from .summarizer import HybridSummarizer


@dataclass
class AnalyzerConfig:
    script_extensions: Sequence[str] = (".txt", ".sql", ".scr", ".fnc")
    summary_cache: Optional[Path] = None
    max_api_calls: int = 0
    chunk_lines: int = 80
    similarity_top_k: int = 5


class ScriptAnalyzer:
    """High level façade that orchestrates the analysis pipeline."""

    def __init__(self, config: Optional[AnalyzerConfig] = None) -> None:
        self.config = config or AnalyzerConfig()
        self.summarizer = HybridSummarizer(
            cache_path=self.config.summary_cache,
            max_api_calls=self.config.max_api_calls,
        )
        self.ingestor = ScriptIngestionPipeline(
            script_extensions=self.config.script_extensions,
            chunk_lines=self.config.chunk_lines,
        )
        self.embedding_store = EmbeddingStore()

    def analyze_directory(self, directory: Path) -> ScriptAnalysisResult:
        documents = self.ingestor.ingest_directory(directory)
        dependency_graph = DependencyGraph()
        metadata_objects: List[ScriptMetadata] = []

        for document in documents:
            for chunk in document.chunks:
                self.embedding_store.add(
                    chunk_id=chunk.chunk_id,
                    text=chunk.content,
                    metadata={"script": document.name, "path": str(document.path)},
                )

        for document in documents:
            dependencies = set(document.hints.get("call_scripts", []))
            structured = self._run_two_step_summary(document)
            metadata = ScriptMetadata(
                name=document.name,
                path=document.path,
                category="undetermined",
                summary=structured.get("business_summary", ""),
                inputs=structured.get("inputs", []),
                outputs=structured.get("outputs", []),
                errors=structured.get("errors", []),
                dependencies=dependencies,
                structured_summary=structured,
            )
            metadata.test_cases = [
                json.dumps(case, ensure_ascii=False)
                for case in structured.get("functional_test_cases", [])
            ]
            dependency_graph.add_dependencies(metadata.name, metadata.dependencies)
            metadata_objects.append(metadata)

        for metadata in metadata_objects:
            metadata.dependencies = dependency_graph.dependencies_of(metadata.name)
            metadata.dependents = dependency_graph.dependents_of(metadata.name)
            metadata.category = self._categorize(metadata)

        metadata_objects.sort(key=lambda item: item.name)
        return ScriptAnalysisResult(scripts=metadata_objects)

    def _run_two_step_summary(self, document: ScriptDocument) -> dict:
        related_chunks = self.embedding_store.similarity_search(
            document.text,
            top_k=self.config.similarity_top_k,
        )
        hints = dict(document.hints)
        hints.setdefault("script", document.name)
        return self.summarizer.generate_structured_summary(
            document.name,
            document.text,
            hints,
            related_chunks,
        )

    def _categorize(self, metadata: ScriptMetadata) -> str:
        if metadata.dependencies or metadata.dependents:
            return "add-on customization"
        return "standalone customization"
