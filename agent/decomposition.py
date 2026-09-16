"""First-pass research question decomposition.

The rule-based implementation is deterministic for demos and tests. A later
LLM implementation can replace the strategy without changing its return shape.
"""

from __future__ import annotations

from models.project import ResearchProject
from models.question import ResearchQuestion


def suggest_questions(project: ResearchProject) -> list[ResearchQuestion]:
    """Create non-overlapping questions from the project's scope."""
    focus = project.focus or "主要研究结果"
    subject = project.subject or "研究对象"
    period = project.time_range or "指定时间范围"
    topics = ["总体效果", "作用机制与实施条件", "局限性与长期影响"]
    return [ResearchQuestion(
        id=None, project_id=project.id or 0,
        text=f"在{period}内，{subject}在{focus}方面的总体研究结果是什么？",
        position=1,
    ), ResearchQuestion(
        id=None, project_id=project.id or 0,
        text=f"哪些研究方法和实施条件可能影响{subject}的{focus}结果？",
        position=2,
    ), ResearchQuestion(
        id=None, project_id=project.id or 0,
        text=f"现有证据对{subject}在{focus}方面的长期影响、局限性和不确定性得出了什么结论？",
        position=3,
    )]
