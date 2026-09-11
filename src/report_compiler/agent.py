"""State-machine orchestration for grounded local research."""

from __future__ import annotations

import json
from pathlib import Path

from .citation_checker import validate_report
from .composer import compose_report
from .loader import load_corpus
from .models import AgentState, Claim, Evidence, RunResult, ValidationResult
from .planner import plan_request
from .retriever import retrieve, tokenize


class ResearchAgent:
    """A bounded, deterministic tool-routing research agent.

    The agent never calls a network service or a language model. Its value is the
    explicit transition log, source-evidence boundary, and verification gate.
    """

    def __init__(self, min_evidence: int = 2, min_coverage: float = 0.35, top_k: int = 3):
        if min_evidence < 1:
            raise ValueError("min_evidence must be at least 1")
        if not 0 < min_coverage <= 1:
            raise ValueError("min_coverage must be between 0 and 1")
        self.min_evidence = min_evidence
        self.min_coverage = min_coverage
        self.top_k = top_k
        self._state = AgentState.INIT
        self._chunks = []

    def _record(self, trace: list[dict[str, object]], action: str, detail: str) -> None:
        trace.append({"step": len(trace) + 1, "state": self._state.value, "action": action, "detail": detail})

    def search_tool(self, query: str) -> list[Evidence]:
        """Route a retrieval request only after indexing has completed."""
        if self._state != AgentState.RETRIEVING:
            raise RuntimeError("search_tool is unavailable until the agent enters RETRIEVING")
        return retrieve(query, self._chunks, top_k=self.top_k)

    def _broaden_query(self, claim: str) -> str:
        terms = tokenize(claim)
        return " ".join(sorted(set(terms), key=lambda item: (-len(item), item))[:3])

    def _evaluate_claim(self, claim: Claim, trace: list[dict[str, object]]) -> None:
        self._state = AgentState.RETRIEVING
        evidence = self.search_tool(claim.text)
        self._record(trace, "retrieve", f"{claim.claim_id}: {len(evidence)} initial evidence chunks")

        self._state = AgentState.EVALUATING
        coverage = max((item.coverage for item in evidence), default=0.0)
        sufficient = len(evidence) >= self.min_evidence and coverage >= self.min_coverage

        if not sufficient:
            retry_query = self._broaden_query(claim.text)
            if retry_query and retry_query != claim.text.lower():
                self._state = AgentState.RETRIEVING
                retry_evidence = self.search_tool(retry_query)
                merged = {item.chunk_id: item for item in evidence}
                merged.update({item.chunk_id: item for item in retry_evidence})
                evidence = sorted(
                    merged.values(),
                    key=lambda item: (-item.score, item.source_path, item.line_start, item.chunk_id),
                )[: self.top_k]
                self._record(trace, "retry_retrieve", f"{claim.claim_id}: {len(evidence)} chunks after one bounded retry")
                self._state = AgentState.EVALUATING
                coverage = max((item.coverage for item in evidence), default=0.0)
                sufficient = len(evidence) >= self.min_evidence and coverage >= self.min_coverage

        claim.coverage = coverage
        claim.evidence = evidence if sufficient else []
        if sufficient:
            claim.status = "GROUNDED"
            self._record(trace, "evaluate", f"{claim.claim_id}: grounded with coverage {coverage:.3f}")
        else:
            claim.status = "INSUFFICIENT_EVIDENCE"
            claim.gap = (
                f"Found {len(evidence)} chunks with best lexical coverage {coverage:.3f}; "
                f"requires at least {self.min_evidence} chunks and {self.min_coverage:.3f} coverage."
            )
            self._record(trace, "evaluate", f"{claim.claim_id}: evidence gap")

    def run(self, request: str, source_directory: str | Path) -> RunResult:
        """Compile a cited evidence brief and its auditable run record."""
        self._state = AgentState.INIT
        trace: list[dict[str, object]] = []
        self._record(trace, "start", "offline deterministic research run")
        claims: list[Claim] = []
        citations: dict[str, Evidence] = {}
        report = ""

        try:
            self._chunks = load_corpus(source_directory)
            self._state = AgentState.INDEXED
            self._record(trace, "index", f"indexed {len(self._chunks)} source chunks")

            claims = plan_request(request)
            self._state = AgentState.PLANNED
            self._record(trace, "plan", f"planned {len(claims)} research sub-question(s)")

            for claim in claims:
                self._evaluate_claim(claim, trace)

            self._state = AgentState.SYNTHESIZING
            report, citations = compose_report(request, claims)
            self._record(trace, "compose", f"composed report with {len(citations)} cited source chunk(s)")

            self._state = AgentState.VERIFYING
            validation = validate_report(report, citations)
            self._record(trace, "verify", "citation validation passed" if validation.passed else "citation validation failed")
            self._state = AgentState.DONE if validation.passed else AgentState.ABORTED
            return RunResult(request, self._state, report, claims, citations, trace, validation)
        except (OSError, ValueError, RuntimeError) as error:
            self._state = AgentState.ABORTED
            self._record(trace, "abort", str(error))
            report = "# Evidence Brief\n\n> **Run aborted:** the source corpus could not be processed safely.\n"
            validation = ValidationResult(passed=False, errors=[str(error)])
            return RunResult(request, self._state, report, claims, citations, trace, validation)


def write_artifacts(result: RunResult, output_directory: str | Path) -> None:
    """Write the report and audit artifacts using stable JSON serialization."""
    target = Path(output_directory)
    target.mkdir(parents=True, exist_ok=True)
    (target / "report.md").write_text(result.report, encoding="utf-8")
    (target / "manifest.json").write_text(
        json.dumps(result.manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "validation.json").write_text(
        json.dumps({"passed": result.validation.passed, "errors": result.validation.errors}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
