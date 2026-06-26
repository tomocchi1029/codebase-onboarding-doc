"""Git history mining for commit messages, blame data, and PR context."""

from __future__ import annotations

import logging
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import CommitInfo

logger = logging.getLogger(__name__)


def run_git(args: list[str], repo_path: str = ".") -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    if result.returncode != 0:
        logger.debug("git %s failed: %s", " ".join(args), result.stderr)
        return ""
    return result.stdout


def get_commit_log(repo_path: str = ".", depth: int = 500) -> list[CommitInfo]:
    """Get commit log with files changed."""
    fmt = "%H%x1f%an%x1f%ad%x1f%s"
    output = run_git(
        ["log", f"--max-count={depth}", f"--format={fmt}", "--date=short"],
        repo_path,
    )
    commits: list[CommitInfo] = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        commit_hash, author, date, message = parts[0], parts[1], parts[2], parts[3]
        # Get files changed in this commit
        files_output = run_git(
            ["show", "--stat", "--format=", commit_hash],
            repo_path,
        )
        files = [
            f.strip().split("|")[0].strip()
            for f in files_output.strip().split("\n")
            if "|" in f and not f.startswith(" ")
        ]
        commits.append(
            CommitInfo(
                hash=commit_hash,
                author=author,
                date=date,
                message=message,
                files_changed=files,
            )
        )
    logger.info("Mined %d commits", len(commits))
    return commits


def get_blame_for_file(file_path: str, repo_path: str = ".") -> dict[int, CommitInfo]:
    """Get git blame data for a file."""
    output = run_git(
        ["blame", "--line-porcelain", file_path],
        repo_path,
    )
    blames: dict[int, CommitInfo] = {}
    current_commit = ""
    current_author = ""
    current_date = ""
    current_line = 0

    for line in output.split("\n"):
        if line.startswith("\t"):
            current_line += 1
            if current_commit:
                blames[current_line] = CommitInfo(
                    hash=current_commit,
                    author=current_author,
                    date=current_date,
                )
            current_commit = ""
            current_author = ""
            current_date = ""
        elif line.startswith("author "):
            current_author = line[7:]
        elif line.startswith("author-mail "):
            pass
        elif line.startswith("author-time "):
            pass
        elif line.startswith("committer-time "):
            pass
        elif line.startswith("summary "):
            pass
        else:
            # First line of blame entry: hash orig-line orig-file
            parts = line.split()
            if parts and len(parts) >= 2 and len(parts[0]) == 40:
                current_commit = parts[0]

    return blames


def get_file_history(file_path: str, repo_path: str = ".", max_commits: int = 20) -> list[CommitInfo]:
    """Get commit history for a specific file."""
    fmt = "%H%x1f%an%x1f%ad%x1f%s"
    output = run_git(
        ["log", f"--max-count={max_commits}", f"--format={fmt}", "--date=short", "--", file_path],
        repo_path,
    )
    commits: list[CommitInfo] = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        commits.append(
            CommitInfo(
                hash=parts[0],
                author=parts[1],
                date=parts[2],
                message=parts[3],
                files_changed=[file_path],
            )
        )
    return commits


def get_diff_for_commit(commit_hash: str, repo_path: str = ".") -> str:
    """Get the diff for a specific commit."""
    return run_git(["show", "--stat", "--patch", commit_hash], repo_path)


def search_commit_messages(pattern: str, repo_path: str = ".", depth: int = 1000) -> list[CommitInfo]:
    """Search commit messages for a pattern."""
    fmt = "%H%x1f%an%x1f%ad%x1f%s"
    output = run_git(
        ["log", f"--max-count={depth}", f"--format={fmt}", "--date=short",
         "--grep", pattern, "-i"],
        repo_path,
    )
    commits: list[CommitInfo] = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        commits.append(
            CommitInfo(
                hash=parts[0],
                author=parts[1],
                date=parts[2],
                message=parts[3],
            )
        )
    return commits


def get_project_name(repo_path: str = ".") -> str:
    """Get the project name from git remote or directory name."""
    remote = run_git(["config", "--get", "remote.origin.url"], repo_path)
    if remote:
        # Extract repo name from URL
        name = remote.strip().split("/")[-1].replace(".git", "")
        if name:
            return name
    return Path(repo_path).resolve().name
