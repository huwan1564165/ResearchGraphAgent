"""Rule-based and LLM-backed research question decomposition."""

from __future__ import annotations

import json

from models.project import ResearchProject
from models.question import ResearchQuestion
from tools.llm import LLMClient, parse_json_object


def suggest_questions(project: ResearchProject) -> list[ResearchQuestion]:
    """Create non-overlapping questions from the project's scope."""
    focus = project.focus or "主要研究结果"
    subject = project.subject or "研究对象"
    period = project.time_range or "指定时间范围"
    return [ResearchQuestion(
        id=None, project_id=project.id or 0,
        text=f"在{period}内，{subject}在{focus}方面的总体研究结果是什么？", position=1,
    ), ResearchQuestion(
        id=None, project_id=project.id or 0,
        text=f"哪些研究方法和实施条件可能影响{subject}的{focus}结果？", position=2,
    ), ResearchQuestion(
        id=None, project_id=project.id or 0,
        text=f"现有证据对{subject}在{focus}方面的长期影响、局限性和不确定性得出了什么结论？", position=3,
    )]


class LLMQuestionDecomposer:
    """Generate structured questions with an injected LLM provider."""

    def __init__(self, client: LLMClient):
        self.client = client

    def suggest_questions(self, project: ResearchProject) -> list[ResearchQuestion]:
        prompt = json.dumps({
            "title": project.title, "research_question": project.research_question,
            "time_range": project.time_range, "region": project.region,
            "subject": project.subject, "focus": project.focus,
        }, ensure_ascii=False)
        response = self.client.generate(
            "请把下面的研究项目拆成 3 个互不重复、可检索的子问题。"
            "只返回 JSON 字符串数组，不要 Markdown 或其他解释。\n" + prompt,
            system="你是严谨的研究问题设计助手。子问题必须具体、可验证，并覆盖结果、条件和局限性。",
        )
        values = parse_json_object(response)
        if not isinstance(values, list) or not values:
            raise ValueError("LLM 必须返回非空 JSON 数组")
        texts = [str(value).strip() for value in values if str(value).strip()]
        if len(texts) < 3 or len(set(texts)) != len(texts):
            raise ValueError("LLM 返回的子问题必须至少有 3 个且不能重复")
        return [ResearchQuestion(None, project.id or 0, text, position=index)
                for index, text in enumerate(texts[:5], start=1)]
