from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Evidence:
    id: Optional[int]
    project_id: int
    source_id: int
    question_id: Optional[int]
    excerpt: str
    locator: Optional[str] = None
    evidence_type: str = "other"
    stance: str = "context"
    strength: Optional[str] = None
    uncertainty: Optional[str] = None
    created_at: Optional[str] = None
