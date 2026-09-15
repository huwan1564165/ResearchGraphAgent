from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Report:
    id: Optional[int]
    project_id: int
    version: int
    content: str
    created_at: Optional[str] = None
