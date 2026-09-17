"""Search orchestration: query a provider, save sources, and log the run."""

from __future__ import annotations

import json
from dataclasses import dataclass

from models.research_log import ResearchLog
from models.source import Source
from tools.search import SearchProvider
from tools.storage import Storage


@dataclass(slots=True)
class SearchRun:
    query: str
    source_ids: list[int]
    new_source_count: int
    duplicate_count: int
    log_id: int


class Researcher:
    def __init__(self, storage: Storage, provider: SearchProvider):
        self.storage = storage
        self.provider = provider

    def search_and_save(self, project_id: int, query: str, question_id: int | None = None,
                        limit: int = 5) -> SearchRun:
        candidates = self.provider.search(query, limit=limit)
        source_ids: list[int] = []
        new_count = 0
        duplicate_count = 0
        for candidate in candidates:
            existing = self.storage.get_source_by_url(project_id, candidate.url)
            if existing is not None:
                source_ids.append(existing.id)
                duplicate_count += 1
                continue
            saved = self.storage.create_source(Source(
                id=None,
                project_id=project_id,
                title=candidate.title,
                authors=candidate.authors,
                institution=candidate.institution,
                published_at=candidate.published_at,
                url=candidate.url,
                abstract=candidate.abstract,
                source_type=candidate.source_type,
            ))
            source_ids.append(saved.id)
            new_count += 1

        log = self.storage.create_log(ResearchLog(
            id=None,
            project_id=project_id,
            action="search",
            input_data=json.dumps({"query": query, "question_id": question_id, "limit": limit}, ensure_ascii=False),
            output_data=json.dumps({"source_ids": source_ids, "candidates": len(candidates),
                                    "new_sources": new_count, "duplicates": duplicate_count}, ensure_ascii=False),
            reasoning="通过搜索适配器获取候选来源，并按项目内 URL 去重。",
        ))
        return SearchRun(query, source_ids, new_count, duplicate_count, log.id)
