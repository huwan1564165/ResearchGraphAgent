from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Claim:
    id: Optional[int]
    project_id: int
    text: str
    claim_type: str = "synthesis"
    confidence: Optional[float] = None
    created_at: Optional[str] = None
