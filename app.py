"""ResearchGraph WSGI application entry point."""

from __future__ import annotations

from config import get_settings
from tools.llm import OpenAIClient
from tools.search import CrossrefProvider, DemoSearchProvider, FallbackSearchProvider, SemanticScholarProvider
from tools.storage import Storage
from web.api import create_app
from web.ui import WebApplication


def create_storage() -> Storage:
    settings = get_settings()
    settings.ensure_data_directory()
    storage = Storage(settings.database_path)
    storage.initialize()
    return storage


def create_application() -> WebApplication:
    settings = get_settings()
    llm_client = None
    if settings.openai_api_key:
        llm_client = OpenAIClient(settings.openai_api_key, settings.openai_model,
                                  settings.openai_base_url)
    if settings.search_provider == "semantic_scholar":
        provider = FallbackSearchProvider(
            SemanticScholarProvider(api_key=settings.semantic_scholar_api_key), CrossrefProvider()
        )
    elif settings.search_provider == "crossref":
        provider = CrossrefProvider()
    else:
        provider = DemoSearchProvider()
    return WebApplication(create_app(create_storage(), llm_client, provider))


def main() -> None:
    from wsgiref.simple_server import make_server
    application = create_application()
    print("ResearchGraph running at http://127.0.0.1:8000")
    with make_server("127.0.0.1", 8000, application) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
