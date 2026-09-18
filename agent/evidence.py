"""Deterministic evidence extraction and evidence-to-claim linking."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from models.evidence import Evidence
from models.research_log import ResearchLog
from models.source import Source
from tools.llm import parse_json_object
from tools.storage import Storage


@dataclass(slots=True)
class EvidenceDraft:
    excerpt: str
    locator: str
    evidence_type: str = "other"
    stance: str = "context"
    strength: str = "weak"
    uncertainty: str | None = None


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", text) if part.strip()]


class RuleBasedEvidenceExtractor:
    """Select relevant sentences without inventing or paraphrasing evidence."""

    def extract(self, source: Source, question: str, limit: int = 3) -> list[EvidenceDraft]:
        text = (source.content or source.abstract or "").strip()
        if not text or limit <= 0:
            return []
        sentences = _sentences(text)
        keywords = {word.lower() for word in re.findall(r"[\w\u4e00-\u9fff]{2,}", question.lower())}
        ranked = sorted(
            enumerate(sentences, start=1),
            key=lambda item: sum(keyword in item[1].lower() for keyword in keywords),
            reverse=True,
        )
        selected = ranked[:limit]
        drafts: list[EvidenceDraft] = []
        for number, sentence in selected:
            lowered = sentence.lower()
            if any(word in lowered for word in ("实验", "experiment", "survey", "调查")):
                evidence_type = "study_result"
            elif any(word in lowered for word in ("数据", "data", "%", "percent")):
                evidence_type = "data"
            else:
                evidence_type = "other"
            drafts.append(EvidenceDraft(
                excerpt=sentence,
                locator=f"摘要第 {number} 句",
                evidence_type=evidence_type,
                uncertainty="仅基于来源摘要或已保存文本，需结合原文核查。",
            ))
        return drafts


class LLMEvidenceExtractor:
    """Use an LLM to classify and select verbatim evidence from a source."""

    def __init__(self, client):
        self.client = client

    def extract(self, source: Source, question: str, limit: int = 3) -> list[EvidenceDraft]:
        text = (source.content or source.abstract or "").strip()
        if not text or limit <= 0:
            return []
        response = self.client.generate(
            json.dumps({"question": question, "source_text": text, "limit": limit}, ensure_ascii=False),
            system=("你是证据抽取助手。只从 source_text 原文中逐字选择证据，不得改写或编造。"
                    "只返回 JSON 数组，每项含 excerpt、locator、evidence_type、stance、strength、uncertainty。"),
        )
        values = parse_json_object(response)
        if not isinstance(values, list):
            raise ValueError("LLM 证据抽取必须返回 JSON 数组")
        drafts = []
        for value in values[:limit]:
            if not isinstance(value, dict) or not isinstance(value.get("excerpt"), str):
                continue
            excerpt = value["excerpt"].strip()
            if not excerpt or excerpt not in text:
                continue
            drafts.append(EvidenceDraft(
                excerpt=excerpt, locator=str(value.get("locator") or "原文"),
                evidence_type=str(value.get("evidence_type") or "other"),
                stance=str(value.get("stance") or "context"),
                strength=str(value.get("strength") or "weak"),
                uncertainty=str(value.get("uncertainty")) if value.get("uncertainty") else None,
            ))
        return drafts


class EvidenceService:
    def __init__(self, storage: Storage, extractor=None):
        self.storage = storage
        self.extractor = extractor or RuleBasedEvidenceExtractor()
        self.fallback_extractor = RuleBasedEvidenceExtractor()

    def extract_and_save(self, project_id: int, question_id: int, question: str,
                         source_ids: list[int], limit_per_source: int = 3) -> list[Evidence]:
        saved: list[Evidence] = []
        for source_id in source_ids:
            source = self.storage.get_source(source_id)
            if source is None or source.project_id != project_id:
                continue
            try:
                drafts = self.extractor.extract(source, question, limit_per_source)
            except Exception:
                drafts = []
            if not drafts and not isinstance(self.extractor, RuleBasedEvidenceExtractor):
                drafts = self.fallback_extractor.extract(source, question, limit_per_source)
            for draft in drafts:
                saved.append(self.storage.create_evidence(Evidence(
                    id=None, project_id=project_id, source_id=source_id,
                    question_id=question_id, excerpt=draft.excerpt,
                    locator=draft.locator, evidence_type=draft.evidence_type,
                    stance=draft.stance, strength=draft.strength,
                    uncertainty=draft.uncertainty,
                )))
        log = self.storage.create_log(ResearchLog(
            id=None, project_id=project_id, action="evidence_extraction",
            input_data=json.dumps({"question_id": question_id, "source_ids": source_ids}, ensure_ascii=False),
            output_data=json.dumps({"evidence_ids": [item.id for item in saved]}, ensure_ascii=False),
            reasoning="只保存来源中的原文句子，并记录其定位和不确定性。",
        ))
        return saved

    def attach_to_claim(self, claim_id: int, evidence_ids: list[int], relation: str = "supports") -> None:
        for evidence_id in evidence_ids:
            self.storage.link_claim_evidence(claim_id, evidence_id, relation)
