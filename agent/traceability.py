"""Services for navigating Claim -> Evidence -> Source relationships."""

from __future__ import annotations

from typing import Any

from tools.storage import Storage


class TraceabilityService:
    def __init__(self, storage: Storage):
        self.storage = storage

    def trace_claim(self, claim_id: int) -> dict[str, Any]:
        claim = self.storage.get_claim(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} does not exist")
        evidence_items = []
        for item in self.storage.list_claim_evidence(claim_id):
            source = self.storage.get_source(item["source_id"])
            evidence_items.append({
                "id": item["evidence_id"],
                "relation": item["relation"],
                "excerpt": item["excerpt"],
                "locator": item["locator"],
                "evidence_type": item["evidence_type"],
                "stance": item["stance"],
                "strength": item["strength"],
                "uncertainty": item["uncertainty"],
                "source": None if source is None else {
                    "id": source.id, "title": source.title, "url": source.url,
                },
            })
        return {
            "claim": {
                "id": claim.id, "project_id": claim.project_id,
                "text": claim.text, "claim_type": claim.claim_type,
                "confidence": claim.confidence,
            },
            "evidence": evidence_items,
        }
