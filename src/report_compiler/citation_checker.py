"""Mechanical verification for report citations and literal support."""

from __future__ import annotations

import re

from .models import Evidence, ValidationResult

CITATION_PATTERN = re.compile(r"\[(S\d+)\]")
QUOTE_PATTERN = re.compile(r'"([^\"]+)"')


def _normalise(text: str) -> str:
    return " ".join(text.split()).lower()


def validate_report(report: str, citations: dict[str, Evidence]) -> ValidationResult:
    """Verify citation targets and quoted-span support.

    A report bullet containing a quoted finding must cite at least one known
    evidence record. Its literal quoted span must still occur in the cited chunk.
    """
    errors: list[str] = []
    for line_number, line in enumerate(report.splitlines(), start=1):
        if not line.startswith("- "):
            continue
        markers = CITATION_PATTERN.findall(line)
        quoted_spans = QUOTE_PATTERN.findall(line)
        if quoted_spans and not markers:
            errors.append(f"Line {line_number} contains quoted evidence without a citation")
            continue
        for marker in markers:
            if marker not in citations:
                errors.append(f"Line {line_number} references unknown citation [{marker}]")
        for quote in quoted_spans:
            supported = any(
                marker in citations and _normalise(quote) in _normalise(citations[marker].text)
                for marker in markers
            )
            if not supported:
                errors.append(f"Line {line_number} quote is not supported by its cited source")
        if any(character.isdigit() for character in line) and quoted_spans and not markers:
            errors.append(f"Line {line_number} contains a numeric quote without a citation")

    return ValidationResult(passed=not errors, errors=errors)
