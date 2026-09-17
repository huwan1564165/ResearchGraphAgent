import tempfile
import unittest
from pathlib import Path

from agent.evidence import EvidenceService, RuleBasedEvidenceExtractor
from models.claim import Claim
from models.project import ResearchProject
from models.question import ResearchQuestion
from models.source import Source
from tools.storage import Storage


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()
        self.project = self.storage.create_project(ResearchProject(None, "测试", "学习效果"))
        self.question = self.storage.create_question(ResearchQuestion(None, self.project.id, "数学学习效果"))

    def tearDown(self):
        self.temp.cleanup()

    def test_extractor_returns_original_sentences_with_locators(self):
        source = Source(
            id=1, project_id=self.project.id, title="示例", url="https://example.org",
            abstract="研究调查显示数学成绩提升了 12%。长期保持仍需要更多数据。",
        )
        drafts = RuleBasedEvidenceExtractor().extract(source, "数学成绩", limit=2)
        self.assertEqual(len(drafts), 2)
        self.assertIn("12%", drafts[0].excerpt)
        self.assertTrue(drafts[0].locator)
        self.assertTrue(drafts[0].uncertainty)

    def test_service_saves_evidence_and_attaches_it_to_claim(self):
        source = self.storage.create_source(Source(
            None, self.project.id, "示例论文", url="https://example.org/paper",
            abstract="实验结果显示成绩提升。长期知识保持尚不确定。",
        ))
        evidence = EvidenceService(self.storage).extract_and_save(
            self.project.id, self.question.id, self.question.text, [source.id]
        )
        self.assertEqual(len(evidence), 2)
        self.assertEqual(self.storage.list_evidence(self.project.id, self.question.id)[0].source_id, source.id)
        claim = self.storage.create_claim(Claim(None, self.project.id, "成绩可能提升"))
        EvidenceService(self.storage).attach_to_claim(claim.id, [item.id for item in evidence])
        links = self.storage.list_claim_evidence(claim.id)
        self.assertEqual(len(links), 2)
        self.assertEqual(self.storage.list_logs(self.project.id)[0].action, "evidence_extraction")
