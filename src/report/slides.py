"""Architecture visualization slides with Mermaid diagrams."""

from __future__ import annotations

from src.models import AnalysisResult


class SlideGenerator:
    """Generates architecture visualization slides using Mermaid diagrams."""

    def generate(self, result: AnalysisResult) -> str:
        """Generate a complete slide deck as HTML with embedded Mermaid diagrams.

        Args:
            result: The analysis result.

        Returns:
            HTML string containing the slide deck.
        """
        score = result.score
        code = result.code_analysis

        score_chart = self._build_score_radar(result)
        language_chart = self._build_language_pie(result)
        risk_flowchart = self._build_risk_flowchart(result)
        timeline_chart = self._build_git_timeline(result)

        overall = score.overall_score if score else 0
        grade = score.grade if score else "N/A"
        recommendation = score.recommendation if score else "No score computed."

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DDE Analysis: {result.project_name}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 0; background: #0f172a; color: #e2e8f0; }}
  .slide {{ min-height: 100vh; padding: 3rem; display: flex; flex-direction: column; justify-content: center; border-bottom: 2px solid #334155; }}
  h1 {{ font-size: 2.5rem; color: #38bdf8; }}
  h2 {{ font-size: 1.8rem; color: #7dd3fc; }}
  .score-badge {{ display: inline-block; padding: 0.5rem 1.5rem; border-radius: 999px; font-size: 2rem; font-weight: bold; }}
  .grade-A {{ background: #22c55e; color: #000; }}
  .grade-B {{ background: #84cc16; color: #000; }}
  .grade-C {{ background: #eab308; color: #000; }}
  .grade-D {{ background: #f97316; color: #fff; }}
  .grade-F {{ background: #ef4444; color: #fff; }}
  .mermaid {{ background: #1e293b; padding: 1.5rem; border-radius: 0.5rem; margin: 1rem 0; }}
  .metric {{ display: inline-block; margin: 0.5rem; padding: 1rem 1.5rem; background: #1e293b; border-radius: 0.5rem; text-align: center; }}
  .metric .value {{ font-size: 2rem; font-weight: bold; color: #38bdf8; }}
  .metric .label {{ font-size: 0.8rem; color: #94a3b8; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ color: #38bdf8; }}
</style>
</head>
<body>
<script>mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});</script>

<!-- Slide 1: Title -->
<div class="slide">
  <h1>Technical Due Diligence Report</h1>
  <h2>{result.project_name}</h2>
  <p>Analysis ID: <code>{result.analysis_id}</code></p>
  <p>{result.timestamp.strftime('%Y-%m-%d %H:%M UTC')}</p>
  <div>
    <span class="score-badge grade-{grade}">{overall:.0f}/100 ({grade})</span>
  </div>
  <p style="margin-top: 1rem; font-size: 1.2rem;">{recommendation}</p>
</div>

<!-- Slide 2: Score Breakdown -->
<div class="slide">
  <h2>Score Breakdown</h2>
  {score_chart}
</div>

<!-- Slide 3: Codebase Overview -->
<div class="slide">
  <h2>Codebase Overview</h2>
  <div>
    <div class="metric"><div class="value">{code.total_files}</div><div class="label">Files</div></div>
    <div class="metric"><div class="value">{code.total_lines:,}</div><div class="label">Lines of Code</div></div>
    <div class="metric"><div class="value">{len(code.languages)}</div><div class="label">Languages</div></div>
    <div class="metric"><div class="value">{code.api_wrapper_ratio:.0%}</div><div class="label">API Wrapper Ratio</div></div>
    <div class="metric"><div class="value">{code.dependency_count}</div><div class="label">Dependencies</div></div>
  </div>
  {language_chart}
</div>

<!-- Slide 4: Risk Analysis -->
<div class="slide">
  <h2>Risk Analysis</h2>
  {risk_flowchart}
</div>

<!-- Slide 5: Git Timeline -->
<div class="slide">
  <h2>Development Timeline</h2>
  {timeline_chart}
</div>

<!-- Slide 6: Cost -->
<div class="slide">
  <h2>Analysis Cost</h2>
  <div class="metric"><div class="value">${result.total_cost_usd:.4f}</div><div class="label">Total API Cost</div></div>
  <table>
    <tr><th>Model Tier</th><th>Input Tokens</th><th>Output Tokens</th></tr>
    {"".join(f'<tr><td>{tier.title()}</td><td>{u.get("input_tokens", 0):,}</td><td>{u.get("output_tokens", 0):,}</td></tr>' for tier, u in result.model_usage.items() if u.get("input_tokens", 0) > 0)}
  </table>
</div>

</body>
</html>"""

        return html

    def _build_score_radar(self, result: AnalysisResult) -> str:
        """Build a bar chart of dimension scores using Mermaid xychart."""
        if not result.score:
            return "<p>No scores available.</p>"

        # Use a simple bar chart (Mermaid xychart-beta)
        dims = result.score.dimensions
        labels = [f'"{d.name}"' for d in dims]
        values = [str(int(d.score)) for d in dims]

        return f"""<div class="mermaid">
xychart-beta
    title "Dimension Scores"
    x-axis [{", ".join(labels)}]
    y-axis "Score (0-100)" 0 --> 100
    bar [{", ".join(values)}]
</div>"""

    def _build_language_pie(self, result: AnalysisResult) -> str:
        """Build a pie chart of language distribution."""
        langs = result.code_analysis.languages
        if not langs:
            return "<p>No language data available.</p>"

        entries = "\n    ".join(
            f'"{ext}" : {count}' for ext, count in sorted(langs.items(), key=lambda x: -x[1])
        )

        return f"""<div class="mermaid">
pie title Language Distribution
    {entries}
</div>"""

    def _build_risk_flowchart(self, result: AnalysisResult) -> str:
        """Build a risk decision flowchart."""
        if not result.score:
            return "<p>No risk data available.</p>"

        critical = sum(1 for f in result.score.red_flags if f.is_deal_breaker)
        high = sum(1 for f in result.score.red_flags if f.severity.value == "high")

        return f"""<div class="mermaid">
flowchart TD
    A[Start Analysis] --> B{{Critical Flags: {critical}}}
    B -->|Yes| C[Deal Breaker Review]
    B -->|No| D{{High Flags: {high}}}
    D -->|Multiple| E[Conditional Proceed]
    D -->|Few/None| F[Standard Proceed]
    C --> G[Pass / Heavy Discount]
    E --> H[Invest with Conditions]
    F --> I[Standard Terms]
</div>"""

    def _build_git_timeline(self, result: AnalysisResult) -> str:
        """Build a git activity timeline."""
        git = result.git_forensics
        if git.total_commits == 0:
            return "<p>No git history available.</p>"

        return f"""<div class="mermaid">
timeline
    title Development History
    section Overview
        Total Commits : {git.total_commits}
        Authors : {git.unique_authors}
    section Timeline
        First Commit : {git.first_commit_date or 'Unknown'}
        Last Commit : {git.last_commit_date or 'Unknown'}
    section Risks
        Rush Ratio : {git.rush_commit_ratio:.0%}
        Suspicious Patterns : {len(git.suspicious_patterns)}
</div>"""

    def save(self, result: AnalysisResult, output_path: Path) -> Path:
        """Save the slide deck to a file.

        Args:
            result: Analysis result.
            output_path: Path to save the HTML file.

        Returns:
            Path to the saved file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = self.generate(result)
        output_path.write_text(html, encoding="utf-8")
        return output_path
