"""Configuration loader for Codebase Onboarding Doc."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from .llm_client import LLMConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "analysis": {
        "git_depth": 500,
        "focus_dirs": [],
        "ignore_dirs": ["vendor/", "node_modules/", ".venv/", "__pycache__/"],
        "detect_todos": True,
        "detect_hacks": True,
        "detect_legacy": True,
        "detect_security_changes": True,
    },
    "output": {
        "format": "markdown",
        "include_code_snippets": True,
        "include_commit_links": True,
        "max_sections": 20,
    },
}


class Config:
    """Configuration for Codebase Onboarding Doc."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or dict(DEFAULT_CONFIG)

    @property
    def llm_config(self) -> LLMConfig:
        llm_data = self._data.get("llm", {})
        return LLMConfig(
            provider=llm_data.get("provider", "openai"),
            model=llm_data.get("model", "gpt-4o"),
            api_key=llm_data.get("api_key", ""),
            base_url=llm_data.get("base_url", ""),
            temperature=llm_data.get("temperature", 0.3),
            max_tokens=llm_data.get("max_tokens", 4096),
        )

    @property
    def git_depth(self) -> int:
        return self._data.get("analysis", {}).get("git_depth", 500)

    @property
    def focus_dirs(self) -> list[str]:
        return self._data.get("analysis", {}).get("focus_dirs", [])

    @property
    def ignore_dirs(self) -> list[str]:
        return self._data.get("analysis", {}).get("ignore_dirs", [])

    @property
    def detect_todos(self) -> bool:
        return self._data.get("analysis", {}).get("detect_todos", True)

    @property
    def detect_hacks(self) -> bool:
        return self._data.get("analysis", {}).get("detect_hacks", True)

    @property
    def detect_legacy(self) -> bool:
        return self._data.get("analysis", {}).get("detect_legacy", True)

    @property
    def detect_security_changes(self) -> bool:
        return self._data.get("analysis", {}).get("detect_security_changes", True)

    @property
    def output_format(self) -> str:
        return self._data.get("output", {}).get("format", "markdown")

    @property
    def include_code_snippets(self) -> bool:
        return self._data.get("output", {}).get("include_code_snippets", True)

    @property
    def include_commit_links(self) -> bool:
        return self._data.get("output", {}).get("include_commit_links", True)

    @property
    def max_sections(self) -> int:
        return self._data.get("output", {}).get("max_sections", 20)

    @classmethod
    def from_file(cls, path: str) -> Config:
        p = Path(path)
        if not p.exists():
            logger.warning("Config file not found: %s, using defaults", path)
            return cls()
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        merged = _deep_merge(dict(DEFAULT_CONFIG), data)
        logger.info("Loaded config from %s", path)
        return cls(merged)

    @classmethod
    def from_env(cls) -> Config:
        data = dict(DEFAULT_CONFIG)
        llm_data = data.get("llm", {})
        if v := os.environ.get("CODOC_LLM_PROVIDER"):
            llm_data["provider"] = v
        if v := os.environ.get("CODOC_LLM_MODEL"):
            llm_data["model"] = v
        if v := os.environ.get("CODOC_LLM_API_KEY"):
            llm_data["api_key"] = v
        if v := os.environ.get("CODOC_LLM_BASE_URL"):
            llm_data["base_url"] = v
        data["llm"] = llm_data
        return cls(data)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
