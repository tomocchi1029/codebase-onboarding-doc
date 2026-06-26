"""Tests for the generator module with mocked LLM."""

from unittest.mock import MagicMock, patch

from codebase_onboarding_doc.generator import OnboardingGenerator
from codebase_onboarding_doc.models import FindingType


def _mock_overview_response():
    return {
        "overview": "A test project with custom architecture.",
        "architecture_summary": "Modular design with separate components.",
        "key_files": ["src/main.py", "src/auth.py"],
    }


def _mock_finding_response():
    return {
        "title": "Why this exists",
        "explanation": "This was needed for backward compatibility.",
        "impact": "New developers should be aware of this constraint.",
        "warnings": ["Don't remove without checking dependencies"],
        "confidence": 0.85,
    }


def test_generate_with_mocked_llm(tmp_path):
    # Create a minimal git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

    # Create a source file with a TODO
    src = tmp_path / "src" / "main.py"
    src.parent.mkdir(parents=True)
    src.write_text("# TODO: Fix this later\nprint('hello')\n")
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(tmp_path), capture_output=True)

    mock_llm = MagicMock()
    mock_llm.chat_json.side_effect = [_mock_overview_response(), _mock_finding_response()]

    generator = OnboardingGenerator(llm_client=mock_llm)
    doc = generator.generate(
        repo_path=str(tmp_path),
        git_depth=10,
        max_sections=5,
    )

    assert doc.project_name != ""
    assert doc.total_findings >= 1
    assert len(doc.sections) >= 1
    assert mock_llm.chat_json.call_count >= 2  # overview + at least one finding


def test_generate_no_findings(tmp_path):
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

    # Create a clean source file with no patterns
    src = tmp_path / "src" / "main.py"
    src.parent.mkdir(parents=True)
    src.write_text("print('hello')\n")
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(tmp_path), capture_output=True)

    mock_llm = MagicMock()
    mock_llm.chat_json.return_value = _mock_overview_response()

    generator = OnboardingGenerator(llm_client=mock_llm)
    doc = generator.generate(repo_path=str(tmp_path), git_depth=10)

    assert doc.total_findings == 0
    assert len(doc.sections) == 0
    # Overview should still be generated
    assert mock_llm.chat_json.call_count >= 1
