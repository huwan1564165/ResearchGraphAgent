import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Settings, load_dotenv


class SettingsTest(unittest.TestCase):
    def test_defaults_point_to_local_data_directory(self):
        settings = Settings()
        self.assertEqual(settings.app_name, "ResearchGraph")
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.database_path.name, "researchgraph.db")
        self.assertEqual(settings.database_path.parent.name, "data")

    def test_dotenv_loads_values_without_overwriting_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text('OPENAI_API_KEY="from-file"\nRESEARCHGRAPH_SEARCH_PROVIDER=semantic_scholar\n', encoding="utf-8")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "from-shell"}, clear=True):
                load_dotenv(dotenv)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "from-shell")
                self.assertEqual(os.environ["RESEARCHGRAPH_SEARCH_PROVIDER"], "semantic_scholar")

    def test_environment_overrides_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "custom.db"
            with patch.dict(os.environ, {
                "RESEARCHGRAPH_APP_NAME": "ResearchGraph Test",
                "RESEARCHGRAPH_ENV": "test",
                "RESEARCHGRAPH_DB_PATH": str(database_path),
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "OPENAI_BASE_URL": "https://gateway.example/v1",
            }, clear=False):
                settings = Settings.from_env()
        self.assertEqual(settings.app_name, "ResearchGraph Test")
        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.database_path, database_path)
        self.assertEqual(settings.openai_api_key, "test-key")
        self.assertEqual(settings.openai_model, "test-model")
        self.assertEqual(settings.openai_base_url, "https://gateway.example/v1")

