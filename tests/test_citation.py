import tempfile
import unittest
from pathlib import Path

from models.evidence import Evidence
from models.project import ResearchProject
from models.report import Report
from models.source import Source
from tools.citation import CitationChecker
from tools.storage import Storage


class CitationCheckerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()
        project = self.storage.create_project(ResearchProject(None, "项目", "问题"))
        source = self.storage.create_source(Source(None, project.id, "来源", url="https://example.org"))
        self.project_id = project.id
        self.evidence = self.storage.create_evidence(
            Evidence(None, project.id, source.id, None, "原文")
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_validates_existing_and_unknown_citations(self):
        checker = CitationChecker(self.storage)
        result = checker.validate_report(Report(None, self.project_id, 1, f"[E{self.evidence.id}] [E999]"))
        self.assertFalse(result.valid)
        self.assertEqual(result.citation_ids, [self.evidence.id, 999])
        self.assertEqual(len(result.errors), 1)

    def test_ignores_duplicate_citations(self):
        result = CitationChecker(self.storage).validate_content(
            self.project_id, f"[E{self.evidence.id}] [E{self.evidence.id}]"
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.citation_ids, [self.evidence.id])


if __name__ == "__main__":
    unittest.main()
