import tempfile
import unittest
from pathlib import Path

from agent.decomposition import suggest_questions
from models.project import ResearchProject
from tools.storage import Storage


class DecompositionTest(unittest.TestCase):
    def test_suggestions_are_deterministic_and_distinct(self):
        project = ResearchProject(7, "示例", "复杂问题", "2020-至今", "中国", "中学生", "数学和英语")
        questions = suggest_questions(project)
        self.assertEqual(len(questions), 3)
        self.assertEqual([q.position for q in questions], [1, 2, 3])
        self.assertEqual(len({q.text for q in questions}), 3)
        self.assertTrue(all(project.subject in q.text for q in questions))


class QuestionEditingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "db.sqlite")
        self.storage.initialize()
        from models.project import ResearchProject
        self.project = self.storage.create_project(ResearchProject(None, "测试", "问题"))

    def tearDown(self):
        self.temp.cleanup()

    def test_add_edit_delete_and_confirm_questions(self):
        from models.question import ResearchQuestion
        first = self.storage.create_question(ResearchQuestion(None, self.project.id, "原问题"))
        second = self.storage.create_question(ResearchQuestion(None, self.project.id, "删除问题", 2))
        updated = self.storage.update_question(first.id, text="修改后的问题")
        self.assertEqual(updated.text, "修改后的问题")
        self.assertTrue(self.storage.delete_question(second.id))
        self.assertEqual(self.storage.confirm_questions(self.project.id), 1)
        saved = self.storage.list_questions(self.project.id)[0]
        self.assertTrue(saved.is_confirmed)
        self.assertEqual(saved.status, "confirmed")
        self.assertEqual(self.storage.get_project(self.project.id).status, "questions_confirmed")
