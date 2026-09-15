from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ResearchLog:
    id: Optional[int]
    project_id: int
    action: str
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    reasoning: Optional[str] = None
    created_at: Optional[str] = None
