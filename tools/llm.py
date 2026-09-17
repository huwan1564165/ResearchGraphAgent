"""LLM provider interfaces and an OpenAI-compatible HTTP client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.request import Request, urlopen


class LLMClient(Protocol):
    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Generate text for a prompt."""


@dataclass(slots=True)
class OpenAIClient:
    """Small dependency-free client for OpenAI Chat Completions.

    The endpoint is configurable so OpenAI-compatible gateways can be used
    without changing the agent code. The API key is never written to logs.
    """

    api_key: str
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 60.0

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        request = Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json", "User-Agent": "ResearchGraph/0.1"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("OpenAI 返回中缺少 choices.message.content") from error
        if not isinstance(content, str):
            raise RuntimeError("OpenAI 返回的 content 不是文本")
        return content


def parse_json_object(text: str) -> Any:
    """Parse a JSON object or array, allowing markdown fences and surrounding prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        starts = [(cleaned.find("{"), cleaned.rfind("}")),
                  (cleaned.find("["), cleaned.rfind("]"))]
        candidates = [(start, end) for start, end in starts if start >= 0 and end > start]
        if candidates:
            start, end = min(candidates, key=lambda item: item[0])
            return json.loads(cleaned[start:end + 1])
        raise
