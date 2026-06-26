"""Tests for models."""

from codebase_onboarding_doc.models import (
    CodeFinding,
    CommitInfo,
    FindingType,
    OnboardingDoc,
    OnboardingSection,
)


def test_commit_info_defaults():
    c = CommitInfo(hash="abc123")
    assert c.author == ""
    assert c.files_changed == []


def test_code_finding_defaults():
    f = CodeFinding(
        id="TEST-001",
        finding_type=FindingType.WORKAROUND,
        title="Test finding",
        file_path="src/main.py",
    )
    assert f.line_start is None
    assert f.tags == []
    assert f.code_snippet == ""


def test_code_finding_all_fields():
    f = CodeFinding(
        id="TEST-002",
        finding_type=FindingType.SECURITY_CHANGE,
        title="Security check removed",
        file_path="auth/login.py",
        line_start=42,
        line_end=50,
        code_snippet="if not verified: return",
        description="Security check was removed in commit abc",
        tags=["security", "auth"],
    )
    assert f.finding_type == FindingType.SECURITY_CHANGE
    assert f.line_start == 42


def test_onboarding_section():
    s = OnboardingSection(
        title="Why custom auth",
        finding_type=FindingType.ARCHITECTURAL_DECISION,
        explanation="Custom auth was needed for mobile support",
        file_path="auth/login.py",
        impact="Affects all auth-related code",
        warnings=["Don't remove without checking mobile clients"],
        confidence=0.9,
    )
    assert s.confidence == 0.9
    assert len(s.warnings) == 1


def test_onboarding_doc():
    doc = OnboardingDoc(
        project_name="my-project",
        overview="A Django REST API",
        architecture_summary="Modular architecture",
        sections=[
            OnboardingSection(
                title="Section 1",
                finding_type=FindingType.WORKAROUND,
                explanation="Explanation",
            ),
        ],
        key_files=["src/main.py", "src/auth.py"],
        total_findings=10,
    )
    assert doc.project_name == "my-project"
    assert len(doc.sections) == 1
    assert len(doc.key_files) == 2
