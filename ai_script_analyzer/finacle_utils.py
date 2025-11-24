"""Utility helpers tailored to Finacle customization scripts."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_BODY_PATTERN = re.compile(r"<--\s*start\s*>(.*?)end-->", re.IGNORECASE | re.DOTALL)
_CALL_PATTERN = re.compile(
    r"\bCALLSCRIPTSIFEXISTS\s*\(\s*'([^']+)'\s*\)"
    r"|\bCALLSCRIPT\s*\(\s*'([^']+)'\s*\)",
    re.IGNORECASE,
)
_HOOK_PATTERN = re.compile(r"\b(urhk|urtn)_[A-Za-z0-9_]+\b", re.IGNORECASE)
_ASSIGN_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_\.]+)\s*=\s*(.+)")
_INPUT_PATTERN = re.compile(r"\b(?:INPUT|PROMPT|PARAM(?:ETER)?|ACCEPT)\s+([A-Z0-9_]+)", re.IGNORECASE)
_OUTPUT_PATTERN = re.compile(r"\b(?:OUTPUT|DISPLAY|PRINT|RETURN|SEND)\s+([A-Z0-9_]+)", re.IGNORECASE)
_ERROR_PATTERN = re.compile(r"\b(?:ERROR|EXCEPTION|RAISE)\b.*", re.IGNORECASE)
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def extract_finacle_body(text: str) -> str:
    """Extract the portion between <--START and END--> when available."""

    match = _BODY_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def detect_calls(script: str) -> List[str]:
    """Return sorted CALLSCRIPT / CALLSCRIPTSIFEXISTS targets."""

    targets = []
    for match in _CALL_PATTERN.finditer(script):
        target = match.group(1) or match.group(2)
        if target:
            targets.append(target.strip().upper())
    return sorted(set(targets))


def detect_user_hooks(script: str) -> List[str]:
    """Return sorted Finacle user hook or routine names."""

    matches = {match.group(0) for match in _HOOK_PATTERN.finditer(script)}
    return sorted(matches)


def detect_assignments(script: str, limit: int = 25) -> List[Tuple[str, str]]:
    """Return sample assignment statements."""

    rows: List[Tuple[str, str]] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ASSIGN_PATTERN.match(stripped)
        if match:
            rows.append((match.group(1), match.group(2)))
        if len(rows) >= limit:
            break
    return rows


def detect_inputs(script: str) -> List[str]:
    values = {match.group(1).upper() for match in _INPUT_PATTERN.finditer(script)}
    return sorted(values)


def detect_outputs(script: str) -> List[str]:
    values = {match.group(1).upper() for match in _OUTPUT_PATTERN.finditer(script)}
    return sorted(values)


def detect_errors(script: str) -> List[str]:
    values: List[str] = []
    for line in script.splitlines():
        match = _ERROR_PATTERN.search(line)
        if match:
            values.append(match.group(0).strip())
        if len(values) >= 10:
            break
    return values


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(text)]


def build_structured_hint(script: str) -> Dict[str, object]:
    """Build a structured hint object that feeds the LLM prompt."""

    return {
        "call_scripts": detect_calls(script),
        "user_hooks": detect_user_hooks(script),
        "sample_assignments": detect_assignments(script),
        "inputs": detect_inputs(script),
        "outputs": detect_outputs(script),
        "errors": detect_errors(script),
    }
