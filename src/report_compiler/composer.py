"""Extractive report composition with explicit source markers."""

from __future__ import annotations

import re

from .models import Claim, Evidence


def _normalise(text: str) -> str:
    return " ".join(text.split())


def quote_from_evidence(evidence: Evidence) -> str:
    """Choose one literal, readable sentence from a retrieved chunk."""
    prose_lines = [
        line.strip()
        for line in evidence.text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    source = _normalise(" ".join(prose_lines)) or _normalise(evidence.text)
    sentences = re.split(r"(?<=[.!?])\s+", source)
    return next((sentence for sentence in sentences if sentence), source)[:500]


def compose_report(request: str, claims: list[Claim]) -> tuple[str, dict[str, Evidence]]:
    """Render grounded claims as cited quotes and gaps as transparent notices."""
    lines = ["# Evidence Brief", "", f"**Request:** {request}", "", "## Findings", ""]
    citations: dict[str, Evidence] = {}
    labels_by_chunk: dict[str, str] = {}

    for claim in claims:
        lines.extend([f"### {claim.text}", ""])
        if claim.status == "GROUNDED":
            for evidence in claim.evidence:
                label = labels_by_chunk.get(evidence.chunk_id)
                if label is None:
                    label = f"S{len(labels_by_chunk) + 1}"
                    labels_by_chunk[evidence.chunk_id] = label
                    citations[label] = evidence
                lines.append(f'- "{quote_from_evidence(evidence)}" [{label}]')
        else:
            lines.append(
                "> **Evidence gap:** the supplied sources did not meet the configured "
                "coverage and evidence-count thresholds for this question."
            )
        lines.append("")

    lines.extend(["## Source index", ""])
    if citations:
        for label, evidence in citations.items():
            lines.append(
                f"- [{label}] `{evidence.source_path}` lines {evidence.line_start}-{evidence.line_end} "
                f"(retrieval score {evidence.score:.3f})"
            )
    else:
        lines.append("- No source chunks met the retrieval threshold.")

    return "\n".join(lines).rstrip() + "\n", citations
