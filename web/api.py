"""Dependency-free JSON API for the ResearchGraph demo."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import parse_qs

from agent.coordinator import ResearchCoordinator
from agent.traceability import TraceabilityService
from models.project import ResearchProject
from tools.llm import LLMClient
from tools.storage import Storage


def _json_default(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return value.__dict__
    if hasattr(value, "__slots__"):
        return {name: getattr(value, name) for name in value.__slots__}
    raise TypeError(f"Unsupported value: {type(value)!r}")


class ApiApplication:
    """Small WSGI application; no framework is required for the first demo."""

    def __init__(self, storage: Storage, llm_client: LLMClient | None = None):
        storage.initialize()
        self.storage = storage
        self.coordinator = ResearchCoordinator(storage, llm_client=llm_client)
        self.traceability = TraceabilityService(storage)

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]):
        try:
            body = self._dispatch(environ)
            status, payload = "200 OK", body
        except ValueError as error:
            status, payload = "404 Not Found", {"error": str(error)}
        except (KeyError, json.JSONDecodeError) as error:
            status, payload = "400 Bad Request", {"error": f"请求参数无效：{error}"}
        except Exception as error:  # Keep the demo API response JSON shaped.
            status, payload = "500 Internal Server Error", {"error": str(error)}
        encoded = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
        start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                                ("Content-Length", str(len(encoded)))])
        return [encoded]

    def _dispatch(self, environ: dict[str, Any]) -> dict[str, Any]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")
        if method == "POST" and path == "/api/projects":
            data = self._body(environ)
            project = self.coordinator.create_project(ResearchProject(
                None, data["title"], data["research_question"], data.get("time_range"),
                data.get("region"), data.get("subject"), data.get("focus"),
            ))
            return {"project": project}
        parts = [part for part in path.split("/") if part]
        if len(parts) < 3 or parts[0] != "api" or parts[1] != "projects":
            raise ValueError("接口不存在")
        project_id = int(parts[2])
        if method == "POST" and len(parts) == 4 and parts[3] == "questions":
            return {"question_ids": self.coordinator.decompose(project_id)}
        if method == "POST" and len(parts) == 5 and parts[3] == "questions" and parts[4] == "confirm":
            return {"confirmed": self.coordinator.confirm_questions(project_id)}
        if method == "POST" and len(parts) == 4 and parts[3] == "run":
            result = self.coordinator.run(project_id)
            return {"question_ids": result.question_ids, "evidence_ids": result.evidence_ids,
                    "claim_ids": result.claim_ids, "report": result.report}
        if method == "GET" and len(parts) == 4 and parts[3] == "report":
            reports = self.storage.list_reports(project_id)
            if not reports:
                raise ValueError("项目尚未生成报告")
            return {"report": reports[-1]}
        if method == "GET" and len(parts) == 4 and parts[3] == "questions":
            return {"questions": self.storage.list_questions(project_id)}
        if method == "GET" and len(parts) == 4 and parts[3] == "trace":
            claim_id = int((parse_qs(environ.get("QUERY_STRING", "")).get("claim_id") or [""])[0])
            return self.traceability.trace_claim(claim_id)
        raise ValueError("接口不存在")

    @staticmethod
    def _body(environ: dict[str, Any]) -> dict[str, Any]:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(length)
        return json.loads(raw.decode("utf-8"))


def create_app(storage: Storage, llm_client: LLMClient | None = None) -> ApiApplication:
    return ApiApplication(storage, llm_client)
