"""A deterministic, bounded planner for research sub-questions."""

from __future__ import annotations

import re

from .models import Claim


def plan_request(request: str, maximum_claims: int = 3) -> list[Claim]:
    """Split a request into a small deterministic queue without an LLM.

    The planner intentionally stays simple: semicolon and question-mark clauses
    become individual research tasks. The original request remains intact when no
    useful split is present.
    """
    cleaned = " ".join(request.split())
    if not cleaned:
        raise ValueError("request must not be empty")

    candidates = [part.strip(" .") for part in re.split(r"[;?]+", cleaned) if part.strip(" .")]
    if not candidates:
        candidates = [cleaned]

    unique: list[str] = []
    for candidate in candidates:
        if candidate.lower() not in {item.lower() for item in unique}:
            unique.append(candidate)
        if len(unique) == maximum_claims:
            break

    return [Claim(claim_id=f"C{index:02d}", text=text) for index, text in enumerate(unique, start=1)]
