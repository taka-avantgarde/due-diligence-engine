"""Report generation in Markdown, HTML, and PDF scorecard formats."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models import AnalysisResult, Severity


class ReportGenerator:
    """Generates due diligence reports in multiple formats."""

    def __init__(self, template_dir: Path | None = None) -> None:
        if template_dir is None:
            template_dir = Path(__file__).parent.parent.parent / "templates"
        self._template_dir = template_dir
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def generate_markdown(self, result: AnalysisResult) -> str:
        """Generate a complete Markdown report.

        Args:
            result: The analysis result to report on.

        Returns:
            Markdown-formatted report string.
        """
        score = result.score
        if score is None:
            return "# Error: No score computed\n"

        lines = [
            f"# Technical Due Diligence Report: {result.project_name}",
            f"",
            f"**Analysis ID:** `{result.analysis_id}`",
            f"**Date:** {result.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Overall Score:** {score.overall_score}/100 (Grade: {score.grade})",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            f"{score.recommendation}",
            f"",
            f"---",
            f"",
            f"## Score Breakdown",
            f"",
            f"| Dimension | Score | Weight | Weighted |",
            f"|-----------|-------|--------|----------|",
        ]

        for dim in score.dimensions:
            lines.append(
                f"| {dim.name} | {dim.score:.0f}/100 | {dim.weight:.0%} | "
                f"{dim.weighted_score:.1f} |"
            )

        lines.extend([
            f"",
            f"**Overall: {score.overall_score}/100**",
            f"",
        ])

        # Dimension details
        lines.extend(["## Detailed Analysis", ""])
        for dim in score.dimensions:
            lines.extend([
                f"### {dim.name} ({dim.score:.0f}/100)",
                f"",
                f"{dim.rationale}",
                f"",
            ])
            if dim.sub_scores:
                lines.append("**Sub-scores:**")
                for name, value in dim.sub_scores.items():
                    lines.append(f"- {name.replace('_', ' ').title()}: {value:.0f}")
                lines.append("")

        # Red flags section
        if score.red_flags:
            lines.extend(["---", "", "## Red Flags", ""])

            critical = [f for f in score.red_flags if f.severity == Severity.CRITICAL]
            high = [f for f in score.red_flags if f.severity == Severity.HIGH]
            medium = [f for f in score.red_flags if f.severity == Severity.MEDIUM]
            low = [f for f in score.red_flags if f.severity == Severity.LOW]

            for label, flags in [
                ("CRITICAL", critical),
                ("HIGH", high),
                ("MEDIUM", medium),
                ("LOW", low),
            ]:
                if flags:
                    lines.append(f"### {label}")
                    lines.append("")
                    for flag in flags:
                        lines.append(f"- **{flag.title}** ({flag.category})")
                        lines.append(f"  {flag.description}")
                        if flag.evidence:
                            lines.append(f"  Evidence: {'; '.join(flag.evidence[:3])}")
                        lines.append("")

        # Code analysis summary
        code = result.code_analysis
        lines.extend([
            "---",
            "",
            "## Code Analysis Summary",
            "",
            f"- **Files:** {code.total_files}",
            f"- **Lines of Code:** {code.total_lines}",
            f"- **Languages:** {', '.join(f'{k} ({v})' for k, v in code.languages.items())}",
            f"- **API Wrapper Ratio:** {code.api_wrapper_ratio:.0%}",
            f"- **Tests:** {'Yes' if code.has_tests else 'No'}",
            f"- **CI/CD:** {'Yes' if code.has_ci_cd else 'No'}",
            f"- **Documentation:** {'Yes' if code.has_documentation else 'No'}",
            f"- **Dependencies:** {code.dependency_count}",
            "",
        ])

        # Git forensics summary
        git = result.git_forensics
        if git.total_commits > 0:
            lines.extend([
                "## Git Forensics Summary",
                "",
                f"- **Total Commits:** {git.total_commits}",
                f"- **Unique Authors:** {git.unique_authors}",
                f"- **First Commit:** {git.first_commit_date or 'N/A'}",
                f"- **Last Commit:** {git.last_commit_date or 'N/A'}",
                f"- **Rush Commit Ratio:** {git.rush_commit_ratio:.0%}",
                "",
            ])
            if git.suspicious_patterns:
                lines.append("**Suspicious Patterns:**")
                for pattern in git.suspicious_patterns:
                    lines.append(f"- {pattern}")
                lines.append("")

        # Cost information
        lines.extend([
            "---",
            "",
            "## Analysis Cost",
            "",
            f"**Total API Cost:** ${result.total_cost_usd:.4f}",
            "",
        ])
        for tier, usage in result.model_usage.items():
            if usage.get("input_tokens", 0) > 0:
                lines.append(
                    f"- {tier.title()}: {usage['input_tokens']} input / "
                    f"{usage['output_tokens']} output tokens"
                )
        lines.append("")

        lines.extend([
            "---",
            f"*Generated by Due Diligence Engine v0.1.0 on "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        ])

        return "\n".join(lines)

    def generate_html(self, result: AnalysisResult) -> str:
        """Generate an HTML scorecard using Jinja2 template.

        Args:
            result: The analysis result to report on.

        Returns:
            HTML-formatted scorecard string.
        """
        try:
            template = self._env.get_template("scorecard.html")
        except Exception:
            # Fallback: wrap markdown in basic HTML
            md = self.generate_markdown(result)
            return f"<html><body><pre>{md}</pre></body></html>"

        return template.render(
            result=result,
            score=result.score,
            code=result.code_analysis,
            git=result.git_forensics,
            docs=result.doc_analysis,
            consistency=result.consistency,
            now=datetime.utcnow(),
        )

    def save_report(
        self,
        result: AnalysisResult,
        output_dir: Path,
        formats: list[str] | None = None,
    ) -> list[Path]:
        """Save report in specified formats.

        Args:
            result: Analysis result.
            output_dir: Directory to save reports.
            formats: List of formats ('md', 'html'). Defaults to both.

        Returns:
            List of paths to generated report files.
        """
        if formats is None:
            formats = ["md", "html"]

        output_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        base_name = f"dde_report_{result.project_name}_{result.analysis_id}"

        if "md" in formats:
            md_path = output_dir / f"{base_name}.md"
            md_path.write_text(self.generate_markdown(result), encoding="utf-8")
            saved.append(md_path)

        if "html" in formats:
            html_path = output_dir / f"{base_name}.html"
            html_path.write_text(self.generate_html(result), encoding="utf-8")
            saved.append(html_path)

        return saved
