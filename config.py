"""Application configuration for ResearchGraph.

The first phase keeps configuration deliberately small and environment based.
No database file is created while importing this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the application and storage layer."""

    app_name: str = "ResearchGraph"
    environment: str = "development"
    database_path: Path = PROJECT_ROOT / "data" / "researchgraph.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables with local defaults."""

        configured_path = os.getenv("RESEARCHGRAPH_DB_PATH")
        database_path = Path(configured_path) if configured_path else cls.database_path
        return cls(
            app_name=os.getenv("RESEARCHGRAPH_APP_NAME", cls.app_name),
            environment=os.getenv("RESEARCHGRAPH_ENV", cls.environment),
            database_path=database_path,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
            openai_base_url=os.getenv("OPENAI_BASE_URL", cls.openai_base_url),
        )

    def ensure_data_directory(self) -> Path:
        """Create the parent directory for the configured SQLite file."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return self.database_path.parent


def get_settings() -> Settings:
    """Return settings for the current process."""

    return Settings.from_env()
