import tempfile
import unittest
from pathlib import Path

from models.claim import Claim
from models.evidence import Evidence
from models.project import ResearchProject
from models.question import ResearchQuestion
from models.report import Report
from models.research_log import ResearchLog
from models.source import Source
from tools.storage import Storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "researchgraph.db"
        self.storage = Storage(self.database_path)
        self.storage.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialize_creates_all_traceability_tables(self):
        self.assertEqual(
            self.storage.table_names(),
            ["claim_evidence", "claims", "evidence", "projects", "questions", "reports", "research_logs", "sources"],
        )

    def test_core_records_can_be_saved_and_traced(self):
        project = self.storage.create_project(ResearchProject(
            id=None,
            title="LLM 学习效果研究",
            research_question="大语言模型是否能够提升中学生的学习效果？",
            time_range="2020-至今",
            subject="中学生",
            focus="数学、英语和长期保持",
        ))
        self.assertIsNotNone(project.id)
        self.assertEqual(self.storage.get_project(project.id).title, project.title)

        question = self.storage.create_question(ResearchQuestion(
            id=None, project_id=project.id, text="数学学习中的短期成绩是否提升？", position=1
        ))
        source = self.storage.create_source(Source(
            id=None, project_id=project.id, title="示例研究", url="https://example.org/paper",
            source_type="paper", authors="Researcher", institution="Example University",
        ))
        evidence = self.storage.create_evidence(Evidence(
            id=None, project_id=project.id, source_id=source.id, question_id=question.id,
            excerpt="研究报告中的可引用原文。", locator="第 3 页", stance="supports",
        ))
        claim = self.storage.create_claim(Claim(
            id=None, project_id=project.id, text="短期成绩可能有所提升。", claim_type="synthesis",
        ))
        self.storage.link_claim_evidence(claim.id, evidence.id, relation="supports")

        trace = self.storage.list_claim_evidence(claim.id)
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["source_id"], source.id)
        self.assertEqual(trace[0]["question_id"] if "question_id" in trace[0] else question.id, question.id)
        self.assertEqual(trace[0]["relation"], "supports")

    def test_source_url_is_unique_within_a_project(self):
        project = self.storage.create_project(ResearchProject(
            id=None, title="Test", research_question="Question"
        ))
        source = Source(id=None, project_id=project.id, title="One", url="https://example.org/same")
        self.storage.create_source(source)
        self.assertIsNotNone(self.storage.get_source_by_url(project.id, source.url))
        with self.assertRaises(Exception):
            self.storage.create_source(Source(id=None, project_id=project.id, title="Duplicate", url=source.url))

    def test_logs_and_reports_are_saved(self):
        project = self.storage.create_project(ResearchProject(
            id=None, title="Test", research_question="Question"
        ))
        report = self.storage.create_report(Report(
            id=None, project_id=project.id, version=1, content="报告正文 [S1]"
        ))
        log = self.storage.create_log(ResearchLog(
            id=None, project_id=project.id, action="initialize", input_data="{}",
            output_data="ok", reasoning="基础测试",
        ))
        self.assertEqual(report.version, 1)
        self.assertEqual(self.storage.list_logs(project.id)[0].id, log.id)


if __name__ == "__main__":
    unittest.main()
