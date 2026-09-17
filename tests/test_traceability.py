import tempfile
import unittest
from pathlib import Path

from agent.traceability import TraceabilityService
from models.claim import Claim
from models.evidence import Evidence
from models.project import ResearchProject
from models.source import Source
from tools.storage import Storage


class TraceabilityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()
        project = self.storage.create_project(ResearchProject(None, "项目", "问题"))
        source = self.storage.create_source(Source(None, project.id, "来源", url="https://example.org"))
        evidence = self.storage.create_evidence(
            Evidence(None, project.id, source.id, None, "可追溯原文", locator="第 1 页")
        )
        claim = self.storage.create_claim(Claim(None, project.id, "结论", confidence=0.8))
        self.storage.link_claim_evidence(claim.id, evidence.id, "supports")
        self.claim_id = claim.id

    def tearDown(self):
        self.temp.cleanup()

    def test_returns_nested_claim_evidence_source_chain(self):
        trace = TraceabilityService(self.storage).trace_claim(self.claim_id)
        self.assertEqual(trace["claim"]["text"], "结论")
        self.assertEqual(trace["evidence"][0]["relation"], "supports")
        self.assertEqual(trace["evidence"][0]["source"]["url"], "https://example.org")

    def test_missing_claim_is_rejected(self):
        with self.assertRaises(ValueError):
            TraceabilityService(self.storage).trace_claim(999)


if __name__ == "__main__":
    unittest.main()
