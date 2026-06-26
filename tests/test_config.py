"""Tests for config module."""

import os
from unittest.mock import patch

import yaml

from codebase_onboarding_doc.config import Config, _deep_merge


def test_default_config():
    cfg = Config()
    assert cfg.git_depth == 500
    assert cfg.detect_todos is True
    assert cfg.max_sections == 20
    assert cfg.output_format == "markdown"


def test_config_from_file(tmp_path):
    config_data = {
        "llm": {"provider": "glm", "model": "glm-4.6"},
        "analysis": {"git_depth": 1000, "focus_dirs": ["src/"]},
        "output": {"format": "html", "max_sections": 10},
    }
    p = tmp_path / ".codoc.yml"
    p.write_text(yaml.dump(config_data))
    cfg = Config.from_file(str(p))
    assert cfg.git_depth == 1000
    assert cfg.focus_dirs == ["src/"]
    assert cfg.output_format == "html"
    assert cfg.max_sections == 10
    assert cfg.llm_config.provider == "glm"


def test_config_file_not_found():
    cfg = Config.from_file("nonexistent.yml")
    assert cfg.git_depth == 500


def test_config_from_env():
    with patch.dict(os.environ, {"CODOC_LLM_PROVIDER": "anthropic", "CODOC_LLM_MODEL": "claude-3"}):
        cfg = Config.from_env()
        assert cfg.llm_config.provider == "anthropic"
        assert cfg.llm_config.model == "claude-3"


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 10}, "e": 5}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 10, "d": 3}, "e": 5}
