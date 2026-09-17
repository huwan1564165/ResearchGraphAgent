"""Application-level orchestration for the offline first-version research flow."""

from __future__ import annotations

from dataclasses import dataclass

from agent.decomposition import suggest_questions
from agent.evidence import EvidenceService
from agent.reporting import ReportService
from agent.researcher import Researcher, SearchRun
from models.claim import Claim
from models.project import ResearchProject
from models.report import Report
from tools.search import DemoSearchProvider, SearchProvider
from tools.storage import Storage


@dataclass(slots=True)
class ResearchRunResult:
    question_ids: list[int]
    search_runs: list[SearchRun]
    evidence_ids: list[int]
    claim_ids: list[int]
    report: Report


class ResearchCoordinator:
    """Coordinate storage-backed stages without hiding individual services."""

    def __init__(self, storage: Storage, provider: SearchProvider | None = None):
        self.storage = storage
        self.researcher = Researcher(storage, provider or DemoSearchProvider())
        self.evidence = EvidenceService(storage)
        self.reporting = ReportService(storage)

    def create_project(self, project: ResearchProject) -> ResearchProject:
        return self.storage.create_project(project)

    def decompose(self, project_id: int) -> list[int]:
        project = self.storage.get_project(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} does not exist")
        questions = [self.storage.create_question(item) for item in suggest_questions(project)]
        return [item.id for item in questions]

    def confirm_questions(self, project_id: int) -> int:
        return self.storage.confirm_questions(project_id)

    def search(self, project_id: int, *, limit: int = 5) -> list[SearchRun]:
        questions = self.storage.list_questions(project_id)
        return [self.researcher.search_and_save(project_id, question.text, question.id, limit)
                for question in questions if question.is_confirmed]

    def extract_evidence(self, project_id: int, runs: list[SearchRun]) -> list[int]:
        evidence_ids: list[int] = []
        for run, question in zip(runs, [q for q in self.storage.list_questions(project_id) if q.is_confirmed]):
            evidence_ids.extend(item.id for item in self.evidence.extract_and_save(
                project_id, question.id, question.text, run.source_ids
            ))
        return evidence_ids

    def create_claims(self, project_id: int) -> list[int]:
        claim_ids: list[int] = []
        for question in self.storage.list_questions(project_id):
            evidence = self.storage.list_evidence(project_id, question.id)
            if not evidence:
                continue
            claim = self.storage.create_claim(Claim(
                None, project_id, f"关于“{question.text}”的现有证据综合判断",
            ))
            for item in evidence:
                self.storage.link_claim_evidence(claim.id, item.id, item.stance)
            claim_ids.append(claim.id)
        return claim_ids

    def run(self, project_id: int, *, search_limit: int = 5) -> ResearchRunResult:
        question_ids = [q.id for q in self.storage.list_questions(project_id)]
        runs = self.search(project_id, limit=search_limit)
        evidence_ids = self.extract_evidence(project_id, runs)
        claim_ids = self.create_claims(project_id)
        report = self.reporting.generate(project_id)
        return ResearchRunResult(question_ids, runs, evidence_ids, claim_ids, report)
