from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ResearchQuestion:
    id: Optional[int]
    project_id: int
    text: str
    position: int = 0
    status: str = "draft"
    is_confirmed: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
