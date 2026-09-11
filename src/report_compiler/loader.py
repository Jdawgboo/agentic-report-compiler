"""Local, line-addressable Markdown and text ingestion."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Chunk

SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_corpus(source_directory: str | Path, chunk_lines: int = 12) -> list[Chunk]:
    """Load supported files into stable, line-addressable chunks.

    Files are sorted by relative path and chunks by their line ranges, making the
    corpus stable for the same directory contents. Unsupported file types are not
    silently parsed as text.
    """
    root = Path(source_directory)
    if not root.is_dir():
        raise ValueError(f"Source directory does not exist: {root}")
    if chunk_lines < 1:
        raise ValueError("chunk_lines must be at least 1")

    files = sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    chunks: list[Chunk] = []
    for path in files:
        relative_path = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for offset in range(0, len(lines), chunk_lines):
            selected = lines[offset : offset + chunk_lines]
            text = "\n".join(selected).strip()
            if not text:
                continue
            line_start = offset + 1
            line_end = offset + len(selected)
            fingerprint = f"{relative_path}:{line_start}:{line_end}:{text}".encode("utf-8")
            chunk_id = hashlib.sha256(fingerprint).hexdigest()[:16]
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    source_path=relative_path,
                    line_start=line_start,
                    line_end=line_end,
                    text=text,
                )
            )

    if not chunks:
        raise ValueError("No non-empty .md or .txt files were found in the source directory")
    return chunks
