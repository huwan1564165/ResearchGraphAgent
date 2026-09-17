"""Search provider abstractions and deterministic demo data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
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

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[SourceCandidate]:
        if not query.strip() or limit <= 0:
            return []
        url = f"{self.endpoint}?query={quote(query)}&limit={min(limit, 100)}&fields=title,authors,year,url,abstract,venue"
        request = Request(url, headers={"User-Agent": "ResearchGraph/0.1"})
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
