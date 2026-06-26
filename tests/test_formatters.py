"""Tests for formatters."""

from codebase_onboarding_doc.models import (
    FindingType,
    OnboardingDoc,
    OnboardingSection,
)
from codebase_onboarding_doc.formatters import generate_html, generate_json, generate_markdown


def _sample_doc() -> OnboardingDoc:
    return OnboardingDoc(
        project_name="my-project",
        overview="A Django REST API with React frontend.",
        architecture_summary="Modular architecture with separate apps.",
        sections=[
            OnboardingSection(
                title="Why custom auth instead of Django auth",
                finding_type=FindingType.ARCHITECTURAL_DECISION,
                explanation="Custom tokens were needed for mobile app support.",
                code_snippet="def create_token(user): ...",
                file_path="auth/tokens.py",
                impact="Affects all authentication flows.",
                warnings=["Don't remove without checking mobile clients"],
                confidence=0.9,
            ),
            OnboardingSection(
                title="500ms sleep in rate limiter",
                finding_type=FindingType.WORKAROUND,
                explanation="Temporary workaround for Redis race condition.",
                code_snippet="time.sleep(0.5)",
                file_path="api/rate_limiter.py",
                impact="Directly affects API latency.",
                warnings=["Known performance bottleneck", "See issue #234"],
                confidence=0.8,
            ),
        ],
        key_files=["src/main.py", "auth/tokens.py", "api/rate_limiter.py"],
        generated_at="2025-01-01 00:00 UTC",
        total_findings=15,
    )


def test_generate_markdown():
    doc = _sample_doc()
    md = generate_markdown(doc)
    assert "Onboarding Guide: my-project" in md
    assert "Django REST API" in md
    assert "Why custom auth" in md
    assert "500ms sleep" in md
    assert "Warnings" in md
    assert "auth/tokens.py" in md
    assert "Key Files" in md


def test_generate_json():
    doc = _sample_doc()
    j = generate_json(doc)
    assert '"my-project"' in j
    assert '"architectural_decision"' in j
    assert '"workaround"' in j
    assert "0.9" in j


def test_generate_html():
    doc = _sample_doc()
    html = generate_html(doc)
    assert "<!DOCTYPE html>" in html
    assert "my-project" in html
    assert "Django REST API" in html
    assert "auth/tokens.py" in html
    assert "warnings" in html


def test_empty_doc_markdown():
    doc = OnboardingDoc(
        project_name="empty-project",
        total_findings=0,
    )
    md = generate_markdown(doc)
    assert "Onboarding Guide: empty-project" in md
