"""Tests for code analyzer."""

import tempfile
from pathlib import Path

from codebase_onboarding_doc.code_analyzer import (
    analyze_codebase,
    detect_anomalies,
    detect_hacks,
    detect_legacy,
    detect_security_patterns,
    detect_todos,
    find_source_files,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_find_source_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "src" / "main.py", "print('hello')\n")
        _write(root / "src" / "utils.js", "console.log('hi')\n")
        _write(root / "node_modules" / "lib.js", "console.log('dep')\n")
        _write(root / "README.md", "# Project\n")

        files = find_source_files(str(root))
        assert len(files) == 2
        assert any("main.py" in f for f in files)
        assert any("utils.js" in f for f in files)
        assert not any("node_modules" in f for f in files)


def test_detect_todos():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        _write(path, "# TODO: Fix this later\n# FIXME: Broken\ndef foo(): pass\n")
        findings = detect_todos(str(path))
        assert len(findings) == 2
        assert findings[0].finding_type.value == "technical_debt"
        assert "Fix this later" in findings[0].description


def test_detect_todos_hack():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        _write(path, "# HACK: Temporary workaround\ndef foo(): pass\n")
        findings = detect_todos(str(path))
        assert len(findings) == 1
        assert findings[0].finding_type.value == "workaround"


def test_detect_hacks():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        _write(path, "import time\ntime.sleep(500)\n# type: ignore\n")
        findings = detect_hacks(str(path))
        assert len(findings) >= 2
        assert any("sleep" in f.description for f in findings)


def test_detect_legacy():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        _write(path, "# This is a deprecated legacy function\ndef old_api(): pass\n")
        findings = detect_legacy(str(path))
        assert len(findings) >= 1
        assert findings[0].finding_type.value == "legacy_code"


def test_detect_security():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        _write(path, "def verify_token(token): return True\npassword = 'secret'\n")
        findings = detect_security_patterns(str(path))
        assert len(findings) >= 1
        assert findings[0].finding_type.value == "security_change"


def test_detect_anomalies_long_function():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        content = "def very_long_function():\n" + "    x = 1\n" * 110
        _write(path, content)
        findings = detect_anomalies(str(path))
        assert len(findings) >= 1
        assert any("Long function" in f.title for f in findings)


def test_detect_anomalies_nested_function():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.py"
        _write(path, "def outer():\n    def inner():\n        pass\n    pass\n")
        findings = detect_anomalies(str(path))
        assert any("Nested" in f.title for f in findings)


def test_analyze_codebase():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "src" / "main.py", "# TODO: Fix this\ntime.sleep(100)\n")
        _write(root / "src" / "auth.py", "def verify_password(p): return True\n")

        findings = analyze_codebase(str(root))
        assert len(findings) >= 2
        types = {f.finding_type for f in findings}
        assert FindingType.TECHNICAL_DEBT in types or FindingType.WORKAROUND in types


# Import here to avoid circular import issues
from codebase_onboarding_doc.models import FindingType  # noqa: E402
