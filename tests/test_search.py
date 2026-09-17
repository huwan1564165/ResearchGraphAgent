import tempfile
import unittest
from pathlib import Path

from agent.researcher import Researcher
from models.project import ResearchProject
from tools.search import DemoSearchProvider, SourceCandidate
from tools.storage import Storage


class DuplicateProvider:
    def search(self, query: str, limit: int = 5):
        return [
            SourceCandidate("同一来源", "https://example.org/one", abstract=query),
            SourceCandidate("同一来源（重复结果）", "https://example.org/one"),
            SourceCandidate("另一个来源", "https://example.org/two"),
        ][:limit]


class SearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()
        self.project = self.storage.create_project(ResearchProject(None, "测试项目", "测试问题"))

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_provider_returns_normalized_candidates(self):
        results = DemoSearchProvider().search("中学生学习效果", limit=1)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].title)
        self.assertTrue(results[0].url.startswith("https://"))

    def test_researcher_saves_sources_deduplicates_and_logs(self):
        run = Researcher(self.storage, DuplicateProvider()).search_and_save(
            self.project.id, "数学学习", question_id=3, limit=5
        )
        self.assertEqual(run.new_source_count, 2)
        self.assertEqual(run.duplicate_count, 1)
        self.assertEqual(len(run.source_ids), 3)
        self.assertEqual(run.source_ids[0], run.source_ids[1])
        logs = self.storage.list_logs(self.project.id)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].action, "search")
        self.assertIn("数学学习", logs[0].input_data)

    def test_same_url_is_deduplicated_across_repeated_searches(self):
        researcher = Researcher(self.storage, DemoSearchProvider())
        first = researcher.search_and_save(self.project.id, "问题")
        second = researcher.search_and_save(self.project.id, "问题")
        self.assertEqual(first.new_source_count, 2)
        self.assertEqual(second.new_source_count, 0)
        self.assertEqual(second.duplicate_count, 2)


if __name__ == "__main__":
    unittest.main()
