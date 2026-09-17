import tempfile
import unittest
from pathlib import Path

from agent.coordinator import ResearchCoordinator
from models.project import ResearchProject
from tools.storage import Storage


class CoordinatorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_runs_demo_flow_from_confirmed_questions_to_report(self):
        coordinator = ResearchCoordinator(self.storage)
        project = coordinator.create_project(ResearchProject(
            None, "演示研究", "大语言模型是否提升学习效果？", subject="中学生", focus="学习效果"
        ))
        question_ids = coordinator.decompose(project.id)
        self.assertEqual(len(question_ids), 3)
        self.assertEqual(coordinator.confirm_questions(project.id), 3)
        result = coordinator.run(project.id, search_limit=2)
        self.assertEqual(len(result.search_runs), 3)
        self.assertTrue(result.evidence_ids)
        self.assertEqual(len(result.claim_ids), 3)
        self.assertEqual(result.report.version, 1)
        self.assertIn("证据明细", result.report.content)


if __name__ == "__main__":
    unittest.main()
