"""Command-line interface for offline report compilation."""

from __future__ import annotations

import argparse
from typing import Sequence

from .agent import ResearchAgent, write_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile a cited evidence brief from local text and Markdown files.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run", help="run the deterministic research agent")
    run.add_argument("--request", required=True, help="research question to ground in the supplied sources")
    run.add_argument("--sources", required=True, help="directory containing .md and .txt source documents")
    run.add_argument("--out", required=True, help="directory for report.md, manifest.json, and validation.json")
    run.add_argument("--min-evidence", type=int, default=2, help="minimum source chunks required for a grounded finding")
    run.add_argument("--min-coverage", type=float, default=0.35, help="minimum lexical query-token coverage")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    agent = ResearchAgent(min_evidence=args.min_evidence, min_coverage=args.min_coverage)
    result = agent.run(args.request, args.sources)
    write_artifacts(result, args.out)
    print(f"Final state: {result.state.value}")
    print(f"Artifacts: {args.out}/report.md, {args.out}/manifest.json, {args.out}/validation.json")
    if result.validation.errors:
        for error in result.validation.errors:
            print(f"Validation error: {error}")
    return 0 if result.validation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
