"""Rule-based synthesis of claims from traceable evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass

from models.research_log import ResearchLog
from tools.llm import parse_json_object
from tools.storage import Storage


@dataclass(slots=True)
class ClaimSynthesis:
    claim_id: int
    conclusion: str
    supporting_evidence_ids: list[int]
    opposing_evidence_ids: list[int]
    contextual_evidence_ids: list[int]
    confidence: float
    uncertainty: str


class SynthesisService:
    """Synthesize claims using an optional LLM while preserving traceability."""

    def __init__(self, storage: Storage, client=None):
        self.storage = storage
        self.client = client

    def _synthesize_with_llm(self, claim, links) -> ClaimSynthesis:
        response = self.client.generate(
            json.dumps({"claim": claim.text, "evidence": links}, ensure_ascii=False),
            system=("你是系统综述综合助手。基于给定证据谨慎综合，不得引入证据外事实。"
                    "只返回 JSON 对象：conclusion、supporting_evidence_ids、opposing_evidence_ids、"
                    "contextual_evidence_ids、confidence（0到1）、uncertainty。"),
        )
        data = parse_json_object(response)
        if not isinstance(data, dict):
            raise ValueError("LLM 综合必须返回 JSON 对象")
        valid = {item["evidence_id"] for item in links}
        def ids(name):
            return [int(item) for item in data.get(name, []) if str(item).isdigit() and int(item) in valid]
        supporting, opposing = ids("supporting_evidence_ids"), ids("opposing_evidence_ids")
        contextual = ids("contextual_evidence_ids")
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0))))
        result = ClaimSynthesis(claim.id, str(data.get("conclusion", "无法形成结论。")),
                                supporting, opposing, contextual, round(confidence, 2),
                                str(data.get("uncertainty", "需结合来源原文核查。")))
        self.storage.update_claim_confidence(claim.id, result.confidence)
        self.storage.create_log(ResearchLog(
            id=None, project_id=claim.project_id, action="claim_synthesis",
            input_data=json.dumps({"claim_id": claim.id, "evidence_ids": list(valid)}),
            output_data=json.dumps({"confidence": result.confidence, "supporting": supporting, "opposing": opposing}),
            reasoning="使用 LLM 基于已关联证据进行结构化综合，并校验引用 ID。",
        ))
        return result

    def synthesize_claim(self, claim_id: int) -> ClaimSynthesis:
        claim = self.storage.get_claim(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} does not exist")
        links = self.storage.list_claim_evidence(claim_id)
        if self.client is not None:
            return self._synthesize_with_llm(claim, links)
        supporting = [item["evidence_id"] for item in links if item["relation"] == "supports"]
        opposing = [item["evidence_id"] for item in links if item["relation"] in {"opposes", "contradicts"}]
        contextual = [item["evidence_id"] for item in links if item["evidence_id"] not in supporting + opposing]
        total = len(supporting) + len(opposing)
        confidence = 0.0 if total == 0 else round(len(supporting) / total, 2)
        if supporting and opposing:
            conclusion = f"现有证据对“{claim.text}”存在支持与相反信号，不能作出确定结论。"
        elif supporting:
            conclusion = f"现有证据总体支持“{claim.text}”，但仍需结合来源原文核查。"
        elif opposing:
            conclusion = f"现有证据总体不支持“{claim.text}”，但仍需结合来源原文核查。"
        else:
            conclusion = f"目前没有与“{claim.text}”建立支持或反对关系的证据。"
        uncertainty = "证据数量有限，且规则综合未评估研究设计质量。"
        result = ClaimSynthesis(claim_id, conclusion, supporting, opposing, contextual, confidence, uncertainty)
        self.storage.update_claim_confidence(claim_id, confidence)
        self.storage.create_log(ResearchLog(
            id=None, project_id=claim.project_id, action="claim_synthesis",
            input_data=json.dumps({"claim_id": claim_id, "evidence_ids": [item["evidence_id"] for item in links]}),
            output_data=json.dumps({"confidence": confidence, "supporting": supporting, "opposing": opposing}),
            reasoning="按证据关联关系和来源数量进行保守的规则式综合。",
        ))
        return result
