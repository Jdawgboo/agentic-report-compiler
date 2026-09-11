# Architecture: deterministic spine, explicit agent loop

This repository is a deliberately small, offline implementation of the engineering principles behind a grounded report agent. Its control flow is a state machine rather than an opaque prompt chain.

```text
INIT → INDEXED → PLANNED → RETRIEVING → EVALUATING
                                      ↘ (one bounded retry)
                 → SYNTHESIZING → VERIFYING → DONE | ABORTED
```

## Components

| Component | Responsibility | Deterministic guarantee |
| --- | --- | --- |
| Loader | Reads Markdown/text files and creates line-addressable chunks | Files and chunks are sorted by relative path and line range |
| Planner | Breaks a request into a bounded queue of sub-questions | Same request produces the same queue |
| Retriever | Scores chunks by lexical query-token coverage | Scores and tie-breaks are stable |
| Evaluator | Applies minimum-evidence and token-coverage thresholds | Insufficient claims become explicit gaps |
| Composer | Emits quoted evidence bullets and citation markers | No free-form unsupported claim is produced |
| Validator | Checks citation IDs and quoted spans against source chunks | Any invalid citation aborts the run |
| Manifest writer | Serializes state transitions, decisions, evidence, and verdict | JSON is sorted and replayable |

## Data boundary

The agent never treats untracked text as report evidence. A report citation resolves to an `Evidence` record containing:

- stable chunk ID
- source-relative path
- inclusive line span
- original quoted text
- retrieval score
- query that retrieved it

The report composer only emits literal quoted spans from those records. This makes the grounding contract testable without relying on model behavior.

## Safeguards

1. Retrieval is unavailable before the source corpus reaches `INDEXED`.
2. A claim needs enough retrieved chunks and lexical token coverage to be marked grounded.
3. An ungrounded claim is rendered as an **Evidence gap**, never omitted or completed from memory.
4. Every evidence bullet requires one or more citation markers.
5. The validator verifies every marker resolves to a known evidence record and every quoted span still occurs in its cited source.
6. A failed validation transitions the job to `ABORTED` and returns a non-zero CLI exit code.

## Honest scope

The MVP demonstrates agent control flow and grounding constraints, not generative intelligence. It does not include an LLM, vector database, web search, OCR, or PDF rendering. Future adapters can add those capabilities behind the existing planner/retriever interfaces while preserving the validation gate.

## Roadmap

- **M1 (current):** local text/Markdown research loop, citations, manifest, tests
- **M2:** pluggable semantic retriever with evaluation fixtures
- **M3:** optional model-backed planner/drafter behind a provider interface
- **M4:** document parsing, numeric-analysis tools, contradiction detection, and PDF export
