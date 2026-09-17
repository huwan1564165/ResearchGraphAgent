"""Traceable Markdown report generation."""

from __future__ import annotations

import json

from agent.synthesis import SynthesisService
from models.report import Report
from models.research_log import ResearchLog
from tools.storage import Storage


class ReportService:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.synthesis = SynthesisService(storage)

    def generate(self, project_id: int) -> Report:
        project = self.storage.get_project(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} does not exist")
        questions = self.storage.list_questions(project_id)
        claims = self.storage.list_claims(project_id)
        sections = [f"# {project.title}", "", "## 1. 研究问题", "", project.research_question,
                    "", "## 2. 研究范围", "",
                    f"- 时间范围：{project.time_range or '未指定'}",
                    f"- 地区：{project.region or '未指定'}",
                    f"- 研究对象：{project.subject or '未指定'}",
                    f"- 关注重点：{project.focus or '未指定'}", "",
                    "## 3. 子问题", ""]
        sections.extend(f"{question.position}. {question.text}" for question in questions)
        sections.extend(["", "## 4. 主要结论", ""])
        if not claims:
            sections.extend(["> ⚠️ 当前项目没有已保存的 Claim，无法形成结论。", ""])
        syntheses = []
        for claim in claims:
            synthesis = self.synthesis.synthesize_claim(claim.id)
            syntheses.append(synthesis)
            sections.extend([f"### {claim.text}", "", synthesis.conclusion,
                             f"- 置信度：{synthesis.confidence:.2f}",
                             f"- 支持证据：{', '.join(f'[E{item}]' for item in synthesis.supporting_evidence_ids) or '无'}",
                             f"- 反对证据：{', '.join(f'[E{item}]' for item in synthesis.opposing_evidence_ids) or '无'}",
                             f"- 不确定性：{synthesis.uncertainty}", ""])
            trace = self.storage.list_claim_evidence(claim.id)
            if trace:
                sections.extend(["证据明细：", ""])
                for item in trace:
                    locator = f"（{item['locator']}）" if item["locator"] else ""
                    sections.append(
                        f"- [E{item['evidence_id']}] {item['source_title']}："
                        f"{item['excerpt']}{locator} [来源]({item['source_url']})"
                    )
                sections.append("")
        sections.extend(["## 5. 证据与局限性", "", "本报告仅使用已保存并关联的证据；规则式综合不替代对原始研究的质量评估。", ""])
        all_sources = {item.source_id: self.storage.get_source(item.source_id)
                       for item in self.storage.list_evidence(project_id)}
        sections.extend(["## 6. 来源列表", ""])
        if not all_sources:
            sections.append("暂无已保存来源。")
        else:
            for source_id, source in all_sources.items():
                if source is not None:
                    sections.append(f"- [S{source_id}] [{source.title}]({source.url})")
        sections.append("")
        version = self.storage.next_report_version(project_id)
        report = self.storage.create_report(Report(None, project_id, version, "\n".join(sections)))
        self.storage.create_log(ResearchLog(
            id=None, project_id=project_id, action="report_generation",
            input_data=json.dumps({"claim_ids": [claim.id for claim in claims]}),
            output_data=json.dumps({"report_id": report.id, "version": version}),
            reasoning="汇总项目、子问题和可追溯 Claim 综合结果，生成 Markdown 报告。",
        ))
        return report
