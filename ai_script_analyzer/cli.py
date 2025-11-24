"""Command line interface for the AI Script Analyzer."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .analyzer import AnalyzerConfig, ScriptAnalyzer
from .excel_exporter import export_analysis_to_excel


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Finacle customization scripts")
    parser.add_argument(
        "scripts_dir",
        type=Path,
        help="Directory that contains custom scripts",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis.xlsx"),
        help="Path to the Excel file to generate",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[".txt", ".sql", ".scr", ".fnc"],
        help="File extensions to include",
    )
    parser.add_argument(
        "--summary-cache",
        type=Path,
        default=None,
        help="Path to reuse LLM summaries and avoid extra API calls",
    )
    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=0,
        help="Upper bound on LLM calls (0 disables API usage)",
    )
    parser.add_argument(
        "--chunk-lines",
        type=int,
        default=80,
        help="Number of lines per chunk added to the embedding store",
    )
    parser.add_argument(
        "--similarity-top-k",
        type=int,
        default=5,
        help="How many related chunks to feed into the LLM prompt",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    config = AnalyzerConfig(
        script_extensions=tuple(args.extensions),
        summary_cache=args.summary_cache,
        max_api_calls=args.max_api_calls,
        chunk_lines=args.chunk_lines,
        similarity_top_k=args.similarity_top_k,
    )
    analyzer = ScriptAnalyzer(config)
    result = analyzer.analyze_directory(args.scripts_dir)
    export_analysis_to_excel(result, args.output)
    print(f"Analysis complete. {len(result.scripts)} script(s) documented at {args.output}.")


if __name__ == "__main__":  # pragma: no cover
    main()
