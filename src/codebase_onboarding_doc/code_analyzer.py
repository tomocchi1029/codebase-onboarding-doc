"""Code analysis to detect patterns, anomalies, TODOs, hacks, and architectural decisions."""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

from .models import CodeFinding, FindingType

logger = logging.getLogger(__name__)


# Patterns for detecting interesting code patterns
TODO_PATTERNS = [
    re.compile(r"#\s*TODO[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"#\s*FIXME[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"#\s*HACK[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"#\s*XXX[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"#\s*WORKAROUND[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"//\s*TODO[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"//\s*FIXME[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"//\s*HACK[:\s]*(.+)", re.IGNORECASE),
    re.compile(r"/\*\s*TODO[:\s]*(.+?)\*/", re.IGNORECASE | re.DOTALL),
    re.compile(r"<!--\s*TODO[:\s]*(.+?)-->", re.IGNORECASE | re.DOTALL),
]

HACK_PATTERNS = [
    re.compile(r"(?:sleep|delay|wait)\s*\(\s*\d+\s*\)", re.IGNORECASE),
    re.compile(r"#\s*type:\s*ignore", re.IGNORECASE),
    re.compile(r"//\s*@ts-ignore", re.IGNORECASE),
    re.compile(r"eslint-disable", re.IGNORECASE),
    re.compile(r"nosec|nolint|noqa", re.IGNORECASE),
    re.compile(r"pragma:\s*no\s*cover", re.IGNORECASE),
]

LEGACY_PATTERNS = [
    re.compile(r"deprecated", re.IGNORECASE),
    re.compile(r"legacy", re.IGNORECASE),
    re.compile(r"backward.?compat", re.IGNORECASE),
    re.compile(r"old.?(?:api|system|version|approach)", re.IGNORECASE),
    re.compile(r"migrat(?:e|ion)", re.IGNORECASE),
]

SECURITY_PATTERNS = [
    re.compile(r"security|auth|password|token|secret|crypto|encrypt|decrypt", re.IGNORECASE),
    re.compile(r"verify|validate|sanitize|escape|encode", re.IGNORECASE),
    re.compile(r"permission|privilege|access.?control|rbac|abac", re.IGNORECASE),
]


def find_source_files(root_dir: str, ignore_dirs: list[str] | None = None) -> list[str]:
    """Find source code files in the project."""
    if ignore_dirs is None:
        ignore_dirs = [".git", "node_modules", "vendor", ".venv", "__pycache__", "dist", "build"]

    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".h"}
    root = Path(root_dir)
    files: list[str] = []

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(ignored in str(p) for ignored in ignore_dirs):
            continue
        if p.suffix in extensions:
            files.append(str(p))

    return sorted(files)


def detect_todos(file_path: str) -> list[CodeFinding]:
    """Detect TODO/FIXME/HACK comments in a file."""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings: list[CodeFinding] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in TODO_PATTERNS:
            m = pattern.search(line)
            if m:
                comment_text = m.group(1).strip()[:200]
                finding_type = FindingType.WORKAROUND if "HACK" in line.upper() else FindingType.TECHNICAL_DEBT
                findings.append(
                    CodeFinding(
                        id=f"TODO-{file_path}-{i}",
                        finding_type=finding_type,
                        title=f"TODO in {Path(file_path).name}:{i}",
                        file_path=file_path,
                        line_start=i,
                        code_snippet=line.strip(),
                        description=comment_text,
                        tags=["todo", "debt"],
                    )
                )
                break

    return findings


def detect_hacks(file_path: str) -> list[CodeFinding]:
    """Detect hack patterns (sleeps, type ignores, lint suppressions, etc.)."""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings: list[CodeFinding] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in HACK_PATTERNS:
            if pattern.search(line):
                findings.append(
                    CodeFinding(
                        id=f"HACK-{file_path}-{i}",
                        finding_type=FindingType.WORKAROUND,
                        title=f"Potential hack in {Path(file_path).name}:{i}",
                        file_path=file_path,
                        line_start=i,
                        code_snippet=line.strip(),
                        description=f"Detected pattern: {pattern.pattern}",
                        tags=["hack", "workaround"],
                    )
                )
                break

    return findings


def detect_legacy(file_path: str) -> list[CodeFinding]:
    """Detect legacy code markers."""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings: list[CodeFinding] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in LEGACY_PATTERNS:
            if pattern.search(line):
                findings.append(
                    CodeFinding(
                        id=f"LEGACY-{file_path}-{i}",
                        finding_type=FindingType.LEGACY_CODE,
                        title=f"Legacy marker in {Path(file_path).name}:{i}",
                        file_path=file_path,
                        line_start=i,
                        code_snippet=line.strip(),
                        description=f"Legacy-related term detected: {pattern.pattern}",
                        tags=["legacy"],
                    )
                )
                break

    return findings


def detect_security_patterns(file_path: str) -> list[CodeFinding]:
    """Detect security-related code patterns."""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings: list[CodeFinding] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in SECURITY_PATTERNS:
            if pattern.search(line):
                # Only flag if it looks like a security-relevant line
                if any(kw in line.lower() for kw in ["check", "verify", "validate", "auth", "token", "password", "secret", "encrypt", "permission"]):
                    findings.append(
                        CodeFinding(
                            id=f"SEC-{file_path}-{i}",
                            finding_type=FindingType.SECURITY_CHANGE,
                            title=f"Security-related code in {Path(file_path).name}:{i}",
                            file_path=file_path,
                            line_start=i,
                            code_snippet=line.strip(),
                            description=f"Security pattern detected",
                            tags=["security"],
                        )
                    )
                    break

    return findings


def detect_anomalies(file_path: str) -> list[CodeFinding]:
    """Detect code anomalies (unusually long functions, deeply nested code, etc.)."""
    if not file_path.endswith(".py"):
        return []

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content)
    except Exception:
        return []

    findings: list[CodeFinding] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Detect very long functions
            if node.end_lineno and (node.end_lineno - node.lineno) > 100:
                findings.append(
                    CodeFinding(
                        id=f"LONG-{file_path}-{node.lineno}",
                        finding_type=FindingType.ANOMALY,
                        title=f"Long function '{node.name}' ({node.end_lineno - node.lineno} lines)",
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno,
                        code_snippet=f"def {node.name}(...):  # {node.end_lineno - node.lineno} lines",
                        description=f"Function '{node.name}' is {node.end_lineno - node.lineno} lines long",
                        tags=["anomaly", "long-function"],
                    )
                )

            # Detect deeply nested functions
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                    findings.append(
                        CodeFinding(
                            id=f"NESTED-{file_path}-{child.lineno}",
                            finding_type=FindingType.ANOMALY,
                            title=f"Nested function '{child.name}' inside '{node.name}'",
                            file_path=file_path,
                            line_start=child.lineno,
                            code_snippet=f"def {child.name}(...):  # nested inside {node.name}",
                            description=f"Nested function definition detected",
                            tags=["anomaly", "nested-function"],
                        )
                    )

    return findings


def analyze_codebase(
    root_dir: str,
    ignore_dirs: list[str] | None = None,
    detect_todos_flag: bool = True,
    detect_hacks_flag: bool = True,
    detect_legacy_flag: bool = True,
    detect_security_flag: bool = True,
    detect_anomalies_flag: bool = True,
    focus_dirs: list[str] | None = None,
) -> list[CodeFinding]:
    """Analyze the codebase and return all findings."""
    source_files = find_source_files(root_dir, ignore_dirs)

    # Filter by focus dirs if specified
    if focus_dirs:
        source_files = [
            f for f in source_files
            if any(fd in f for fd in focus_dirs)
        ]

    logger.info("Analyzing %d source files", len(source_files))

    all_findings: list[CodeFinding] = []

    for file_path in source_files:
        if detect_todos_flag:
            all_findings.extend(detect_todos(file_path))
        if detect_hacks_flag:
            all_findings.extend(detect_hacks(file_path))
        if detect_legacy_flag:
            all_findings.extend(detect_legacy(file_path))
        if detect_security_flag:
            all_findings.extend(detect_security_patterns(file_path))
        if detect_anomalies_flag:
            all_findings.extend(detect_anomalies(file_path))

    logger.info("Found %d total findings", len(all_findings))
    return all_findings
