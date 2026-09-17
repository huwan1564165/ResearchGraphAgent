"""Validation helpers for evidence citations embedded in reports."""

from __future__ import annotations

import re
from dataclasses import dataclass

from models.report import Report
from tools.storage import Storage


_CITATION_PATTERN = re.compile(r"\[E(\d+)\]")


@dataclass(frozen=True, slots=True)
class CitationValidation:
    valid: bool
    citation_ids: list[int]
    errors: list[str]


class CitationChecker:
    """Check that report evidence references exist in the report's project."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def validate_report(self, report: Report) -> CitationValidation:
        return self.validate_content(report.project_id, report.content)

    def validate_content(self, project_id: int, content: str) -> CitationValidation:
        citation_ids = list(dict.fromkeys(int(value) for value in _CITATION_PATTERN.findall(content)))
        evidence_by_id = {item.id: item for item in self.storage.list_evidence(project_id)}
        errors: list[str] = []
        for evidence_id in citation_ids:
            if evidence_id not in evidence_by_id:
                errors.append(f"证据引用 [E{evidence_id}] 不存在或不属于项目 {project_id}。")
        return CitationValidation(not errors, citation_ids, errors)
