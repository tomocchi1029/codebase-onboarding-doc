"""CLI entry point for Codebase Onboarding Doc."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .formatters import generate_html, generate_json, generate_markdown
from .generator import OnboardingGenerator
from .llm_client import LLMClient, LLMConfig

console = Console()
logger = logging.getLogger("codebase_onboarding_doc")


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool) -> None:
    """Codebase Onboarding Doc - Generate 'Why' documentation for your codebase."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@cli.command()
@click.option("--repo", "-r", default=".", help="Path to the git repository")
@click.option("--output", "-o", default="docs/onboarding.md", help="Output file path")
@click.option("--format", "-f", "output_format", type=click.Choice(["markdown", "json", "html"]), default="markdown", help="Output format")
@click.option("--depth", "-d", default=500, type=int, help="Number of commits to analyze")
@click.option("--focus", multiple=True, help="Directories to focus on")
@click.option("--ignore", multiple=True, help="Directories to ignore")
@click.option("--max-sections", default=20, type=int, help="Maximum number of sections in the doc")
@click.option("--provider", envvar="CODOC_LLM_PROVIDER", default="openai", help="LLM provider")
@click.option("--model", envvar="CODOC_LLM_MODEL", default="gpt-4o", help="LLM model name")
@click.option("--api-key", envvar="CODOC_LLM_API_KEY", help="LLM API key")
@click.option("--base-url", envvar="CODOC_LLM_BASE_URL", help="LLM API base URL")
def generate(
    repo: str,
    output: str,
    output_format: str,
    depth: int,
    focus: tuple[str, ...],
    ignore: tuple[str, ...],
    max_sections: int,
    provider: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
) -> None:
    """Generate an onboarding document for a codebase."""
    repo_path = Path(repo).resolve()
    if not repo_path.exists():
        console.print(f"[red]Error: Repository path not found: {repo}[/red]")
        sys.exit(1)

    console.print(f"[bold blue]Analyzing codebase:[/bold blue] {repo_path}")

    # Configure LLM
    config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key or "",
        base_url=base_url or "",
    )
    llm = LLMClient(config)
    generator = OnboardingGenerator(llm)

    console.print("  Mining git history...")
    console.print("  Analyzing code patterns...")
    console.print("  Generating explanations via LLM...")

    try:
        doc = generator.generate(
            repo_path=str(repo_path),
            git_depth=depth,
            focus_dirs=list(focus) if focus else None,
            ignore_dirs=list(ignore) if ignore else None,
            max_sections=max_sections,
        )
    except Exception as e:
        console.print(f"[red]✗ Generation failed: {e}[/red]")
        logger.exception("Generation failed")
        sys.exit(1)

    # Generate output
    if output_format == "markdown":
        content = generate_markdown(doc)
    elif output_format == "json":
        content = generate_json(doc)
    else:
        content = generate_html(doc)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    console.print(f"\n[green]✓[/green] Onboarding doc written to {output}")
    console.print(f"  Project: {doc.project_name}")
    console.print(f"  Total findings: {doc.total_findings}")
    console.print(f"  Sections generated: {len(doc.sections)}")

    # Display section summary
    if doc.sections:
        table = Table(title="Generated Sections")
        table.add_column("Title", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("File", style="dim")
        table.add_column("Confidence", style="green")

        for s in doc.sections:
            table.add_row(
                s.title[:50],
                s.finding_type.value,
                s.file_path[:40] if s.file_path else "-",
                f"{s.confidence:.0%}" if s.confidence > 0 else "-",
            )
        console.print(table)


@cli.command()
@click.option("--repo", "-r", default=".", help="Path to the git repository")
@click.option("--focus", multiple=True, help="Directories to focus on")
@click.option("--ignore", multiple=True, help="Directories to ignore")
def scan(repo: str, focus: tuple[str, ...], ignore: tuple[str, ...]) -> None:
    """Scan codebase and display findings without generating docs."""
    from .code_analyzer import analyze_codebase

    findings = analyze_codebase(
        repo,
        ignore_dirs=list(ignore) if ignore else None,
        focus_dirs=list(focus) if focus else None,
    )

    table = Table(title=f"Code Findings ({len(findings)} total)")
    table.add_column("Type", style="yellow")
    table.add_column("Title", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Line", style="dim")
    table.add_column("Description", style="dim")

    for f in findings:
        table.add_row(
            f.finding_type.value,
            f.title[:50],
            f.file_path[:40],
            str(f.line_start or "-"),
            f.description[:60],
        )
    console.print(table)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
