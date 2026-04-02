"""Click CLI for the Due Diligence Engine.

Commands:
  analyze     - Run due diligence on a project directory or zip
  prompt      - Generate AI evaluation prompt for IDE terminals
  report      - Generate report from a previous analysis
  purge       - Securely delete analysis data
  leaderboard - Show scoring leaderboard across analyses
  serve       - Start the SaaS API server
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.config import Config, get_config

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="dde")
def cli() -> None:
    """Due Diligence Engine - AI startup technical due diligence."""
    pass


@cli.command()
@click.argument("target")
@click.option("--name", "-n", default=None, help="Project name (auto-detected from URL/path if omitted)")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output directory")
@click.option("--skip-git", is_flag=True, help="Skip git forensics analysis")
@click.option("--skip-ai", is_flag=True, help="Skip AI-enhanced analysis (local only)")
@click.option("--format", "-f", "formats", multiple=True, default=["md", "html"],
              type=click.Choice(["md", "html"]), help="Output formats")
def analyze(
    target: str,
    name: str | None,
    output: str | None,
    skip_git: bool,
    skip_ai: bool,
    formats: tuple[str, ...],
) -> None:
    """Run technical due diligence on a project.

    TARGET can be:

    \b
      GitHub URL:  https://github.com/owner/repo
      Short form:  owner/repo
      Local path:  /path/to/project
      Zip archive: /path/to/project.zip

    \b
    Examples:
      dde analyze https://github.com/langchain-ai/langchain
      dde analyze openai/whisper
      dde analyze ./my-startup-code
      dde analyze startup.zip
    """
    from src.analyze.engine import AnalysisEngine
    from src.ingest.secure_loader import SecureLoader
    from src.report.generator import ReportGenerator
    from src.report.slides import SlideGenerator

    config = get_config()

    if skip_ai:
        config.anthropic_api_key = ""

    errors = config.validate()
    if errors and not skip_ai:
        console.print(
            Panel(
                "\n".join(f"[red]- {e}[/red]" for e in errors),
                title="Configuration Errors",
                border_style="red",
            )
        )
        console.print("[yellow]Tip: Set ANTHROPIC_API_KEY or use --skip-ai[/yellow]")
        sys.exit(1)

    config.ensure_dirs()

    output_dir = Path(output) if output else config.output_dir

    # Detect target type: URL or local path
    is_url = _is_github_url(target)

    # Auto-detect project name
    if name is None:
        name = _extract_project_name(target)

    loader = SecureLoader(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Ingest
        task = progress.add_task("Ingesting project data...", total=None)

        try:
            if is_url:
                progress.update(task, description=f"Cloning {target} ...")
                loader.load_from_url(target)
                repo_path = loader.cloned_repo_path
            else:
                source = Path(target)
                if not source.exists():
                    console.print(f"[red]Path not found: {target}[/red]")
                    console.print("[yellow]Tip: Did you mean a GitHub URL? Try: dde analyze owner/repo[/yellow]")
                    sys.exit(1)
                if source.suffix == ".zip":
                    loader.load_archive(source)
                    repo_path = None
                else:
                    loader.load_directory(source)
                    repo_path = source if source.is_dir() else None
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            console.print(f"[red]Ingestion error: {e}[/red]")
            sys.exit(1)

        progress.update(task, description=f"Ingested {len(loader.manifest)} files")

        # Analyze
        progress.update(task, description="Running analysis...")
        engine = AnalysisEngine(config, loader)
        result = engine.run(
            project_name=name,
            repo_path=repo_path,
            skip_git=skip_git,
        )
        progress.update(task, description="Analysis complete")

        # Generate reports
        progress.update(task, description="Generating reports...")
        report_gen = ReportGenerator()
        saved = report_gen.save_report(result, output_dir, formats=list(formats))

        # Generate slides
        slide_gen = SlideGenerator()
        safe_name = name.replace("/", "_").replace("\\", "_")
        slide_path = output_dir / f"dde_slides_{safe_name}_{result.analysis_id}.html"
        slide_gen.save(result, slide_path)
        saved.append(slide_path)

        progress.update(task, description="Done!")

    # Cleanup workspace (cryptographic purge)
    loader.destroy()

    # Display results
    score = result.score
    if score:
        _display_score_summary(result, score)

    console.print()
    console.print("[bold]Generated Reports:[/bold]")
    for p in saved:
        console.print(f"  [cyan]{p}[/cyan]")

    if result.total_cost_usd > 0:
        console.print(f"\n[dim]API cost: ${result.total_cost_usd:.4f}[/dim]")


@cli.command()
@click.argument("target", default=".", required=False)
@click.option("--name", "-n", default=None, help="Project name (auto-detected if omitted)")
@click.option("--lang", "-l", default="en", type=click.Choice(["en", "ja"]),
              help="Output language (en: English, ja: Japanese)")
@click.option("--stage", "-s", default="unknown",
              type=click.Choice(["seed", "series_a", "series_b", "growth", "unknown"]),
              help="Startup development stage (adjusts evaluation criteria)")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Save prompt to file instead of stdout")
@click.option("--copy", "-c", is_flag=True, help="Copy prompt to clipboard")
@click.option("--skip-git", is_flag=True, help="Skip git forensics analysis")
@click.option("--pdf", "-p", is_flag=True,
              help="Generate consulting-grade PDF (requires AI terminal like Claude Code)")
def prompt(
    target: str,
    name: str | None,
    lang: str,
    stage: str,
    output: str | None,
    copy: bool,
    skip_git: bool,
    pdf: bool,
) -> None:
    """Generate an AI evaluation prompt for IDE terminals.

    Runs heuristic analysis (no AI API needed), then outputs a structured
    prompt that you can paste into Claude Code, Cursor, GitHub Copilot, etc.

    \b
    TARGET can be (defaults to current directory if omitted):
      GitHub URL:  https://github.com/owner/repo
      Short form:  owner/repo
      Local path:  /path/to/project (default: .)
      Zip archive: /path/to/project.zip

    \b
    Examples:
      dde prompt --pdf --lang ja             # Current dir → consulting PDF
      dde prompt owner/repo --pdf            # GitHub repo → consulting PDF
      dde prompt . --lang ja                 # Current dir, Japanese output
      dde prompt owner/repo --lang ja        # GitHub repo, Japanese output
      dde prompt ./my-startup -s seed -c     # Seed stage, copy to clipboard
    """
    from src.analyze.engine import AnalysisEngine
    from src.ingest.secure_loader import SecureLoader
    from src.prompt.generator import generate_prompt

    # --pdf mode requires explicit --lang selection
    if pdf and lang == "en":
        # Check if --lang was actually passed by the user
        ctx = click.get_current_context()
        if "lang" not in ctx.params or ctx.get_parameter_source("lang") != click.core.ParameterSource.COMMANDLINE:
            lang = click.prompt(
                "PDF language / PDF言語を選択",
                type=click.Choice(["en", "ja"]),
                default="en",
            )

    config = get_config()
    # Force skip AI — prompt mode never calls AI APIs
    config.anthropic_api_key = ""
    config.ensure_dirs()

    is_url = _is_github_url(target)
    if name is None:
        name = _extract_project_name(target)

    loader = SecureLoader(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Collecting project data...", total=None)

        try:
            if is_url:
                progress.update(task, description=f"Cloning {target} ...")
                loader.load_from_url(target)
                repo_path = loader.cloned_repo_path
            else:
                source = Path(target)
                if not source.exists():
                    console.print(f"[red]Path not found: {target}[/red]")
                    sys.exit(1)
                if source.suffix == ".zip":
                    loader.load_archive(source)
                    repo_path = None
                else:
                    loader.load_directory(source)
                    repo_path = source if source.is_dir() else None
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            console.print(f"[red]Ingestion error: {e}[/red]")
            sys.exit(1)

        progress.update(task, description="Running heuristic analysis...")
        engine = AnalysisEngine(config, loader)
        result = engine.run(
            project_name=name,
            repo_path=repo_path,
            skip_git=skip_git,
        )
        progress.update(task, description="Generating prompt...")

    # Cleanup
    loader.destroy()

    # Generate the structured prompt
    if pdf:
        # --pdf mode: check if running inside an AI terminal
        if not _detect_ai_terminal():
            console.print(
                Panel(
                    "[bold yellow]⚠ AI terminal not detected[/bold yellow]\n\n"
                    "This command requires an AI-powered terminal to generate the PDF.\n"
                    "Please run inside one of:\n"
                    "  • [cyan]Claude Code[/cyan] (claude)\n"
                    "  • [cyan]Cursor[/cyan] Terminal\n"
                    "  • [cyan]GitHub Copilot[/cyan] Chat\n\n"
                    "Without AI, use: [dim]dde prompt owner/repo --lang ja[/dim] (prompt-only)",
                    title="DDE",
                    border_style="yellow",
                )
            )
            # Continue anyway — the user may know what they're doing
            console.print("[dim]Continuing anyway...[/dim]\n")

        from src.prompt.generator import generate_consulting_prompt
        prompt_text = generate_consulting_prompt(result, lang=lang, stage=stage)
    else:
        prompt_text = generate_prompt(result, lang=lang, stage=stage)

    # Output
    if output:
        out_path = Path(output)
        out_path.write_text(prompt_text, encoding="utf-8")
        console.print(f"[green]Prompt saved to: {out_path}[/green]")
    else:
        # Print to stdout (use print, not console, to avoid Rich markup)
        print(prompt_text)

    if copy:
        try:
            import subprocess
            process = subprocess.Popen(
                ["pbcopy"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            process.communicate(prompt_text.encode("utf-8"))
            console.print("[green]Prompt copied to clipboard![/green]")
        except (FileNotFoundError, OSError):
            console.print("[yellow]Could not copy to clipboard (pbcopy/xclip not found)[/yellow]")

    if not pdf:
        console.print(
            Panel(
                f"[bold]Next step[/bold]: Paste the prompt into your AI terminal\n"
                f"(Claude Code, Cursor, GitHub Copilot, etc.)\n\n"
                f"The AI will read the data and generate a full evaluation report.\n"
                f"[dim]No API keys needed — your IDE's AI handles the analysis.[/dim]",
                title="DDE Prompt Generated",
                border_style="green",
            )
        )
    # --pdf mode: no trailing panel — the prompt itself contains all instructions for the AI


@cli.command()
@click.argument("result_file", type=click.Path(exists=True), required=False, default=None)
@click.option("--format", "-f", "fmt", default="md", type=click.Choice(["md", "html"]))
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--consulting", type=click.Path(exists=True), default=None,
              help="Consulting report JSON from AI evaluation (generates consulting-grade PDF)")
@click.option("--pdf", "-p", is_flag=True, help="Generate PDF output")
@click.option("--lang", "-l", default="en", type=click.Choice(["en", "ja"]),
              help="PDF language")
def report(
    result_file: str | None,
    fmt: str,
    output: str | None,
    consulting: str | None,
    pdf: bool,
    lang: str,
) -> None:
    """Generate a report from a saved analysis result JSON.

    \b
    Standard mode:
      dde report result.json                    # Markdown report
      dde report result.json -f html            # HTML report

    \b
    Consulting mode (from AI evaluation):
      dde report --consulting ai_result.json --pdf --lang ja
    """
    from src.models import AnalysisResult
    from src.report.generator import ReportGenerator

    config = get_config()
    config.ensure_dirs()
    output_dir = Path(output) if output else config.output_dir

    if consulting:
        # Consulting PDF mode — always save to ~/Downloads
        from src.prompt.response_parser import parse_consulting_json
        from src.report.pdf_generator import PDFReportGenerator

        cr = parse_consulting_json(consulting)

        # Build a minimal AnalysisResult with consulting report attached
        if result_file:
            result_path = Path(result_file)
            data = json.loads(result_path.read_text(encoding="utf-8"))
            result = AnalysisResult(**data)
        else:
            result = AnalysisResult(
                project_name=cr.project_name or "unknown",
                analysis_id=cr.analysis_id or "consulting",
            )

        result.consulting_report = cr

        pdf_gen = PDFReportGenerator()
        safe_name = result.project_name.replace("/", "_").replace("\\", "_")

        # Date stamp in filename (ja: 2026年04月02日, en: 2026-04-02)
        now = datetime.now()
        if lang == "ja":
            date_str = now.strftime("%Y年%m月%d日")
        else:
            date_str = now.strftime("%Y-%m-%d")

        # Use ~/Downloads as default output for consulting PDFs
        downloads_dir = Path.home() / "Downloads"
        consulting_output = Path(output) if output else downloads_dir
        consulting_output.mkdir(parents=True, exist_ok=True)
        pdf_path = consulting_output / f"dde_consulting_{safe_name}_{date_str}.pdf"
        pdf_gen.generate_to_file(result, pdf_path, lang=lang)

        console.print(
            Panel(
                f"[bold green]Consulting PDF generated![/bold green]\n\n"
                f"  [cyan]{pdf_path}[/cyan]\n\n"
                f"Grade: {cr.grade} | Score: {cr.overall_score:.0f}/100\n"
                f"AI Model: {cr.ai_model_used or 'unknown'}",
                title="DDE Consulting Report",
                border_style="green",
            )
        )
        return

    # Standard report mode
    if not result_file:
        console.print("[red]Error: RESULT_FILE is required (or use --consulting)[/red]")
        sys.exit(1)

    result_path = Path(result_file)
    data = json.loads(result_path.read_text(encoding="utf-8"))
    result = AnalysisResult(**data)

    report_gen = ReportGenerator()
    saved = report_gen.save_report(result, output_dir, formats=[fmt])

    if pdf:
        from src.report.pdf_generator import PDFReportGenerator
        pdf_gen = PDFReportGenerator()
        safe_name = result.project_name.replace("/", "_").replace("\\", "_")
        pdf_path = output_dir / f"dde_report_{safe_name}_{result.analysis_id}.pdf"
        pdf_gen.generate_to_file(result, pdf_path, lang=lang)
        saved.append(pdf_path)

    for p in saved:
        console.print(f"[green]Report saved: {p}[/green]")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--analysis-id", "-a", required=True, help="Analysis ID to purge")
@click.option("--project-name", "-n", default="unknown", help="Project name")
@click.option("--operator", default="cli_user", help="Operator name for certificate")
@click.option("--cert-output", "-c", type=click.Path(), default=None, help="Certificate output path")
@click.confirmation_option(prompt="Are you sure you want to securely purge this data?")
def purge(
    path: str,
    analysis_id: str,
    project_name: str,
    operator: str,
    cert_output: str | None,
) -> None:
    """Securely purge analysis data and generate a purge certificate."""
    from src.purge.secure_delete import SecurePurger

    target = Path(path)
    purger = SecurePurger()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Securely purging data...", total=None)

        cert = purger.purge_directory(
            directory=target,
            analysis_id=analysis_id,
            project_name=project_name,
            operator=operator,
        )

        progress.update(task, description="Purge complete")

    console.print(
        Panel(
            f"Files purged: {cert.files_purged}\n"
            f"Bytes overwritten: {cert.bytes_overwritten:,}\n"
            f"Method: {cert.method}\n"
            f"Certificate ID: {cert.certificate_id}",
            title="Purge Certificate",
            border_style="green",
        )
    )

    if cert_output:
        cert_path = Path(cert_output)
    else:
        config = get_config()
        config.ensure_dirs()
        cert_path = config.output_dir / f"purge_cert_{analysis_id}.json"

    purger.export_certificate(cert, cert_path)
    console.print(f"[green]Certificate saved: {cert_path}[/green]")


@cli.command()
@click.option("--data-dir", type=click.Path(), default=None, help="Data directory with results")
def leaderboard(data_dir: str | None) -> None:
    """Show a scoring leaderboard across all completed analyses."""
    from src.models import AnalysisResult

    config = get_config()
    search_dir = Path(data_dir) if data_dir else config.output_dir

    if not search_dir.exists():
        console.print("[yellow]No analysis data found.[/yellow]")
        return

    # Find all report files and extract scores
    entries: list[tuple[str, float, str, str]] = []

    for md_file in sorted(search_dir.glob("dde_report_*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            # Parse score from the markdown header
            for line in content.splitlines():
                if "Overall Score:" in line:
                    parts = line.split("Overall Score:**")
                    if len(parts) >= 2:
                        score_part = parts[1].strip()
                        score_str = score_part.split("/")[0].strip()
                        grade_match = score_part.split("Grade: ")
                        grade = grade_match[1].rstrip(")") if len(grade_match) > 1 else "?"
                        # Extract project name from filename
                        fname = md_file.stem
                        proj_name = fname.replace("dde_report_", "").rsplit("_", 1)[0]
                        entries.append(
                            (proj_name, float(score_str), grade, str(md_file))
                        )
                    break
        except (ValueError, IndexError):
            continue

    if not entries:
        console.print("[yellow]No completed analyses found.[/yellow]")
        return

    # Sort by score descending
    entries.sort(key=lambda x: x[1], reverse=True)

    table = Table(title="Due Diligence Leaderboard")
    table.add_column("Rank", style="bold", width=6)
    table.add_column("Project", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Grade", justify="center")
    table.add_column("Report", style="dim")

    for i, (proj, score, grade, path) in enumerate(entries, 1):
        grade_color = {
            "A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red",
        }.get(grade, "white")

        table.add_row(
            str(i),
            proj,
            f"{score:.1f}/100",
            f"[{grade_color}]{grade}[/{grade_color}]",
            Path(path).name,
        )

    console.print(table)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, do_reload: bool) -> None:
    """Start the SaaS API server."""
    import uvicorn

    console.print(
        Panel(
            f"Starting DDE SaaS API\n"
            f"Host: {host}:{port}\n"
            f"Docs: http://{host}:{port}/docs",
            title="Due Diligence Engine - SaaS Mode",
            border_style="blue",
        )
    )

    uvicorn.run(
        "src.saas.app:app",
        host=host,
        port=port,
        reload=do_reload,
    )


def _display_score_summary(result, score) -> None:
    """Display a rich score summary in the terminal."""
    grade_colors = {
        "A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red",
    }
    color = grade_colors.get(score.grade, "white")

    # Overall score panel
    console.print()
    console.print(
        Panel(
            f"[bold {color}]{score.overall_score:.0f}/100 (Grade: {score.grade})[/bold {color}]\n\n"
            f"{score.recommendation}",
            title=f"Due Diligence Score: {result.project_name}",
            border_style=color,
        )
    )

    # Dimensions table
    table = Table(title="Score Dimensions")
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Weighted", justify="right")

    for dim in score.dimensions:
        table.add_row(
            dim.name,
            f"{dim.score:.0f}",
            f"{dim.weight:.0%}",
            f"{dim.weighted_score:.1f}",
        )

    console.print(table)

    # Red flags
    if score.red_flags:
        console.print()
        critical = [f for f in score.red_flags if f.is_deal_breaker]
        if critical:
            console.print("[bold red]CRITICAL RED FLAGS:[/bold red]")
            for flag in critical:
                console.print(f"  [red]!! {flag.title}[/red]: {flag.description[:100]}")

        high = [f for f in score.red_flags if f.severity.value == "high"]
        if high:
            console.print("[bold yellow]HIGH SEVERITY FLAGS:[/bold yellow]")
            for flag in high:
                console.print(f"  [yellow]! {flag.title}[/yellow]: {flag.description[:100]}")


def _detect_ai_terminal() -> bool:
    """Best-effort detection of whether we're running inside an AI terminal."""
    import os
    # Claude Code sets CLAUDE_CODE or similar env vars
    if os.environ.get("CLAUDE_CODE"):
        return True
    # Cursor sets CURSOR_SESSION or TERM_PROGRAM contains "cursor"
    if os.environ.get("CURSOR_SESSION"):
        return True
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if "cursor" in term_program or "claude" in term_program:
        return True
    # Check if parent process name hints at AI terminal
    # (heuristic — not always reliable)
    if os.environ.get("VSCODE_GIT_ASKPASS_NODE"):
        # Running inside VS Code / Cursor terminal
        return True
    return False


def _is_github_url(target: str) -> bool:
    """Determine if the target looks like a GitHub URL or owner/repo shorthand."""
    target = target.strip()
    # Explicit URLs
    if target.startswith(("https://", "http://", "git@", "github.com/")):
        return True
    # Short form: owner/repo (no dots, no path separators beyond one slash)
    import re
    if re.match(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$", target):
        # Exclude local paths like ./foo or ../bar
        if not target.startswith((".", "/")):
            return True
    return False


def _extract_project_name(target: str) -> str:
    """Extract a human-readable project name from URL or path."""
    import re
    target = target.strip().rstrip("/")
    # Remove .git suffix
    target = re.sub(r"\.git$", "", target)
    # Remove /tree/branch suffix
    target = re.sub(r"/tree/[^/]+/?$", "", target)
    # Get last path component
    name = target.rstrip("/").split("/")[-1]
    # Remove .zip suffix
    name = re.sub(r"\.zip$", "", name)
    return name or "unknown"


if __name__ == "__main__":
    cli()
