"""SQLite persistence for the ResearchGraph domain objects."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TypeVar

from models.claim import Claim
from models.evidence import Evidence
from models.project import ResearchProject
from models.question import ResearchQuestion
from models.report import Report
from models.research_log import ResearchLog
from models.source import Source


T = TypeVar("T")


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    research_question TEXT NOT NULL,
    time_range TEXT,
    region TEXT,
    subject TEXT,
    focus TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    is_confirmed INTEGER NOT NULL DEFAULT 0 CHECK (is_confirmed IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    authors TEXT,
    institution TEXT,
    published_at TEXT,
    url TEXT NOT NULL,
    abstract TEXT,
    content TEXT,
    source_type TEXT NOT NULL DEFAULT 'web',
    authority_score REAL,
    relevance_score REAL,
    method_notes TEXT,
    conflict_of_interest TEXT,
    evaluation_reason TEXT,
    fetched_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, url)
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE SET NULL,
    excerpt TEXT NOT NULL,
    locator TEXT,
    evidence_type TEXT NOT NULL DEFAULT 'other',
    stance TEXT NOT NULL DEFAULT 'context',
    strength TEXT,
    uncertainty TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    claim_type TEXT NOT NULL DEFAULT 'synthesis',
    confidence REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relation TEXT NOT NULL DEFAULT 'supports',
    PRIMARY KEY (claim_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, version)
);

CREATE TABLE IF NOT EXISTS research_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    reasoning TEXT,
    created_at TEXT NOT NULL
);
"""


class Storage:
    """Small repository-style wrapper around SQLite.

    Connections are short lived and configured with foreign-key enforcement.
    This is sufficient for the local first version and keeps tests isolated.
    """

    app_name = "ResearchGraph"

    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(sources)")}
            if "content" not in columns:
                connection.execute("ALTER TABLE sources ADD COLUMN content TEXT")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _model(model_type: type[T], row: sqlite3.Row | None) -> T | None:
        if row is None:
            return None
        values = dict(row)
        if model_type is ResearchQuestion:
            values["is_confirmed"] = bool(values["is_confirmed"])
        return model_type(**values)

    def create_project(self, project: ResearchProject) -> ResearchProject:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO projects
                (title, research_question, time_range, region, subject, focus,
                 status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (project.title, project.research_question, project.time_range,
                 project.region, project.subject, project.focus, project.status,
                 now, now),
            )
            project_id = cursor.lastrowid
        return ResearchProject(id=project_id, created_at=now, updated_at=now, **{
            key: value for key, value in asdict(project).items()
            if key not in {"id", "created_at", "updated_at"}
        })

    def get_project(self, project_id: int) -> ResearchProject | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return self._model(ResearchProject, row)

    def create_question(self, question: ResearchQuestion) -> ResearchQuestion:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO questions
                (project_id, text, position, status, is_confirmed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (question.project_id, question.text, question.position, question.status,
                 int(question.is_confirmed), now, now),
            )
            question_id = cursor.lastrowid
        return ResearchQuestion(id=question_id, created_at=now, updated_at=now, **{
            key: value for key, value in asdict(question).items()
            if key not in {"id", "created_at", "updated_at"}
        })

    def list_questions(self, project_id: int) -> list[ResearchQuestion]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM questions WHERE project_id = ? ORDER BY position, id", (project_id,)
            ).fetchall()
        return [self._model(ResearchQuestion, row) for row in rows]

    def update_question(self, question_id: int, *, text: str | None = None,
                        position: int | None = None, status: str | None = None,
                        is_confirmed: bool | None = None) -> ResearchQuestion | None:
        """Update editable question fields and return the updated question."""
        changes, values = [], []
        for column, value in (("text", text), ("position", position),
                              ("status", status), ("is_confirmed", is_confirmed)):
            if value is not None:
                changes.append(f"{column} = ?")
                values.append(int(value) if column == "is_confirmed" else value)
        if not changes:
            return self._get_question(question_id)
        changes.append("updated_at = ?")
        values.extend([self._now(), question_id])
        with self._connection() as connection:
            connection.execute(f"UPDATE questions SET {', '.join(changes)} WHERE id = ?", values)
        return self._get_question(question_id)

    def _get_question(self, question_id: int) -> ResearchQuestion | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return self._model(ResearchQuestion, row)

    def delete_question(self, question_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return cursor.rowcount > 0

    def confirm_questions(self, project_id: int) -> int:
        """Confirm all current questions and move the project to confirmed state."""
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE questions SET is_confirmed = 1, status = 'confirmed', updated_at = ? WHERE project_id = ?",
                (now, project_id),
            )
            connection.execute("UPDATE projects SET status = 'questions_confirmed', updated_at = ? WHERE id = ?",
                               (now, project_id))
        return cursor.rowcount

    def create_source(self, source: Source) -> Source:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO sources
                (project_id, title, authors, institution, published_at, url, abstract, content,
                 source_type, authority_score, relevance_score, method_notes,
                 conflict_of_interest, evaluation_reason, fetched_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (source.project_id, source.title, source.authors, source.institution,
                 source.published_at, source.url, source.abstract, source.content, source.source_type,
                 source.authority_score, source.relevance_score, source.method_notes,
                 source.conflict_of_interest, source.evaluation_reason,
                 source.fetched_at, now),
            )
            source_id = cursor.lastrowid
        return Source(id=source_id, created_at=now, **{
            key: value for key, value in asdict(source).items()
            if key not in {"id", "created_at"}
        })

    def get_source_by_url(self, project_id: int, url: str) -> Source | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM sources WHERE project_id = ? AND url = ?", (project_id, url)
            ).fetchone()
        return self._model(Source, row)

    def get_source(self, source_id: int) -> Source | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return self._model(Source, row)

    def list_evidence(self, project_id: int, question_id: int | None = None) -> list[Evidence]:
        query = "SELECT * FROM evidence WHERE project_id = ?"
        params: list[int] = [project_id]
        if question_id is not None:
            query += " AND question_id = ?"
            params.append(question_id)
        query += " ORDER BY id"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._model(Evidence, row) for row in rows]

    def create_evidence(self, evidence: Evidence) -> Evidence:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO evidence
                (project_id, source_id, question_id, excerpt, locator, evidence_type,
                 stance, strength, uncertainty, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (evidence.project_id, evidence.source_id, evidence.question_id,
                 evidence.excerpt, evidence.locator, evidence.evidence_type,
                 evidence.stance, evidence.strength, evidence.uncertainty, now),
            )
            evidence_id = cursor.lastrowid
        return Evidence(id=evidence_id, created_at=now, **{
            key: value for key, value in asdict(evidence).items()
            if key not in {"id", "created_at"}
        })

    def create_claim(self, claim: Claim) -> Claim:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO claims (project_id, text, claim_type, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
                (claim.project_id, claim.text, claim.claim_type, claim.confidence, now),
            )
            claim_id = cursor.lastrowid
        return Claim(id=claim_id, created_at=now, **{
            key: value for key, value in asdict(claim).items()
            if key not in {"id", "created_at"}
        })

    def link_claim_evidence(self, claim_id: int, evidence_id: int, relation: str = "supports") -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO claim_evidence (claim_id, evidence_id, relation) VALUES (?, ?, ?)",
                (claim_id, evidence_id, relation),
            )

    def list_claim_evidence(self, claim_id: int) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT ce.claim_id, ce.evidence_id, ce.relation,
                          e.project_id, e.source_id, e.question_id, e.excerpt, e.locator,
                          e.evidence_type, e.stance, e.strength, e.uncertainty,
                          s.title AS source_title, s.url AS source_url
                   FROM claim_evidence ce
                   JOIN evidence e ON e.id = ce.evidence_id
                   JOIN sources s ON s.id = e.source_id
                   WHERE ce.claim_id = ? ORDER BY ce.evidence_id""",
                (claim_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_claim(self, claim_id: int) -> Claim | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        return self._model(Claim, row)

    def update_claim_confidence(self, claim_id: int, confidence: float) -> Claim | None:
        with self._connection() as connection:
            connection.execute("UPDATE claims SET confidence = ? WHERE id = ?", (confidence, claim_id))
        return self.get_claim(claim_id)

    def list_claims(self, project_id: int) -> list[Claim]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM claims WHERE project_id = ? ORDER BY id", (project_id,)).fetchall()
        return [self._model(Claim, row) for row in rows]

    def next_report_version(self, project_id: int) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COALESCE(MAX(version), 0) + 1 AS version FROM reports WHERE project_id = ?", (project_id,)).fetchone()
        return int(row["version"])

    def list_reports(self, project_id: int) -> list[Report]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM reports WHERE project_id = ? ORDER BY version", (project_id,)
            ).fetchall()
        return [self._model(Report, row) for row in rows]

    def create_report(self, report: Report) -> Report:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO reports (project_id, version, content, created_at) VALUES (?, ?, ?, ?)",
                (report.project_id, report.version, report.content, now),
            )
            report_id = cursor.lastrowid
        return Report(id=report_id, created_at=now, project_id=report.project_id,
                      version=report.version, content=report.content)

    def create_log(self, log: ResearchLog) -> ResearchLog:
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO research_logs
                (project_id, action, input_data, output_data, reasoning, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (log.project_id, log.action, log.input_data, log.output_data,
                 log.reasoning, now),
            )
            log_id = cursor.lastrowid
        return ResearchLog(id=log_id, created_at=now, **{
            key: value for key, value in asdict(log).items()
            if key not in {"id", "created_at"}
        })

    def list_logs(self, project_id: int) -> list[ResearchLog]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM research_logs WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [self._model(ResearchLog, row) for row in rows]

    def table_names(self) -> list[str]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [row["name"] for row in rows]
