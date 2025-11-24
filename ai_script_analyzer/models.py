"""Data models for representing Finacle script analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Set


@dataclass
class ScriptMetadata:
    """Structured information extracted from a script."""

    name: str
    path: Path
    category: str
    summary: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    test_cases: List[str] = field(default_factory=list)
    structured_summary: dict = field(default_factory=dict)

    def as_row(self) -> List[str]:
        """Return a list representation suitable for writing to Excel."""

        def join(values: Sequence[str]) -> str:
            return "\n".join(sorted(values)) if values else "-"

        return [
            self.name,
            str(self.path),
            self.category,
            self.summary or "-",
            join(self.inputs),
            join(self.outputs),
            join(self.errors),
            join(self.dependencies),
            join(self.dependents),
            join(self.test_cases),
        ]


@dataclass
class ScriptAnalysisResult:
    """Container that stores the aggregated analysis."""

    scripts: List[ScriptMetadata] = field(default_factory=list)

    def to_table(self) -> List[List[str]]:
        header = [
            "Script Name",
            "Path",
            "Category",
            "Business Summary",
            "Inputs",
            "Outputs",
            "Error Conditions",
            "Dependencies",
            "Dependents",
            "Functional Test Cases",
        ]
        return [header] + [script.as_row() for script in self.scripts]
