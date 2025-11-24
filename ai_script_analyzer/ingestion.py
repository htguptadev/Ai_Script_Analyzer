"""Script ingestion pipeline that turns files into chunked documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from .finacle_utils import build_structured_hint, extract_finacle_body


@dataclass
class ScriptChunk:
    """Represents a chunk of a script that can be embedded."""

    chunk_id: str
    content: str
    order: int


@dataclass
class ScriptDocument:
    """High-level representation of a Finacle script."""

    name: str
    path: Path
    text: str
    chunks: List[ScriptChunk] = field(default_factory=list)
    hints: dict = field(default_factory=dict)


class ScriptIngestionPipeline:
    """Load files, normalize script bodies, and produce chunks."""

    def __init__(
        self,
        script_extensions: Sequence[str],
        chunk_lines: int = 80,
    ) -> None:
        self.extensions = tuple(ext.lower() for ext in script_extensions)
        self.chunk_lines = chunk_lines

    def ingest_directory(self, directory: Path) -> List[ScriptDocument]:
        documents: List[ScriptDocument] = []
        for path in self._iter_scripts(directory):
            raw_text = path.read_text(encoding="utf-8", errors="ignore")
            body = extract_finacle_body(raw_text)
            normalized = body.strip()
            if not normalized:
                continue
            name = path.stem.upper()
            chunks = self._chunk_text(name, normalized)
            hints = build_structured_hint(normalized)
            documents.append(
                ScriptDocument(
                    name=name,
                    path=path,
                    text=normalized,
                    chunks=chunks,
                    hints=hints,
                )
            )
        return documents

    def _iter_scripts(self, directory: Path) -> Iterable[Path]:
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.extensions:
                yield path

    def _chunk_text(self, script_name: str, text: str) -> List[ScriptChunk]:
        lines = text.splitlines()
        if not lines:
            return [ScriptChunk(chunk_id=f"{script_name}:chunk-0", content=text, order=0)]

        chunks: List[ScriptChunk] = []
        current: List[str] = []
        order = 0

        def flush(buffer: List[str], order: int) -> None:
            if not buffer:
                return
            chunk_text = "\n".join(buffer).strip()
            if chunk_text:
                chunk_id = f"{script_name}:chunk-{order}"
                chunks.append(ScriptChunk(chunk_id=chunk_id, content=chunk_text, order=order))

        for line in lines:
            current.append(line)
            if len(current) >= self.chunk_lines:
                flush(current, order)
                current = []
                order += 1

        flush(current, order)

        if not chunks:
            chunks.append(ScriptChunk(chunk_id=f"{script_name}:chunk-0", content=text, order=0))
        return chunks
