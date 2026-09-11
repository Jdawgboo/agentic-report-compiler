"""Transparent lexical retrieval for local evidence chunks."""

from __future__ import annotations

from collections import Counter
import re

from .models import Chunk, Evidence

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "what", "with", "about", "do",
}


def tokenize(text: str) -> list[str]:
    """Return normalized lexical tokens while removing common stop words."""
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def retrieve(query: str, chunks: list[Chunk], top_k: int = 3) -> list[Evidence]:
    """Rank chunks using coverage plus capped term frequency.

    This is deliberately lexical rather than semantic retrieval. The score is
    exposed in the manifest so users can inspect why a source was selected.
    """
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    query_terms = set(query_tokens)
    ranked: list[Evidence] = []

    for chunk in chunks:
        counts = Counter(tokenize(chunk.text))
        matched = query_terms.intersection(counts)
        if not matched:
            continue
        coverage = len(matched) / len(query_terms)
        frequency = sum(min(counts[token], 3) for token in matched) / (3 * len(query_terms))
        score = coverage + frequency
        ranked.append(
            Evidence(
                chunk_id=chunk.chunk_id,
                source_path=chunk.source_path,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                text=chunk.text,
                score=score,
                coverage=coverage,
                query=query,
            )
        )

    return sorted(
        ranked,
        key=lambda item: (-item.score, item.source_path, item.line_start, item.chunk_id),
    )[:top_k]
