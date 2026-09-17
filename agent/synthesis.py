"""Rule-based synthesis of claims from traceable evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass

from models.research_log import ResearchLog
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
    """Produce a cautious, deterministic synthesis without inventing evidence."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def synthesize_claim(self, claim_id: int) -> ClaimSynthesis:
        claim = self.storage.get_claim(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} does not exist")
        links = self.storage.list_claim_evidence(claim_id)
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
