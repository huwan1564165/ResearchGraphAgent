from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ResearchProject:
    id: Optional[int]
    title: str
    research_question: str
    time_range: Optional[str] = None
    region: Optional[str] = None
    subject: Optional[str] = None
    focus: Optional[str] = None
    status: str = "draft"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
