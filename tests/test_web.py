import io
import tempfile
import unittest
from pathlib import Path

from tools.storage import Storage
from web.api import create_app
from web.ui import WebApplication


class WebTest(unittest.TestCase):
    def test_home_page_contains_workflow_form(self):
        with tempfile.TemporaryDirectory() as directory:
            application = WebApplication(create_app(Storage(Path(directory) / "db.sqlite")))
            result = {}
            body = b"".join(application({
                "REQUEST_METHOD": "GET", "PATH_INFO": "/", "wsgi.input": io.BytesIO(b"")
            }, lambda status, headers: result.update(status=status)))
        self.assertEqual(result["status"], "200 OK")
        self.assertIn("创建项目", body.decode("utf-8"))
        self.assertIn("确认并运行研究", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
