"""Search provider abstractions and deterministic demo data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(slots=True)
class SourceCandidate:
    """Provider-neutral metadata returned by a search service."""

    title: str
    url: str
    authors: str | None = None
    institution: str | None = None
    published_at: str | None = None
    abstract: str | None = None
    source_type: str = "web"


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 5) -> list[SourceCandidate]:
        """Return normalized candidates for a query."""


class DemoSearchProvider:
    """Offline provider used for demos and repeatable tests."""

    def search(self, query: str, limit: int = 5) -> list[SourceCandidate]:
        candidates = [
            SourceCandidate(
                title=f"研究综述：{query}",
                url="https://demo.researchgraph.local/review",
                authors="ResearchGraph Demo Team",
                institution="ResearchGraph Demo Lab",
                published_at="2024",
                abstract="这是用于演示证据链的数据来源。",
                source_type="report",
            ),
            SourceCandidate(
                title=f"实证研究：{query}",
                url="https://demo.researchgraph.local/empirical",
                authors="Demo Author",
                institution="Example University",
                published_at="2023",
                abstract="这是用于测试来源保存和去重的示例摘要。",
                source_type="paper",
            ),
        ]
        return candidates[: max(0, limit)]


class SemanticScholarProvider:
    """Minimal Semantic Scholar adapter using its public paper search API."""

    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, timeout: float = 15.0, api_key: str | None = None):
        self.timeout = timeout
        self.api_key = api_key

    def search(self, query: str, limit: int = 5) -> list[SourceCandidate]:
        if not query.strip() or limit <= 0:
            return []
        url = f"{self.endpoint}?query={quote(query)}&limit={min(limit, 100)}&fields=title,authors,year,url,abstract,venue"
        headers = {"User-Agent": "ResearchGraph/0.1"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        request = Request(url, headers=headers)
        with urlopen(request, timeout=self.timeout) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        candidates: list[SourceCandidate] = []
        for paper in payload.get("data", []):
            paper_url = paper.get("url") or ""
            title = (paper.get("title") or "").strip()
            if not title or not paper_url:
                continue
            authors = ", ".join(
                author.get("name", "") for author in paper.get("authors", []) if author.get("name")
            ) or None
            candidates.append(SourceCandidate(
                title=title,
                url=paper_url,
                authors=authors,
                institution=paper.get("venue") or None,
                published_at=str(paper["year"]) if paper.get("year") else None,
                abstract=paper.get("abstract"),
                source_type="paper",
            ))
        return candidates


class CrossrefProvider:
    """Search scholarly works through Crossref's public REST API."""

    endpoint = "https://api.crossref.org/works"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[SourceCandidate]:
        if not query.strip() or limit <= 0:
            return []
        fields = "DOI,title,author,published,URL,abstract,publisher,type"
        url = f"{self.endpoint}?query={quote(query)}&rows={min(limit, 100)}&select={fields}"
        request = Request(url, headers={"User-Agent": "ResearchGraph/0.1 (mailto:researchgraph@example.com)"})
        with urlopen(request, timeout=self.timeout) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        results = []
        for work in payload.get("message", {}).get("items", []):
            titles = work.get("title") or []
            title = str(titles[0]).strip() if titles else ""
            doi = work.get("DOI")
            url = work.get("URL") or (f"https://doi.org/{doi}" if doi else "")
            if not title or not url:
                continue
            authors = ", ".join(" ".join(filter(None, (a.get("given"), a.get("family"))))
                                for a in work.get("author", [])) or None
            date_parts = (work.get("published") or {}).get("date-parts") or []
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else None
            results.append(SourceCandidate(
                title=title, url=url, authors=authors, institution=work.get("publisher"),
                published_at=year, abstract=work.get("abstract"),
                source_type=str(work.get("type") or "paper"),
            ))
        return results


class FallbackSearchProvider:
    """Use a secondary real provider when the primary is throttled or unavailable."""

    def __init__(self, primary: SearchProvider, fallback: SearchProvider):
        self.primary, self.fallback = primary, fallback

    def search(self, query: str, limit: int = 5) -> list[SourceCandidate]:
        try:
            results = self.primary.search(query, limit)
            return results if results else self.fallback.search(query, limit)
        except (HTTPError, TimeoutError, OSError):
            return self.fallback.search(query, limit)
