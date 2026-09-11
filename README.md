# Agentic Report Compiler

A deterministic, tool-routing research agent that turns a local folder of Markdown and text files into a cited Markdown evidence brief.

> **Current milestone:** a fully offline, standard-library MVP. It is deliberately **not** an LLM system: planning, retrieval, composition, and validation are deterministic so the run can be reproduced and inspected. A future adapter may add model-backed planning or retrieval without changing the control flow.

## Why this exists

Agentic systems should not depend on a prompt alone to stay grounded. This project makes the control flow explicit:

1. **Index** local source files into line-addressable chunks.
2. **Plan** a small queue of research sub-questions.
3. **Retrieve** lexical evidence through a tool gate that only opens after indexing.
4. **Evaluate** whether each sub-question has sufficient source coverage.
5. **Compose** an extractive report in which every evidence bullet has a citation.
6. **Verify** citation IDs and quoted spans before an output is accepted.

When evidence is insufficient, the report states the gap instead of guessing.

## What is implemented in this first milestone

- Offline ingestion of `.md` and `.txt` files
- Deterministic state-machine orchestration with bounded retrieval retries
- Local lexical retrieval with transparent scores
- Cited, extractive Markdown composition
- Evidence-gap disclosure and an auditable JSON manifest
- Citation validation that blocks dangling citations or unsupported quotes
- Unit tests and a GitHub Actions test workflow

## What is intentionally not implemented yet

- LLM drafting, semantic embeddings, web search, OCR, PDF/DOCX parsing, or PDF export
- Automated contradiction resolution or numeric computation
- Network calls or API-key dependencies

Those are documented extension paths, not claims about this MVP.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

report-compiler run \
  --request "What do the supplied notes say about vibration under load?" \
  --sources examples/sources \
  --out out
```

The command writes:

- `out/report.md` — cited evidence brief
- `out/manifest.json` — deterministic agent trace and source evidence
- `out/validation.json` — citation-verification result

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the state machine, data contracts, safeguards, and roadmap.

## Design principles

- **Evidence is data, not prompt context.** Only retrieved evidence records may appear in a grounded section.
- **Citations are checked mechanically.** A citation is not accepted just because it looks plausible.
- **Gaps are first-class output.** Missing coverage is rendered in the report and stored in the manifest.
- **Same inputs, same artifacts.** There is no randomness, network dependency, or hidden model call in the MVP.

## License

MIT — see [LICENSE](LICENSE).