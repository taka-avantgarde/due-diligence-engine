"""Web dashboard for the Due Diligence Engine.

Provides a browser-based interface for:
- GitHub OAuth connection
- Repository selection and analysis
- Real-time analysis progress and results
- Disconnect & purge with certificate generation
- PDF report export

All HTML is rendered via inline Jinja2 templates (no separate template files).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ---------------------------------------------------------------------------
# In-memory analysis store (would be backed by a database in production)
# ---------------------------------------------------------------------------

# analysis_id -> {result: AnalysisResult, status: str, connection_id: str, purge_cert: PurgeCertificate | None}
_analysis_store: dict[str, dict[str, Any]] = {}


def store_analysis(analysis_id: str, data: dict[str, Any]) -> None:
    """Store analysis data in the in-memory store."""
    _analysis_store[analysis_id] = data


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    """Retrieve analysis data from the in-memory store."""
    return _analysis_store.get(analysis_id)


# ---------------------------------------------------------------------------
# Shared HTML layout
# ---------------------------------------------------------------------------

_BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - DDE</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        surface: '#1e293b',
        accent: '#38bdf8',
      }}
    }}
  }}
}}
</script>
<style>
  body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
  .animate-pulse-slow {{ animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }}
</style>
</head>
<body class="bg-slate-950 text-slate-200 min-h-screen">
  <nav class="border-b border-slate-800 px-6 py-4">
    <div class="max-w-5xl mx-auto flex items-center justify-between">
      <a href="/dashboard/" class="text-accent font-bold text-lg tracking-wide">DUE DILIGENCE ENGINE</a>
      <div class="text-sm text-slate-500">Technical DD for VCs</div>
    </div>
  </nav>
  <main class="max-w-5xl mx-auto px-6 py-8">
    {content}
  </main>
  <footer class="border-t border-slate-800 mt-12 py-6 text-center text-xs text-slate-600">
    CONFIDENTIAL &mdash; Subject to NDA &mdash; Due Diligence Engine v0.1.0
  </footer>
  {scripts}
</body>
</html>"""


def _render_page(title: str, content: str, scripts: str = "") -> HTMLResponse:
    """Render a full HTML page with the shared layout."""
    html = _BASE_TEMPLATE.format(title=title, content=content, scripts=scripts)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Page: Landing / Login
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def landing_page() -> HTMLResponse:
    """Landing page with URL search bar — paste a GitHub URL and analyze."""
    content = """
    <div class="flex flex-col items-center justify-center min-h-[70vh]">

      <!-- Hero: Search Bar -->
      <div class="text-center max-w-2xl w-full">
        <h1 class="text-5xl font-bold text-white mb-3 tracking-tight">
          Due Diligence Engine
        </h1>
        <p class="text-slate-400 text-lg mb-10">
          Paste a GitHub URL. Get a technology score in minutes.
        </p>

        <!-- Search Bar -->
        <form id="analyze-form" class="relative w-full">
          <div class="flex items-center bg-slate-900 border-2 border-slate-700
                      focus-within:border-accent rounded-2xl overflow-hidden
                      transition-all duration-300 shadow-xl shadow-black/30">
            <div class="pl-5 text-slate-500">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
            </div>
            <input id="repo-url" type="text"
                   placeholder="https://github.com/owner/repo"
                   class="flex-1 bg-transparent text-white text-lg px-4 py-5
                          outline-none placeholder-slate-600"
                   autocomplete="off" spellcheck="false" />
            <button type="submit" id="analyze-btn"
                    class="bg-accent hover:bg-cyan-400 text-slate-950 font-bold
                           text-lg px-8 py-5 transition-all duration-200
                           disabled:opacity-50 disabled:cursor-not-allowed">
              Analyze
            </button>
          </div>
          <p id="url-hint" class="text-slate-600 text-sm mt-3 text-left pl-2">
            Public repos: paste URL. Private repos:
            <a href="/api/github/connect?user_id=demo_user"
               class="text-accent hover:underline">connect GitHub first</a>.
          </p>
        </form>
      </div>

      <!-- Status area (hidden by default) -->
      <div id="status-area" class="hidden w-full max-w-2xl mt-8">
        <div class="bg-surface rounded-2xl border border-slate-800 p-8">
          <div class="flex items-center gap-4 mb-6">
            <div id="spinner" class="w-8 h-8 border-3 border-accent border-t-transparent
                        rounded-full animate-spin"></div>
            <div>
              <div id="status-text" class="text-white font-semibold">Analyzing...</div>
              <div id="status-sub" class="text-slate-500 text-sm">This may take a few minutes</div>
            </div>
          </div>

          <div class="space-y-3 text-sm">
            <div id="step-1" class="flex items-center gap-3 text-slate-600">
              <span class="w-5 text-center">&#9675;</span>
              <span>Cloning repository</span>
            </div>
            <div id="step-2" class="flex items-center gap-3 text-slate-600">
              <span class="w-5 text-center">&#9675;</span>
              <span>Code structure analysis (AST, dependencies)</span>
            </div>
            <div id="step-3" class="flex items-center gap-3 text-slate-600">
              <span class="w-5 text-center">&#9675;</span>
              <span>Git forensics</span>
            </div>
            <div id="step-4" class="flex items-center gap-3 text-slate-600">
              <span class="w-5 text-center">&#9675;</span>
              <span>AI analysis (Haiku &rarr; Sonnet &rarr; Opus)</span>
            </div>
            <div id="step-5" class="flex items-center gap-3 text-slate-600">
              <span class="w-5 text-center">&#9675;</span>
              <span>Scoring &amp; report generation</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 10-Level Tech Rating Preview -->
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mt-16 w-full max-w-3xl">
        <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">
          <div class="text-accent text-xs font-bold tracking-wider mb-2">ORIGINALITY</div>
          <div class="text-white font-semibold text-sm mb-1">Lv.1 Copy &mdash; Lv.10 Frontier</div>
          <p class="text-slate-500 text-xs">API wrapper or genuine IP?</p>
        </div>
        <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">
          <div class="text-accent text-xs font-bold tracking-wider mb-2">ADVANCEMENT</div>
          <div class="text-white font-semibold text-sm mb-1">Lv.1 Legacy &mdash; Lv.10 Visionary</div>
          <p class="text-slate-500 text-xs">How cutting-edge is the tech?</p>
        </div>
        <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">
          <div class="text-accent text-xs font-bold tracking-wider mb-2">IMPLEMENTATION</div>
          <div class="text-white font-semibold text-sm mb-1">Lv.1 Mockup &mdash; Lv.10 Mission-Critical</div>
          <p class="text-slate-500 text-xs">PoC or production-grade?</p>
        </div>
        <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">
          <div class="text-accent text-xs font-bold tracking-wider mb-2">ARCHITECTURE</div>
          <div class="text-white font-semibold text-sm mb-1">Lv.1 Spaghetti &mdash; Lv.10 Distributed</div>
          <p class="text-slate-500 text-xs">Scalable design?</p>
        </div>
        <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">
          <div class="text-accent text-xs font-bold tracking-wider mb-2">CONSISTENCY</div>
          <div class="text-white font-semibold text-sm mb-1">Lv.1 Fabricated &mdash; Lv.10 Transparent</div>
          <p class="text-slate-500 text-xs">Claims match reality?</p>
        </div>
        <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">
          <div class="text-accent text-xs font-bold tracking-wider mb-2">SECURITY</div>
          <div class="text-white font-semibold text-sm mb-1">Lv.1 Negligent &mdash; Lv.10 Military-Grade</div>
          <p class="text-slate-500 text-xs">Security maturity level?</p>
        </div>
      </div>

      <!-- Pricing pills -->
      <div class="flex flex-col sm:flex-row gap-4 mt-12">
        <div class="bg-surface rounded-xl px-6 py-4 border border-green-900/50 text-center">
          <div class="text-green-400 font-bold text-sm">BYOK</div>
          <div class="text-white text-xl font-bold">FREE</div>
          <div class="text-slate-500 text-xs">Your own API key</div>
        </div>
        <div class="bg-surface rounded-xl px-6 py-4 border border-accent/30 text-center">
          <div class="text-accent font-bold text-sm">SaaS</div>
          <div class="text-white text-xl font-bold">2x API Cost</div>
          <div class="text-slate-500 text-xs">We handle everything</div>
        </div>
      </div>
    </div>
    """

    scripts = """
    <script>
    const form = document.getElementById('analyze-form');
    const input = document.getElementById('repo-url');
    const btn = document.getElementById('analyze-btn');
    const statusArea = document.getElementById('status-area');
    const statusText = document.getElementById('status-text');
    const statusSub = document.getElementById('status-sub');

    // Parse GitHub URL to owner/repo
    function parseGitHubUrl(url) {
      url = url.trim();
      if (!url) return null;
      // Remove trailing slashes
      url = url.replace(/\/+$/, '');
      // Handle full GitHub URLs
      var m = url.match(/github[.]com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)/);
      if (m) return m[1] + '/' + m[2].replace(/[.]git$/, '');
      // Handle owner/repo format
      var m2 = url.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
      if (m2) return m2[1] + '/' + m2[2];
      return null;
    }

    function setStep(n, status) {
      const el = document.getElementById('step-' + n);
      if (!el) return;
      const icon = el.querySelector('span');
      el.className = el.className.replace(/text-[a-z]+-[0-9]+/g, '').replace(/text-accent/g, '').replace(/text-slate-600/g, '');
      if (status === 'done') {
        el.classList.add('text-green-400');
        icon.innerHTML = '&#10003;';
      } else if (status === 'active') {
        el.classList.add('text-accent');
        icon.innerHTML = '&#9679;';
        el.classList.add('animate-pulse');
      } else {
        el.classList.add('text-slate-600');
        icon.innerHTML = '&#9675;';
      }
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const repo = parseGitHubUrl(input.value);
      if (!repo) {
        input.classList.add('border-red-500');
        document.getElementById('url-hint').textContent = 'Please enter a valid GitHub URL (e.g., https://github.com/owner/repo)';
        document.getElementById('url-hint').classList.add('text-red-400');
        return;
      }

      // Show status area
      btn.disabled = true;
      btn.textContent = 'Analyzing...';
      input.disabled = true;
      statusArea.classList.remove('hidden');

      // Simulate progress steps
      const steps = [
        { n: 1, label: 'Cloning repository...', delay: 0 },
        { n: 2, label: 'Analyzing code structure...', delay: 2000 },
        { n: 3, label: 'Running git forensics...', delay: 4000 },
        { n: 4, label: 'AI analysis in progress...', delay: 6000 },
        { n: 5, label: 'Generating report...', delay: 10000 },
      ];

      for (const step of steps) {
        setTimeout(() => {
          if (step.n > 1) setStep(step.n - 1, 'done');
          setStep(step.n, 'active');
          statusText.textContent = step.label;
        }, step.delay);
      }

      // POST to analyze endpoint
      try {
        const resp = await fetch('/api/v1/analyze/url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repo_url: repo }),
        });

        if (resp.ok) {
          const data = await resp.json();
          window.location.href = '/dashboard/analysis/' + data.analysis_id;
        } else if (resp.status === 422 || resp.status === 400) {
          const err = await resp.json();
          statusText.textContent = 'Error: ' + (err.detail || 'Analysis failed');
          statusSub.textContent = 'Please check the URL and try again.';
          document.getElementById('spinner').classList.add('hidden');
          btn.disabled = false;
          btn.textContent = 'Analyze';
          input.disabled = false;
        } else {
          throw new Error('HTTP ' + resp.status);
        }
      } catch (err) {
        statusText.textContent = 'Error: ' + err.message;
        statusSub.textContent = 'Please try again.';
        document.getElementById('spinner').classList.add('hidden');
        btn.disabled = false;
        btn.textContent = 'Analyze';
        input.disabled = false;
      }
    });

    // Focus the input on page load
    input.focus();
    </script>
    """
    return _render_page("Due Diligence Engine", content, scripts)


# ---------------------------------------------------------------------------
# Page: Repository Selection
# ---------------------------------------------------------------------------

@router.get("/repos", response_class=HTMLResponse)
async def repos_page(
    connection_id: str = Query(..., description="GitHub connection ID"),
) -> HTMLResponse:
    """Show list of accessible repositories for analysis."""
    # In a real implementation, we'd fetch repos from GitHubOAuthManager.
    # Here we render a template that will be populated by the API.
    content = f"""
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white mb-2">Select a Repository</h1>
      <p class="text-slate-400">Choose a repository to run technical due diligence analysis.</p>
    </div>

    <div id="repos-list" class="space-y-3">
      <div class="text-center py-12 text-slate-500">
        <div class="animate-pulse-slow">Loading repositories...</div>
      </div>
    </div>

    <div class="mt-8 text-center">
      <a href="/dashboard/" class="text-slate-500 hover:text-slate-300 text-sm">
        &larr; Back to home
      </a>
    </div>
    """

    scripts = """
    <script>
    const connectionId = '""" + connection_id + """';

    async function loadRepos() {
      try {
        const resp = await fetch(`/api/github/repos/${connectionId}`);
        if (!resp.ok) throw new Error('Failed to load repositories');
        const repos = await resp.json();

        const container = document.getElementById('repos-list');
        if (repos.length === 0) {
          container.innerHTML = '<p class="text-slate-500 text-center py-8">No repositories found.</p>';
          return;
        }

        container.innerHTML = repos.map(repo => `
          <div class="bg-surface rounded-xl p-5 border border-slate-800
                      hover:border-accent/50 transition-all duration-200">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-3">
                  <h3 class="font-semibold text-white">${repo.full_name}</h3>
                  ${repo.private
                    ? '<span class="text-xs bg-amber-900/50 text-amber-400 px-2 py-0.5 rounded-full">Private</span>'
                    : '<span class="text-xs bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full">Public</span>'}
                </div>
                <p class="text-slate-500 text-sm mt-1">${repo.description || 'No description'}</p>
                <div class="flex items-center gap-4 mt-2 text-xs text-slate-600">
                  ${repo.language ? `<span>${repo.language}</span>` : ''}
                  <span>${repo.stargazers_count} stars</span>
                  <span>Updated ${new Date(repo.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
              <form action="/api/analyze/github/${connectionId}/${encodeURIComponent(repo.full_name)}" method="POST">
                <button type="submit"
                        class="bg-accent hover:bg-cyan-500 text-slate-950 font-semibold
                               px-5 py-2 rounded-lg transition-colors duration-200 text-sm">
                  Analyze
                </button>
              </form>
            </div>
          </div>
        `).join('');
      } catch (err) {
        document.getElementById('repos-list').innerHTML =
          `<p class="text-red-400 text-center py-8">Error: ${err.message}</p>`;
      }
    }

    loadRepos();
    </script>
    """

    return _render_page("Select Repository", content, scripts)


# ---------------------------------------------------------------------------
# Page: Analysis Results
# ---------------------------------------------------------------------------

@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def analysis_page(analysis_id: str) -> HTMLResponse:
    """Show analysis progress or completed results."""
    data = get_analysis(analysis_id)

    if data is None:
        content = """
        <div class="text-center py-20">
          <h1 class="text-2xl font-bold text-red-400 mb-4">Analysis Not Found</h1>
          <p class="text-slate-500">The requested analysis could not be found.</p>
          <a href="/dashboard/" class="text-accent hover:underline mt-4 inline-block">Return to home</a>
        </div>
        """
        return _render_page("Not Found", content)

    status = data.get("status", "unknown")

    if status == "running":
        return _render_progress_page(analysis_id)
    elif status == "completed":
        return _render_results_page(analysis_id, data)
    elif status == "purged":
        return _render_purged_results_page(analysis_id, data)
    else:
        content = f"""
        <div class="text-center py-20">
          <h1 class="text-2xl font-bold text-yellow-400 mb-4">Analysis Status: {status}</h1>
          <p class="text-slate-500">Please wait or try again later.</p>
        </div>
        """
        return _render_page("Analysis", content)


def _render_progress_page(analysis_id: str) -> HTMLResponse:
    """Render the analysis in-progress page with auto-refresh."""
    content = f"""
    <div class="flex flex-col items-center justify-center min-h-[50vh]">
      <div class="text-center">
        <div class="w-16 h-16 border-4 border-accent border-t-transparent rounded-full
                    animate-spin mx-auto mb-8"></div>
        <h1 class="text-2xl font-bold text-white mb-4">Analysis in Progress</h1>
        <p class="text-slate-400 mb-2">Running AI-powered due diligence pipeline...</p>
        <p class="text-slate-600 text-sm">Analysis ID: {analysis_id}</p>

        <div class="mt-8 bg-surface rounded-xl p-6 border border-slate-800 max-w-md mx-auto text-left">
          <div class="space-y-3 text-sm">
            <div class="flex items-center gap-3 text-green-400">
              <span>&#10003;</span> Phase 1: Local code analysis
            </div>
            <div class="flex items-center gap-3 text-accent animate-pulse">
              <span>&#9679;</span> Phase 2: AI-enhanced analysis (Haiku &rarr; Sonnet &rarr; Opus)
            </div>
            <div class="flex items-center gap-3 text-slate-600">
              <span>&#9675;</span> Phase 3: Scoring &amp; report generation
            </div>
          </div>
        </div>
      </div>
    </div>
    """

    scripts = f"""
    <script>
    setTimeout(function() {{ window.location.reload(); }}, 5000);
    </script>
    """

    return _render_page("Analyzing...", content, scripts)


def _render_results_page(analysis_id: str, data: dict[str, Any]) -> HTMLResponse:
    """Render the completed analysis results page."""
    result = data.get("result")
    connection_id = data.get("connection_id", "")

    if result is None:
        return _render_page("Error", "<p>No result data found.</p>")

    score = result.score
    if score is None:
        score_html = '<p class="text-slate-500">No score computed.</p>'
        grade = "N/A"
        overall_score = 0
        recommendation = ""
        red_flags_html = ""
    else:
        grade = score.grade
        overall_score = score.overall_score
        recommendation = score.recommendation

        # Grade color
        grade_colors = {
            "A": "text-green-400 border-green-500 bg-green-950/50",
            "B": "text-lime-400 border-lime-500 bg-lime-950/50",
            "C": "text-yellow-400 border-yellow-500 bg-yellow-950/50",
            "D": "text-orange-400 border-orange-500 bg-orange-950/50",
            "F": "text-red-400 border-red-500 bg-red-950/50",
        }
        gc = grade_colors.get(grade, "text-slate-400 border-slate-500 bg-slate-950/50")

        # Score circle
        score_html = f"""
        <div class="flex flex-col md:flex-row items-center justify-center gap-8 mb-8">
          <div class="w-40 h-40 rounded-full border-4 {gc}
                      flex flex-col items-center justify-center">
            <div class="text-5xl font-bold">{overall_score:.0f}</div>
            <div class="text-sm opacity-75">/ 100 ({grade})</div>
          </div>
          <div class="bg-surface rounded-xl p-6 border border-slate-800 max-w-md">
            <p class="text-slate-300">{recommendation}</p>
          </div>
        </div>
        """

        # Dimensions table
        dims_rows = ""
        for dim in score.dimensions:
            bar_color = "bg-green-500" if dim.score >= 70 else "bg-yellow-500" if dim.score >= 40 else "bg-red-500"
            dims_rows += f"""
            <tr class="border-b border-slate-800">
              <td class="py-3 font-medium text-white">{dim.name}</td>
              <td class="py-3 text-center">{dim.score:.0f}/100</td>
              <td class="py-3 text-center">{dim.weight:.0%}</td>
              <td class="py-3">
                <div class="w-full bg-slate-800 rounded-full h-2">
                  <div class="{bar_color} rounded-full h-2" style="width: {dim.score}%"></div>
                </div>
              </td>
            </tr>
            <tr class="border-b border-slate-800/50">
              <td colspan="4" class="py-2 text-sm text-slate-500 pl-4">{dim.rationale}</td>
            </tr>
            """

        score_html += f"""
        <div class="bg-surface rounded-xl p-6 border border-slate-800 mb-6">
          <h2 class="text-lg font-semibold text-accent mb-4">Score Breakdown</h2>
          <table class="w-full">
            <thead>
              <tr class="text-xs text-accent uppercase tracking-wider">
                <th class="text-left py-2">Dimension</th>
                <th class="text-center py-2">Score</th>
                <th class="text-center py-2">Weight</th>
                <th class="text-left py-2" style="width: 40%">Bar</th>
              </tr>
            </thead>
            <tbody>{dims_rows}</tbody>
          </table>
        </div>
        """

        # Red flags
        if score.red_flags:
            severity_styles = {
                "critical": "bg-red-950/50 border-l-4 border-red-500",
                "high": "bg-orange-950/50 border-l-4 border-orange-500",
                "medium": "bg-yellow-950/50 border-l-4 border-yellow-500",
                "low": "bg-green-950/50 border-l-4 border-green-500",
                "info": "bg-cyan-950/50 border-l-4 border-cyan-500",
            }
            severity_badges = {
                "critical": "bg-red-900 text-red-300",
                "high": "bg-orange-900 text-orange-300",
                "medium": "bg-yellow-900 text-yellow-300",
                "low": "bg-green-900 text-green-300",
                "info": "bg-cyan-900 text-cyan-300",
            }

            flags_items = ""
            for flag in score.red_flags:
                sv = flag.severity.value
                style = severity_styles.get(sv, "bg-slate-800 border-l-4 border-slate-500")
                badge = severity_badges.get(sv, "bg-slate-700 text-slate-300")
                evidence_html = ""
                if flag.evidence:
                    evidence_html = (
                        '<p class="text-xs text-slate-600 mt-1">Evidence: '
                        + "; ".join(flag.evidence[:3])
                        + "</p>"
                    )
                flags_items += f"""
                <div class="{style} rounded-r-lg p-4 mb-3">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="{badge} text-xs px-2 py-0.5 rounded-full uppercase font-bold">{sv}</span>
                    <span class="font-semibold text-white">{flag.title}</span>
                    <span class="text-xs text-slate-500">({flag.category})</span>
                  </div>
                  <p class="text-sm text-slate-400">{flag.description}</p>
                  {evidence_html}
                </div>
                """

            red_flags_html = f"""
            <div class="bg-surface rounded-xl p-6 border border-slate-800 mb-6">
              <h2 class="text-lg font-semibold text-red-400 mb-4">
                Red Flags ({len(score.red_flags)})
              </h2>
              {flags_items}
            </div>
            """
        else:
            red_flags_html = ""

    # Action buttons
    actions_html = f"""
    <div class="flex flex-col sm:flex-row gap-4 justify-center mt-8 mb-8">
      <a href="/api/report/{analysis_id}/pdf"
         class="inline-flex items-center justify-center gap-2 bg-accent hover:bg-cyan-500
                text-slate-950 font-semibold px-6 py-3 rounded-xl transition-colors duration-200">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        Export PDF
      </a>

      <button onclick="showDisconnectModal()"
              class="inline-flex items-center justify-center gap-2 bg-red-900/50 hover:bg-red-800
                     text-red-300 font-semibold px-6 py-3 rounded-xl
                     border border-red-800 hover:border-red-600 transition-colors duration-200">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
        </svg>
        Disconnect &amp; Purge
      </button>
    </div>

    <!-- Disconnect Confirmation Modal -->
    <div id="disconnect-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm
         hidden items-center justify-center z-50">
      <div class="bg-slate-900 rounded-2xl border border-red-800 p-8 max-w-lg mx-4 shadow-2xl">
        <h3 class="text-xl font-bold text-red-400 mb-4">Disconnect &amp; Purge Data</h3>

        <div class="bg-red-950/30 border border-red-900 rounded-lg p-4 mb-4">
          <p class="text-red-300 text-sm mb-3">
            <strong>Warning:</strong> This action will:
          </p>
          <ul class="text-red-300/80 text-sm space-y-1 list-disc list-inside">
            <li>Revoke your GitHub access token</li>
            <li>Permanently delete all cloned source code</li>
            <li>Generate a purge certificate as proof of deletion</li>
          </ul>
        </div>

        <div class="bg-slate-800 rounded-lg p-4 mb-6 space-y-2">
          <p class="text-slate-300 text-sm">
            All source code data will be permanently deleted from this tool.
            Only report scores and findings will be retained.
          </p>
          <p class="text-slate-400 text-sm" lang="ja">
            &#20840;&#12390;&#12398;&#12477;&#12540;&#12473;&#12467;&#12540;&#12489;&#12487;&#12540;&#12479;&#12364;&#12371;&#12398;&#12484;&#12540;&#12523;&#12363;&#12425;&#23436;&#20840;&#12395;&#21066;&#38500;&#12373;&#12428;&#12414;&#12377;&#12290;&#12524;&#12509;&#12540;&#12488;&#12398;&#12473;&#12467;&#12450;&#12392;&#25152;&#35211;&#12398;&#12415;&#20445;&#25345;&#12373;&#12428;&#12414;&#12377;&#12290;
          </p>
        </div>

        <div class="flex gap-3 justify-end">
          <button onclick="hideDisconnectModal()"
                  class="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600
                         text-slate-300 transition-colors duration-200">
            Cancel
          </button>
          <form action="/api/github/disconnect/{connection_id}" method="POST" id="disconnect-form">
            <input type="hidden" name="analysis_id" value="{analysis_id}">
            <button type="submit"
                    class="px-5 py-2 rounded-lg bg-red-700 hover:bg-red-600
                           text-white font-semibold transition-colors duration-200">
              Confirm Disconnect &amp; Purge
            </button>
          </form>
        </div>
      </div>
    </div>
    """

    content = f"""
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-white mb-1">Analysis Results</h1>
      <p class="text-slate-500 text-sm">
        Analysis ID: {analysis_id} &mdash;
        {result.project_name} &mdash;
        {result.timestamp.strftime('%Y-%m-%d %H:%M UTC')}
      </p>
    </div>

    {score_html}
    {red_flags_html}
    {actions_html}
    """

    scripts = """
    <script>
    function showDisconnectModal() {
      document.getElementById('disconnect-modal').classList.remove('hidden');
      document.getElementById('disconnect-modal').classList.add('flex');
    }
    function hideDisconnectModal() {
      document.getElementById('disconnect-modal').classList.add('hidden');
      document.getElementById('disconnect-modal').classList.remove('flex');
    }
    // Close modal on backdrop click
    document.getElementById('disconnect-modal').addEventListener('click', function(e) {
      if (e.target === this) hideDisconnectModal();
    });
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') hideDisconnectModal();
    });
    </script>
    """

    return _render_page(f"Results: {result.project_name}", content, scripts)


def _render_purged_results_page(analysis_id: str, data: dict[str, Any]) -> HTMLResponse:
    """Render results page for a purged analysis (scores retained, data deleted)."""
    result = data.get("result")
    if result is None:
        return _render_page("Error", "<p>No result data found.</p>")

    score = result.score
    if score is None:
        overall_score = 0
        grade = "N/A"
        recommendation = ""
    else:
        overall_score = score.overall_score
        grade = score.grade
        recommendation = score.recommendation

    content = f"""
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-white mb-1">Analysis Results (Purged)</h1>
      <p class="text-slate-500 text-sm">
        Analysis ID: {analysis_id} &mdash; Data has been purged
      </p>
    </div>

    <div class="bg-red-950/30 border border-red-800 rounded-xl p-6 mb-8 text-center">
      <p class="text-red-300 font-semibold mb-2">Source Code Data Purged</p>
      <p class="text-slate-400 text-sm">
        All source code data has been permanently deleted. Only scores and findings are retained.
      </p>
    </div>

    <div class="flex items-center justify-center gap-4 mb-8">
      <div class="text-center">
        <div class="text-5xl font-bold text-white">{overall_score:.0f}</div>
        <div class="text-slate-500 text-sm">/ 100 (Grade: {grade})</div>
      </div>
    </div>

    <div class="bg-surface rounded-xl p-6 border border-slate-800 mb-6 text-center">
      <p class="text-slate-300">{recommendation}</p>
    </div>

    <div class="text-center mt-6">
      <a href="/dashboard/purge-complete/{analysis_id}"
         class="text-accent hover:underline">View Purge Certificate</a>
    </div>
    """

    return _render_page(f"Purged: {result.project_name}", content)


# ---------------------------------------------------------------------------
# Page: Purge Certificate
# ---------------------------------------------------------------------------

@router.get("/purge-complete/{analysis_id}", response_class=HTMLResponse)
async def purge_complete_page(analysis_id: str) -> HTMLResponse:
    """Show purge certificate confirmation page."""
    data = get_analysis(analysis_id)

    if data is None:
        return _render_page(
            "Not Found",
            '<p class="text-center py-20 text-slate-500">Analysis not found.</p>',
        )

    purge_cert = data.get("purge_cert")
    if purge_cert is None:
        return _render_page(
            "No Certificate",
            '<p class="text-center py-20 text-slate-500">No purge certificate found for this analysis.</p>',
        )

    # Truncate verification hash for display
    display_hash = purge_cert.verification_hash[:64]
    if len(purge_cert.verification_hash) > 64:
        display_hash += "..."

    content = f"""
    <div class="flex flex-col items-center justify-center min-h-[50vh]">
      <div class="max-w-2xl w-full">
        <div class="text-center mb-8">
          <div class="w-16 h-16 rounded-full bg-green-950 border-2 border-green-500
                      flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-green-400 mb-2">Data Successfully Purged</h1>
          <p class="text-slate-400">All source code data has been cryptographically erased.</p>
        </div>

        <div class="bg-surface rounded-xl border border-slate-800 overflow-hidden">
          <div class="bg-red-900/20 px-6 py-3 border-b border-slate-800">
            <h2 class="font-semibold text-red-300">Purge Certificate</h2>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-slate-500">Certificate ID</div>
                <div class="text-white font-mono text-xs break-all">{purge_cert.certificate_id}</div>
              </div>
              <div>
                <div class="text-slate-500">Analysis ID</div>
                <div class="text-white font-mono text-xs">{purge_cert.analysis_id}</div>
              </div>
              <div>
                <div class="text-slate-500">Project Name</div>
                <div class="text-white">{purge_cert.project_name}</div>
              </div>
              <div>
                <div class="text-slate-500">Purge Timestamp</div>
                <div class="text-white">{purge_cert.purge_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
              </div>
              <div>
                <div class="text-slate-500">Files Purged</div>
                <div class="text-white">{purge_cert.files_purged}</div>
              </div>
              <div>
                <div class="text-slate-500">Bytes Overwritten</div>
                <div class="text-white">{purge_cert.bytes_overwritten:,}</div>
              </div>
              <div>
                <div class="text-slate-500">Method</div>
                <div class="text-white">{purge_cert.method}</div>
              </div>
              <div>
                <div class="text-slate-500">Operator</div>
                <div class="text-white">{purge_cert.operator}</div>
              </div>
            </div>

            <div class="pt-4 border-t border-slate-800">
              <div class="text-slate-500 text-sm">Verification Hash</div>
              <div class="text-white font-mono text-xs break-all mt-1">{display_hash}</div>
            </div>
          </div>
        </div>

        <div class="mt-8 text-center space-y-2">
          <p class="text-slate-400 text-sm">
            All source code data has been permanently deleted from this tool.
            Only report scores and findings have been retained.
          </p>
          <p class="text-slate-500 text-sm" lang="ja">
            &#20840;&#12390;&#12398;&#12477;&#12540;&#12473;&#12467;&#12540;&#12489;&#12487;&#12540;&#12479;&#12364;&#12371;&#12398;&#12484;&#12540;&#12523;&#12363;&#12425;&#23436;&#20840;&#12395;&#21066;&#38500;&#12373;&#12428;&#12414;&#12375;&#12383;&#12290;&#12524;&#12509;&#12540;&#12488;&#12398;&#12473;&#12467;&#12450;&#12392;&#25152;&#35211;&#12398;&#12415;&#20445;&#25345;&#12373;&#12428;&#12390;&#12356;&#12414;&#12377;&#12290;
          </p>
        </div>

        <div class="text-center mt-8">
          <a href="/dashboard/" class="text-accent hover:underline">&larr; Return to home</a>
        </div>
      </div>
    </div>
    """

    return _render_page("Purge Certificate", content)
