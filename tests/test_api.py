import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.storage import Storage
from web.api import create_app


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(Storage(Path(self.temp.name) / "db.sqlite"))

    def tearDown(self):
        self.temp.cleanup()

    def request(self, method, path, payload=None):
        raw = json.dumps(payload or {}, ensure_ascii=False).encode()
        environ = {
            "REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw),
        }
        result = {}
        def start_response(status, headers):
            result["status"] = status
        body = b"".join(self.app(environ, start_response))
        return result["status"], json.loads(body)

    def test_questions_can_be_added_updated_and_deleted(self):
        _, created = self.request("POST", "/api/projects", {"title": "编辑", "research_question": "问题"})
        project_id = created["project"]["id"]
        status, added = self.request("POST", f"/api/projects/{project_id}/questions/add", {"text": "新问题"})
        self.assertEqual(status, "200 OK")
        question_id = added["question"]["id"]
        status, updated = self.request("PATCH", f"/api/projects/{project_id}/questions/{question_id}", {"text": "修改后"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(updated["question"]["text"], "修改后")
        status, deleted = self.request("DELETE", f"/api/projects/{project_id}/questions/{question_id}")
        self.assertEqual(status, "200 OK")
        self.assertTrue(deleted["deleted"])

    def test_evidence_endpoint_returns_source_details(self):
        _, created = self.request("POST", "/api/projects", {"title": "证据", "research_question": "问题"})
        project_id = created["project"]["id"]
        # The endpoint should return a stable shape even before a run creates evidence.
        status, result = self.request("GET", f"/api/projects/{project_id}/evidence")
        self.assertEqual(status, "200 OK")
        self.assertEqual(result["evidence"], [])

    def test_project_questions_and_run_endpoints(self):
        status, created = self.request("POST", "/api/projects", {
            "title": "API 测试", "research_question": "测试问题"
        })
        self.assertEqual(status, "200 OK")
        project_id = created["project"]["id"]
        status, questions = self.request("POST", f"/api/projects/{project_id}/questions")
        self.assertEqual(status, "200 OK")
        self.assertEqual(len(questions["question_ids"]), 3)
        status, confirmed = self.request("POST", f"/api/projects/{project_id}/questions/confirm")
        self.assertEqual(confirmed["confirmed"], 3)
        status, result = self.request("POST", f"/api/projects/{project_id}/run")
        self.assertEqual(status, "200 OK")
        self.assertTrue(result["report"]["content"])


if __name__ == "__main__":
    unittest.main()
