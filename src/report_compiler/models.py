"""Typed data contracts for deterministic research runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    INIT = "INIT"
    INDEXED = "INDEXED"
    PLANNED = "PLANNED"
    RETRIEVING = "RETRIEVING"
    EVALUATING = "EVALUATING"
    SYNTHESIZING = "SYNTHESIZING"
    VERIFYING = "VERIFYING"
    DONE = "DONE"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_path: str
    line_start: int
    line_end: int
    text: str


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    source_path: str
    line_start: int
    line_end: int
    text: str
    score: float
    coverage: float
    query: str


@dataclass
class Claim:
    claim_id: str
    text: str
    status: str = "PENDING"
    coverage: float = 0.0
    evidence: list[Evidence] = field(default_factory=list)
    gap: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: list[str]


@dataclass
class RunResult:
    request: str
    state: AgentState
    report: str
    claims: list[Claim]
    citations: dict[str, Evidence]
    trace: list[dict[str, Any]]
    validation: ValidationResult

    def manifest(self) -> dict[str, Any]:
        """Return a JSON-serializable, deterministic record of the run."""
        return {
            "request": self.request,
            "final_state": self.state.value,
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "text": claim.text,
                    "status": claim.status,
                    "coverage": round(claim.coverage, 6),
                    "gap": claim.gap,
                    "evidence": [asdict(item) for item in claim.evidence],
                }
                for claim in self.claims
            ],
            "citations": {label: asdict(item) for label, item in self.citations.items()},
            "trace": self.trace,
            "validation": asdict(self.validation),
        }
