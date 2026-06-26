"""Core onboarding document generation logic using LLM reasoning."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from .code_analyzer import analyze_codebase
from .git_miner import get_commit_log, get_file_history, get_project_name
from .llm_client import LLMClient
from .models import CodeFinding, FindingType, OnboardingDoc, OnboardingSection

logger = logging.getLogger(__name__)

OVERVIEW_SYSTEM_PROMPT = """\
You are an expert software architect creating an onboarding guide for new developers.
Your job is to analyze a codebase's structure, history, and patterns to explain
WHY the code is the way it is — not just what it does.

Focus on:
1. Architectural decisions and their rationale
2. Workarounds and technical debt (and why they exist)
3. Legacy code and migration history
4. Security decisions and their context
5. Things new developers should be careful about

Be specific and practical. New developers should be able to read this and understand
the codebase's "story" — not just its structure.

Respond in valid JSON only, no markdown formatting."""

FINDING_SYSTEM_PROMPT = """\
You are an expert software engineer explaining code decisions to new team members.
For each code finding, explain WHY it exists, not just what it does.

Use the commit history and code context to provide a meaningful explanation.
If the commit history doesn't fully explain the finding, use your understanding
of common software engineering patterns to infer the likely reason.

Respond in valid JSON only, no markdown formatting."""

OVERVIEW_PROMPT = """\
## Project: {project_name}

## Commit History Summary ({commit_count} recent commits)

{commit_summary}

## Code Findings ({finding_count} total)

{findings_summary}

## Instructions

Generate an onboarding overview for this project. Include:
1. A high-level overview of what the project is and its architecture
2. A summary of key architectural decisions visible in the code
3. Notable patterns, workarounds, or technical debt
4. The "story" of this codebase based on its history

## Response Format

```json
{{
  "overview": "2-3 paragraph overview of the project",
  "architecture_summary": "Description of the architecture and key decisions",
  "key_files": ["src/main.py", "src/auth.py", ...]
}}
```"""

FINDING_PROMPT = """\
## Code Finding

{finding_json}

## Related Commit History

{commit_history}

## Instructions

Explain WHY this code pattern exists. Consider:
1. What problem was this trying to solve?
2. Why was this approach chosen over alternatives?
3. What is the history behind it (based on commits)?
4. What should new developers know about this?
5. Are there any risks or things to watch out for?

## Response Format

```json
{{
  "title": "Short descriptive title",
  "explanation": "2-3 paragraph explanation of WHY this exists",
  "impact": "What this means for new developers working with this code",
  "warnings": ["Warning 1", "Warning 2"],
  "confidence": 0.85
}}
```"""


class OnboardingGenerator:
    """Generates onboarding documentation from codebase analysis."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def _format_commit_summary(self, commits: list[Any], max_commits: int = 30) -> str:
        """Format commit log for LLM context."""
        lines = []
        for c in commits[:max_commits]:
            files = ", ".join(c.files_changed[:5]) if c.files_changed else ""
            lines.append(f"- [{c.date}] {c.message} (by {c.author})" + (f" — {files}" if files else ""))
        return "\n".join(lines)

    def _format_findings_summary(self, findings: list[CodeFinding], max_findings: int = 50) -> str:
        """Format findings for LLM context."""
        lines = []
        for f in findings[:max_findings]:
            line = f"- [{f.finding_type.value}] {f.title} ({f.file_path}"
            if f.line_start:
                line += f":{f.line_start}"
            line += f") — {f.description[:100]}"
            lines.append(line)
        return "\n".join(lines)

    def _format_finding_detail(self, finding: CodeFinding) -> str:
        """Format a single finding with full detail for LLM."""
        entry: dict[str, Any] = {
            "type": finding.finding_type.value,
            "title": finding.title,
            "file": finding.file_path,
            "description": finding.description,
        }
        if finding.line_start:
            entry["line"] = f"{finding.line_start}-{finding.line_end or finding.line_start}"
        if finding.code_snippet:
            entry["code"] = finding.code_snippet[:500]
        if finding.tags:
            entry["tags"] = finding.tags
        return json.dumps(entry, indent=2, ensure_ascii=False)

    def _format_commit_history(self, commits: list[Any], max_commits: int = 10) -> str:
        """Format commit history for a specific finding."""
        if not commits:
            return "No specific commit history found for this file."
        lines = []
        for c in commits[:max_commits]:
            lines.append(f"- [{c.date}] {c.message} (by {c.author}, {c.hash[:8]})")
        return "\n".join(lines)

    def _parse_finding_response(
        self, response: dict[str, Any], finding: CodeFinding
    ) -> OnboardingSection:
        """Parse LLM response for a single finding."""
        return OnboardingSection(
            title=response.get("title", finding.title),
            finding_type=finding.finding_type,
            explanation=response.get("explanation", ""),
            code_snippet=finding.code_snippet,
            file_path=finding.file_path,
            commit_history="",
            impact=response.get("impact", ""),
            warnings=response.get("warnings", []),
            confidence=float(response.get("confidence", 0.5)),
        )

    def generate(
        self,
        repo_path: str = ".",
        git_depth: int = 500,
        focus_dirs: list[str] | None = None,
        ignore_dirs: list[str] | None = None,
        max_sections: int = 20,
    ) -> OnboardingDoc:
        """Generate a complete onboarding document."""
        project_name = get_project_name(repo_path)
        logger.info("Generating onboarding doc for: %s", project_name)

        # Mine git history
        commits = get_commit_log(repo_path, depth=git_depth)
        logger.info("Mined %d commits", len(commits))

        # Analyze code
        findings = analyze_codebase(
            repo_path,
            ignore_dirs=ignore_dirs,
            focus_dirs=focus_dirs,
        )
        logger.info("Found %d code findings", len(findings))

        if not findings:
            logger.warning("No findings detected. Generating minimal doc.")

        # Generate overview
        overview_prompt = OVERVIEW_PROMPT.format(
            project_name=project_name,
            commit_count=len(commits),
            commit_summary=self._format_commit_summary(commits),
            finding_count=len(findings),
            findings_summary=self._format_findings_summary(findings),
        )

        messages = [
            {"role": "system", "content": OVERVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": overview_prompt},
        ]

        logger.info("Generating project overview via LLM...")
        try:
            overview_response = self.llm.chat_json(messages)
        except Exception as e:
            logger.error("Failed to generate overview: %s", e)
            overview_response = {
                "overview": "Failed to generate overview.",
                "architecture_summary": "",
                "key_files": [],
            }

        # Generate explanations for top findings
        sections: list[OnboardingSection] = []
        findings_to_explain = findings[:max_sections]

        for i, finding in enumerate(findings_to_explain):
            logger.info("Explaining finding %d/%d: %s", i + 1, len(findings_to_explain), finding.title)

            # Get file-specific commit history
            file_commits = get_file_history(finding.file_path, repo_path, max_commits=10)

            finding_prompt = FINDING_PROMPT.format(
                finding_json=self._format_finding_detail(finding),
                commit_history=self._format_commit_history(file_commits),
            )

            messages = [
                {"role": "system", "content": FINDING_SYSTEM_PROMPT},
                {"role": "user", "content": finding_prompt},
            ]

            try:
                response = self.llm.chat_json(messages)
                section = self._parse_finding_response(response, finding)
                section.commit_history = self._format_commit_history(file_commits)
                sections.append(section)
            except Exception as e:
                logger.error("Failed to explain finding %s: %s", finding.id, e)
                # Add a basic section without LLM explanation
                sections.append(
                    OnboardingSection(
                        title=finding.title,
                        finding_type=finding.finding_type,
                        explanation=finding.description,
                        code_snippet=finding.code_snippet,
                        file_path=finding.file_path,
                        impact="Unable to generate detailed explanation.",
                        confidence=0.0,
                    )
                )

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return OnboardingDoc(
            project_name=project_name,
            overview=overview_response.get("overview", ""),
            architecture_summary=overview_response.get("architecture_summary", ""),
            sections=sections,
            key_files=overview_response.get("key_files", []),
            generated_at=now,
            total_findings=len(findings),
        )
