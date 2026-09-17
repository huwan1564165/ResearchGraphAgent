from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Source:
    id: Optional[int]
    project_id: int
    title: str
    authors: Optional[str] = None
    institution: Optional[str] = None
    published_at: Optional[str] = None
    url: str = ""
    abstract: Optional[str] = None
    content: Optional[str] = None
    source_type: str = "web"
    authority_score: Optional[float] = None
    relevance_score: Optional[float] = None
    method_notes: Optional[str] = None
    conflict_of_interest: Optional[str] = None
    evaluation_reason: Optional[str] = None
    fetched_at: Optional[str] = None
    created_at: Optional[str] = None
