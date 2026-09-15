"""Small application entry point for the first development phase.

The web API will be added in a later phase. For now, running this module
initializes the local SQLite schema so the project has a deterministic smoke
entry point without requiring external services.
"""

from __future__ import annotations

from config import get_settings
from tools.storage import Storage


def create_storage() -> Storage:
    """Create and initialize the configured storage instance."""

    settings = get_settings()
    settings.ensure_data_directory()
    storage = Storage(settings.database_path)
    storage.initialize()
    return storage


def main() -> None:
    storage = create_storage()
    print(f"{storage.app_name} database ready: {storage.database_path}")


if __name__ == "__main__":
    main()
