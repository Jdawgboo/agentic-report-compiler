from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from report_compiler.agent import ResearchAgent, write_artifacts
from report_compiler.citation_checker import validate_report
from report_compiler.loader import load_corpus
from report_compiler.models import Evidence
from report_compiler.retriever import retrieve


class ResearchAgentTests(unittest.TestCase):
    def make_sources(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "sensor.md").write_text(
            "# Sensor note\n\nVibration increased from 2 mm/s to 4 mm/s after a load change. "
            "The sensor sampled the bearing housing at 10 kHz.\n",
            encoding="utf-8",
        )
        (root / "maintenance.txt").write_text(
            "Technicians observed higher vibration under sustained load. "
            "They recommended a follow-up inspection before the next production run.\n",
            encoding="utf-8",
        )
        return root

    def test_loader_preserves_stable_line_spans(self) -> None:
        root = self.make_sources()
        chunks = load_corpus(root, chunk_lines=1)
        self.assertEqual([chunk.source_path for chunk in chunks], ["maintenance.txt", "maintenance.txt", "sensor.md", "sensor.md", "sensor.md"])
        self.assertEqual(chunks[-1].line_start, 3)

    def test_retriever_returns_ranked_lexical_evidence(self) -> None:
        evidence = retrieve("vibration load", load_corpus(self.make_sources()), top_k=3)
        self.assertEqual(len(evidence), 2)
        self.assertTrue(all(item.coverage == 1.0 for item in evidence))
        self.assertGreaterEqual(evidence[0].score, evidence[1].score)

    def test_search_tool_is_closed_before_retrieval_state(self) -> None:
        agent = ResearchAgent()
        with self.assertRaises(RuntimeError):
            agent.search_tool("vibration")

    def test_insufficient_evidence_becomes_visible_gap(self) -> None:
        result = ResearchAgent().run("astronomy observations", self.make_sources())
        self.assertTrue(result.validation.passed)
        self.assertIn("Evidence gap", result.report)
        self.assertEqual(result.claims[0].status, "INSUFFICIENT_EVIDENCE")

    def test_citation_checker_rejects_unknown_marker(self) -> None:
        evidence = Evidence("chunk", "source.md", 1, 1, "A supported observation.", 1.0, 1.0, "observation")
        validation = validate_report('- "A supported observation." [S99]\n', {"S1": evidence})
        self.assertFalse(validation.passed)
        self.assertIn("unknown citation", validation.errors[0])

    def test_run_is_deterministic_and_writes_audit_artifacts(self) -> None:
        root = self.make_sources()
        first = ResearchAgent().run("vibration load", root)
        second = ResearchAgent().run("vibration load", root)
        self.assertTrue(first.validation.passed)
        self.assertEqual(first.report, second.report)
        self.assertEqual(first.manifest(), second.manifest())

        with tempfile.TemporaryDirectory() as target:
            write_artifacts(first, target)
            manifest = json.loads((Path(target) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["final_state"], "DONE")
            self.assertTrue((Path(target) / "report.md").exists())
            self.assertTrue((Path(target) / "validation.json").exists())


if __name__ == "__main__":
    unittest.main()
