import tempfile
import unittest
from pathlib import Path

from agent.reporting import ReportService
from agent.synthesis import SynthesisService
from models.claim import Claim
from models.evidence import Evidence
from models.project import ResearchProject
from models.source import Source
from tools.storage import Storage


class SynthesisReportingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()
        self.project = self.storage.create_project(ResearchProject(
            None, "测试报告", "研究问题", time_range="2020-至今", subject="研究对象", focus="重点"
        ))
        source = self.storage.create_source(Source(None, self.project.id, "来源", url="https://example.org"))
        self.support = self.storage.create_evidence(Evidence(None, self.project.id, source.id, None, "支持原文", stance="supports"))
        self.opposition = self.storage.create_evidence(Evidence(None, self.project.id, source.id, None, "相反原文", stance="opposes"))
        self.claim = self.storage.create_claim(Claim(None, self.project.id, "测试结论"))
        self.storage.link_claim_evidence(self.claim.id, self.support.id, "supports")
        self.storage.link_claim_evidence(self.claim.id, self.opposition.id, "opposes")

    def tearDown(self):
        self.temp.cleanup()

    def test_synthesis_is_cautious_when_evidence_conflicts(self):
        result = SynthesisService(self.storage).synthesize_claim(self.claim.id)
        self.assertEqual(result.supporting_evidence_ids, [self.support.id])
        self.assertEqual(result.opposing_evidence_ids, [self.opposition.id])
        self.assertEqual(result.confidence, 0.5)
        self.assertIn("不能作出确定结论", result.conclusion)
        self.assertEqual(self.storage.get_claim(self.claim.id).confidence, 0.5)

    def test_report_is_saved_with_version_and_traceability(self):
        report = ReportService(self.storage).generate(self.project.id)
        self.assertEqual(report.version, 1)
        self.assertIn("测试结论", report.content)
        self.assertIn(f"[E{self.support.id}]", report.content)
        self.assertIn("来源", report.content)
        self.assertIn("https://example.org", report.content)
        self.assertIn("时间范围：2020-至今", report.content)
        self.assertIn("## 6. 来源列表", report.content)
        self.assertEqual(self.storage.list_logs(self.project.id)[-1].action, "report_generation")


if __name__ == "__main__":
    unittest.main()
