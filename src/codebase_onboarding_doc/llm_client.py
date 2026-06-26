"""LLM client for codebase onboarding doc generation."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> LLMConfig:
        provider = os.environ.get("CODOC_LLM_PROVIDER", "openai")
        model = os.environ.get("CODOC_LLM_MODEL", "gpt-4o")
        api_key = os.environ.get("CODOC_LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        base_url = os.environ.get("CODOC_LLM_BASE_URL", "")
        if not base_url:
            default_urls = {
                "openai": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com/v1",
                "glm": "https://open.bigmodel.cn/api/paas/v4",
                "ollama": "http://localhost:11434/v1",
            }
            base_url = default_urls.get(provider, "")
        return cls(provider=provider, model=model, api_key=api_key, base_url=base_url)


class LLMClient:
    """HTTP client for LLM API calls."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()
        if not self.config.api_key and self.config.provider != "ollama":
            logger.warning("No API key configured.")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            if self.config.provider == "anthropic":
                headers["x-api-key"] = self.config.api_key
                headers["anthropic-version"] = "2023-06-01"
            else:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _build_payload(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if self.config.provider == "anthropic":
            system = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_messages = [m for m in messages if m["role"] != "system"]
            return {
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "system": system,
                "messages": user_messages,
            }
        return {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

    def _extract_content(self, response: dict[str, Any]) -> str:
        if self.config.provider == "anthropic":
            return response.get("content", [{}])[0].get("text", "")
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")

    def chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.config.base_url}/chat/completions"
        if self.config.provider == "anthropic":
            url = f"{self.config.base_url}/messages"
        payload = self._build_payload(messages)
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return self._extract_content(data)

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any] | list[Any]:
        content = self.chat(messages)
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        return json.loads(content)
