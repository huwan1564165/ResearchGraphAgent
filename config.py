"""Application configuration for ResearchGraph.

The first phase keeps configuration deliberately small and environment based.
No database file is created while importing this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path | None = None) -> None:
    """Load simple KEY=VALUE settings without adding a third-party dependency.

    Existing process environment variables always win over values in ``.env``.
    """
    dotenv_path = path or PROJECT_ROOT / ".env"
    if not dotenv_path.is_file():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key.startswith("#"):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the application and storage layer."""

    app_name: str = "ResearchGraph"
    environment: str = "development"
    database_path: Path = PROJECT_ROOT / "data" / "researchgraph.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    search_provider: str = "demo"
    semantic_scholar_api_key: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from shell variables and the optional project ``.env``."""

        load_dotenv()
        configured_path = os.getenv("RESEARCHGRAPH_DB_PATH")
        database_path = Path(configured_path) if configured_path else cls.database_path
        return cls(
            app_name=os.getenv("RESEARCHGRAPH_APP_NAME", cls.app_name),
            environment=os.getenv("RESEARCHGRAPH_ENV", cls.environment),
            database_path=database_path,
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
            openai_base_url=os.getenv("OPENAI_BASE_URL", cls.openai_base_url),
            search_provider=os.getenv("RESEARCHGRAPH_SEARCH_PROVIDER", cls.search_provider),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY") or None,
        )

    def ensure_data_directory(self) -> Path:
        """Create the parent directory for the configured SQLite file."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return self.database_path.parent


def get_settings() -> Settings:
    """Return settings for the current process."""

    return Settings.from_env()
