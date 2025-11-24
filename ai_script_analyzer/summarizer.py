"""Summarization helpers with optional LLM support."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from .finacle_utils import detect_errors, detect_inputs, detect_outputs

DEFAULT_SUMMARY = "Automated summary unavailable. Review script manually."


class HybridSummarizer:
    """Combines rule-based summarization with optional LLM augmentation."""

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        max_api_calls: int = 0,
        llm_callable: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.cache_path = cache_path
        self.max_api_calls = max_api_calls
        self.llm_callable = llm_callable
        self._api_calls = 0
        self._cache = self._load_cache()

    def summarize(self, script_name: str, text: str) -> str:
        structured = self.generate_structured_summary(script_name, text, hints={}, related_chunks=[])
        return structured.get("business_summary", DEFAULT_SUMMARY)

    def generate_structured_summary(
        self,
        script_name: str,
        text: str,
        hints: Dict[str, object],
        related_chunks: Sequence[Dict[str, object]] | None,
    ) -> Dict[str, object]:
        """Return a structured summary aligned with the requested JSON schema."""

        related_chunks = related_chunks or []
        cache_key = self._make_key(script_name, text + json.dumps(hints, sort_keys=True))
        if cache_key in self._cache:
            return self._cache[cache_key]

        structured = self._heuristic_structured_summary(text, hints, related_chunks)

        if self.llm_callable and self._api_calls < self.max_api_calls:
            prompt = self._build_structured_prompt(script_name, text, hints, related_chunks)
            try:
                response = self.llm_callable(prompt, text)
                parsed = self._safe_parse_json(response)
                structured = self._merge_structured(structured, parsed)
                self._api_calls += 1
            except ValueError:
                pass

        self._cache[cache_key] = structured
        self._save_cache()
        return structured

    def _heuristic_structured_summary(
        self,
        text: str,
        hints: Dict[str, object],
        related_chunks: Sequence[Dict[str, object]],
    ) -> Dict[str, object]:
        inputs = hints.get("inputs") or detect_inputs(text)
        outputs = hints.get("outputs") or detect_outputs(text)
        errors = hints.get("errors") or detect_errors(text)
        summary = self._rule_based_summary(text)

        call_scripts = hints.get("call_scripts") or []
        user_hooks = hints.get("user_hooks") or []
        context_scripts = {
            chunk.get("script")
            for chunk in related_chunks
            if chunk.get("script") and chunk.get("script") != hints.get("script")
        }
        if call_scripts:
            summary += " Dependencies: " + ", ".join(call_scripts)
        if user_hooks:
            summary += " Hooks: " + ", ".join(user_hooks)
        if context_scripts:
            summary += " Context overlap: " + ", ".join(sorted(context_scripts))

        test_cases = self._build_test_cases(inputs, errors, call_scripts)
        return {
            "business_summary": summary[:500] or DEFAULT_SUMMARY,
            "inputs": list(inputs),
            "outputs": list(outputs),
            "errors": list(errors),
            "functional_test_cases": test_cases,
        }

    def _rule_based_summary(self, text: str) -> str:
        lines = [line.strip().strip("-/*#") for line in text.splitlines()]
        comment_lines = [line for line in lines if line and line[0].isalpha()]
        top_lines = comment_lines[:3]
        if not top_lines:
            tokens = [token for token in text.split() if token.isalpha()]
            top_lines = [" ".join(tokens[:30])]
        return " ".join(top_lines)[:400] or DEFAULT_SUMMARY

    def _build_test_cases(
        self,
        inputs: Sequence[str],
        errors: Sequence[str],
        dependencies: Sequence[str],
    ) -> List[Dict[str, str]]:
        cases: List[Dict[str, str]] = []

        def add_case(name: str, preconditions: str, input_data: str, expected: str, error: str = "") -> None:
            case_id = f"TC-{len(cases) + 1:03d}"
            cases.append(
                {
                    "Test Case Id": case_id,
                    "Test Case Name": name,
                    "Preconditions": preconditions or "-",
                    "Input Data": input_data or "-",
                    "Expected Outcome": expected or "-",
                    "Expected Error Message": error or "-",
                }
            )

        if inputs:
            add_case(
                "Happy path processing",
                "All mandatory Finacle fields captured",
                ", ".join(inputs),
                "Script computes and persists business values",
            )
            add_case(
                "Missing or invalid input",
                "Leave one mandatory field blank",
                inputs[0],
                "Script rejects transaction",
                "Validation error presented",
            )

        for error_text in errors:
            add_case(
                f"Error condition: {error_text[:40]}",
                "Trigger upstream condition",
                "-",
                "Script surfaces friendly error",
                error_text,
            )

        if dependencies:
            add_case(
                "Cross-script orchestration",
                "Invoke calling script",
                ", ".join(dependencies),
                "All dependent scripts execute in order",
            )

        if not cases:
            add_case(
                "Smoke test",
                "Run default scenario",
                "-",
                "Script completes without runtime failures",
            )

        return cases

    def _build_structured_prompt(
        self,
        script_name: str,
        text: str,
        hints: Dict[str, object],
        related_chunks: Sequence[Dict[str, object]],
    ) -> str:
        context_blocks = []
        for chunk in related_chunks[:3]:
            context_blocks.append(
                f"[script={chunk.get('script')} score={chunk.get('score', 0):.2f}]\n{chunk.get('content', '')}"
            )
        context = "\n---\n".join(context_blocks) or "No additional context"
        hint_text = json.dumps(hints, indent=2)
        return (
            "You are an expert Finacle business analyst."
            " Review the script, structured hints, and related chunks to produce a JSON payload"
            " with keys business_summary, inputs, outputs, errors, functional_test_cases."
            " Each functional test case must be an object with the keys: Test Case Id, Test Case Name,"
            " Preconditions, Input Data, Expected Outcome, Expected Error Message."
            f"\nSCRIPT NAME: {script_name}\n"
            "SCRIPT BODY:\n" + text +
            "\nHINTS:\n" + hint_text +
            "\nRELATED CHUNKS:\n" + context +
            "\nReturn strict JSON only."
        )

    def _safe_parse_json(self, payload: str) -> Dict[str, object]:
        payload = payload.strip()
        if not payload:
            raise ValueError("Empty response")
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ValueError("Invalid JSON") from exc

    @staticmethod
    def _merge_structured(
        base: Dict[str, object], override: Dict[str, object]
    ) -> Dict[str, object]:
        merged = dict(base)
        for key, value in override.items():
            if not value:
                continue
            if key == "functional_test_cases" and isinstance(value, list):
                merged[key] = value
            else:
                merged[key] = value
        return merged

    def _load_cache(self) -> dict:
        if not self.cache_path or not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")

    @staticmethod
    def _make_key(script_name: str, text: str) -> str:
        digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
        return f"{script_name}:{digest}"
