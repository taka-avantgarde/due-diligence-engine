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
      <div class="flex items-center gap-4">
        <button id="lang-toggle" onclick="toggleLang()" class="text-xs border border-slate-700 rounded-lg px-3 py-1 text-slate-400 hover:text-white hover:border-accent transition-all">EN / JA</button>
        <div class="text-sm text-slate-500" data-en="Technical DD for VCs" data-ja="VC&#21521;&#12369;&#25216;&#34899;DD">Technical DD for VCs</div>
      </div>
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
    """Landing page with URL search bar and language toggle."""
    # Using a completely separate HTML to avoid Python string escaping issues with JS regex
    html = _build_landing_html()
    return HTMLResponse(content=html)


def _build_landing_html() -> str:
    """Build the landing page HTML as a complete document."""
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Due Diligence Engine</title>\n'
        '<script src="https://cdn.tailwindcss.com"></script>\n'
        '<script>\n'
        'tailwind.config = { theme: { extend: { colors: { surface: "#1e293b", accent: "#38bdf8" } } } }\n'
        '</script>\n'
        '<style>body { font-family: "Inter", system-ui, -apple-system, sans-serif; }</style>\n'
        '</head>\n'
        '<body class="bg-slate-950 text-slate-200 min-h-screen">\n'
        '<nav class="border-b border-slate-800 px-6 py-4">\n'
        '  <div class="max-w-5xl mx-auto flex items-center justify-between">\n'
        '    <a href="/dashboard/" class="text-accent font-bold text-lg tracking-wide">DUE DILIGENCE ENGINE</a>\n'
        '    <div class="flex items-center gap-4">\n'
        '      <a href="https://github.com/taka-avantgarde/Due-diligence-engine" target="_blank" rel="noopener" class="text-slate-500 hover:text-white transition-all" title="GitHub Repository"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"/></svg></a>\n'
        '      <button id="lang-toggle" class="text-xs border border-slate-700 rounded-lg px-3 py-1.5 text-slate-400 hover:text-white hover:border-accent transition-all cursor-pointer">EN / JA</button>\n'
        '    </div>\n'
        '  </div>\n'
        '</nav>\n'
        '<main class="max-w-5xl mx-auto px-6 py-8">\n'
        '  <div class="flex flex-col items-center justify-center min-h-[70vh]">\n'
        '    <div class="text-center max-w-2xl w-full">\n'
        '      <h1 class="text-5xl font-bold text-white mb-3 tracking-tight">Due Diligence Engine</h1>\n'
        '      <p id="hero-sub" class="text-slate-400 text-lg mb-10" data-en="Paste a GitHub URL. Get a technology score in minutes." data-ja="GitHub URL&#12434;&#36028;&#12427;&#12384;&#12369;&#12290;&#25968;&#20998;&#12391;&#25216;&#34899;&#12473;&#12467;&#12450;&#12434;&#21462;&#24471;&#12290;">Paste a GitHub URL. Get a technology score in minutes.</p>\n'
        '      <form id="analyze-form" class="relative w-full">\n'
        '        <div class="flex items-center bg-slate-900 border-2 border-slate-700 focus-within:border-accent rounded-2xl overflow-hidden transition-all duration-300 shadow-xl shadow-black/30">\n'
        '          <div class="pl-5 text-slate-500">\n'
        '            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>\n'
        '          </div>\n'
        '          <input id="repo-url" type="text" placeholder="https://github.com/owner/repo" class="flex-1 bg-transparent text-white text-lg px-4 py-5 outline-none placeholder-slate-600" autocomplete="off" spellcheck="false" />\n'
        '          <button type="submit" id="analyze-btn" class="bg-accent hover:bg-cyan-400 text-slate-950 font-bold text-lg px-8 py-5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed" data-en="Analyze" data-ja="&#20998;&#26512;">Analyze</button>\n'
        '        </div>\n'
        '        <p id="url-hint" class="text-slate-600 text-sm mt-3 text-left pl-2" data-en="Public repos: paste URL directly. Private repos: &lt;a href=/api/github/connect?user_id=demo_user class=text-accent hover:underline&gt;connect GitHub first&lt;/a&gt;." data-ja="&#20844;&#38283;&#12522;&#12509;: URL&#12434;&#36028;&#12427;&#12384;&#12369;&#12290;Private&#12522;&#12509;: &lt;a href=/api/github/connect?user_id=demo_user class=text-accent hover:underline&gt;GitHub&#36899;&#25658;&lt;/a&gt;&#12364;&#24517;&#35201;&#12391;&#12377;&#12290;">Public repos: paste URL directly. Private repos: <a href="/api/github/connect?user_id=demo_user" class="text-accent hover:underline">connect GitHub first</a>.</p>\n'
        '      </form>\n'
        '    </div>\n'
        '    <div id="status-area" class="hidden w-full max-w-2xl mt-8">\n'
        '      <div class="bg-surface rounded-2xl border border-slate-800 p-8">\n'
        '        <div class="flex items-center gap-4 mb-6">\n'
        '          <div id="spinner" class="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>\n'
        '          <div>\n'
        '            <div id="status-text" class="text-white font-semibold">Analyzing...</div>\n'
        '            <div id="status-sub" class="text-slate-500 text-sm">This may take 1-2 minutes</div>\n'
        '          </div>\n'
        '        </div>\n'
        '        <div class="space-y-3 text-sm" id="steps">\n'
        '          <div class="flex items-center gap-3 text-slate-600"><span class="w-5 text-center">&#9675;</span><span data-en="Cloning repository" data-ja="&#12522;&#12509;&#12472;&#12488;&#12522;&#12434;&#12463;&#12525;&#12540;&#12531;&#20013;">Cloning repository</span></div>\n'
        '          <div class="flex items-center gap-3 text-slate-600"><span class="w-5 text-center">&#9675;</span><span data-en="Code structure analysis" data-ja="&#12467;&#12540;&#12489;&#27083;&#36896;&#35299;&#26512;">Code structure analysis</span></div>\n'
        '          <div class="flex items-center gap-3 text-slate-600"><span class="w-5 text-center">&#9675;</span><span data-en="Git forensics" data-ja="Git&#23653;&#27508;&#12501;&#12457;&#12524;&#12531;&#12472;&#12483;&#12463;">Git forensics</span></div>\n'
        '          <div class="flex items-center gap-3 text-slate-600"><span class="w-5 text-center">&#9675;</span><span data-en="AI analysis (Haiku &#8594; Sonnet &#8594; Opus)" data-ja="AI&#20998;&#26512; (Haiku &#8594; Sonnet &#8594; Opus)">AI analysis (Haiku &#8594; Sonnet &#8594; Opus)</span></div>\n'
        '          <div class="flex items-center gap-3 text-slate-600"><span class="w-5 text-center">&#9675;</span><span data-en="Scoring &amp; report" data-ja="&#12473;&#12467;&#12450;&#12522;&#12531;&#12464; &amp; &#12524;&#12509;&#12540;&#12488;&#29983;&#25104;">Scoring &amp; report</span></div>\n'
        '        </div>\n'
        '      </div>\n'
        '    </div>\n'
        '    <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mt-16 w-full max-w-3xl">\n'
        '      <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">\n'
        '        <div class="text-accent text-xs font-bold tracking-wider mb-2" data-en="ORIGINALITY" data-ja="&#25216;&#34899;&#29420;&#33258;&#24615;">ORIGINALITY</div>\n'
        '        <div class="text-white font-semibold text-sm mb-1">Lv.1 Copy &mdash; Lv.10 Frontier</div>\n'
        '        <p class="text-slate-500 text-xs" data-en="API wrapper or genuine IP?" data-ja="API&#12521;&#12483;&#12497;&#12540;&#12363;&#26412;&#29289;&#12398;IP&#12363;&#65311;">API wrapper or genuine IP?</p>\n'
        '      </div>\n'
        '      <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">\n'
        '        <div class="text-accent text-xs font-bold tracking-wider mb-2" data-en="ADVANCEMENT" data-ja="&#25216;&#34899;&#20808;&#36914;&#24615;">ADVANCEMENT</div>\n'
        '        <div class="text-white font-semibold text-sm mb-1">Lv.1 Legacy &mdash; Lv.10 Visionary</div>\n'
        '        <p class="text-slate-500 text-xs" data-en="How cutting-edge is the tech?" data-ja="&#25216;&#34899;&#12399;&#12393;&#12428;&#12411;&#12393;&#20808;&#36914;&#30340;&#12363;&#65311;">How cutting-edge is the tech?</p>\n'
        '      </div>\n'
        '      <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">\n'
        '        <div class="text-accent text-xs font-bold tracking-wider mb-2" data-en="IMPLEMENTATION" data-ja="&#23455;&#35013;&#28145;&#24230;">IMPLEMENTATION</div>\n'
        '        <div class="text-white font-semibold text-sm mb-1">Lv.1 Mockup &mdash; Lv.10 Mission-Critical</div>\n'
        '        <p class="text-slate-500 text-xs" data-en="PoC or production-grade?" data-ja="PoC&#12363;&#26412;&#30058;&#21697;&#36074;&#12363;&#65311;">PoC or production-grade?</p>\n'
        '      </div>\n'
        '      <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">\n'
        '        <div class="text-accent text-xs font-bold tracking-wider mb-2" data-en="ARCHITECTURE" data-ja="&#12450;&#12540;&#12461;&#12486;&#12463;&#12481;&#12515;">ARCHITECTURE</div>\n'
        '        <div class="text-white font-semibold text-sm mb-1">Lv.1 Spaghetti &mdash; Lv.10 Distributed</div>\n'
        '        <p class="text-slate-500 text-xs" data-en="Scalable design?" data-ja="&#12473;&#12465;&#12540;&#12521;&#12502;&#12523;&#12394;&#35373;&#35336;&#12363;&#65311;">Scalable design?</p>\n'
        '      </div>\n'
        '      <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">\n'
        '        <div class="text-accent text-xs font-bold tracking-wider mb-2" data-en="CONSISTENCY" data-ja="&#20027;&#24373;&#25972;&#21512;&#24615;">CONSISTENCY</div>\n'
        '        <div class="text-white font-semibold text-sm mb-1">Lv.1 Fabricated &mdash; Lv.10 Transparent</div>\n'
        '        <p class="text-slate-500 text-xs" data-en="Claims match reality?" data-ja="&#20027;&#24373;&#12392;&#29694;&#23455;&#12399;&#19968;&#33268;&#12375;&#12390;&#12356;&#12427;&#12363;&#65311;">Claims match reality?</p>\n'
        '      </div>\n'
        '      <div class="bg-surface rounded-xl p-5 border border-slate-800 hover:border-accent/30 transition-all">\n'
        '        <div class="text-accent text-xs font-bold tracking-wider mb-2" data-en="SECURITY" data-ja="&#12475;&#12461;&#12517;&#12522;&#12486;&#12451;">SECURITY</div>\n'
        '        <div class="text-white font-semibold text-sm mb-1">Lv.1 Negligent &mdash; Lv.10 Military-Grade</div>\n'
        '        <p class="text-slate-500 text-xs" data-en="Security maturity level?" data-ja="&#12475;&#12461;&#12517;&#12522;&#12486;&#12451;&#25104;&#29087;&#24230;&#12399;&#65311;">Security maturity level?</p>\n'
        '      </div>\n'
        '    </div>\n'
        '    <div class="flex flex-col sm:flex-row gap-4 mt-12">\n'
        '      <div class="bg-surface rounded-xl px-6 py-4 border border-green-900/50 text-center">\n'
        '        <div class="text-green-400 font-bold text-sm">BYOK</div>\n'
        '        <div class="text-white text-xl font-bold">FREE</div>\n'
        '        <div class="text-slate-500 text-xs" data-en="Your own API key" data-ja="&#33258;&#31038;API&#12461;&#12540;">Your own API key</div>\n'
        '      </div>\n'
        '      <div class="bg-surface rounded-xl px-6 py-4 border border-accent/30 text-center">\n'
        '        <div class="text-accent font-bold text-sm">SaaS</div>\n'
        '        <div class="text-white text-xl font-bold">2x API Cost</div>\n'
        '        <div class="text-slate-500 text-xs" data-en="We handle everything" data-ja="&#20840;&#12390;&#12362;&#20219;&#12379;">We handle everything</div>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</main>\n'
        '<footer class="border-t border-slate-800 mt-12 py-6 text-center text-xs text-slate-600">\n'
        '  CONFIDENTIAL &mdash; Due Diligence Engine v0.1.0\n'
        '</footer>\n'
        '<script>\n'
        'var currentLang = "en";\n'
        'function toggleLang() {\n'
        '  currentLang = currentLang === "en" ? "ja" : "en";\n'
        '  document.querySelectorAll("[data-" + currentLang + "]").forEach(function(el) {\n'
        '    var val = el.getAttribute("data-" + currentLang);\n'
        '    if (val.indexOf("<") >= 0) { el.innerHTML = val; } else { el.textContent = val; }\n'
        '  });\n'
        '  document.getElementById("lang-toggle").textContent = currentLang === "en" ? "EN / JA" : "JA / EN";\n'
        '  document.documentElement.lang = currentLang;\n'
        '}\n'
        'document.getElementById("lang-toggle").addEventListener("click", toggleLang);\n'
        '\n'
        'function parseUrl(raw) {\n'
        '  if (!raw) return null;\n'
        '  raw = raw.trim();\n'
        '  var idx = raw.indexOf("github.com/");\n'
        '  if (idx >= 0) {\n'
        '    var after = raw.substring(idx + 11);\n'
        '    var parts = after.split("/");\n'
        '    if (parts.length >= 2 && parts[0] && parts[1]) {\n'
        '      var repo = parts[1].replace(".git", "");\n'
        '      return parts[0] + "/" + repo;\n'
        '    }\n'
        '  }\n'
        '  var slash = raw.indexOf("/");\n'
        '  if (slash > 0 && slash < raw.length - 1 && raw.indexOf(" ") < 0 && raw.indexOf(":") < 0) {\n'
        '    return raw;\n'
        '  }\n'
        '  return null;\n'
        '}\n'
        '\n'
        'var form = document.getElementById("analyze-form");\n'
        'var inp = document.getElementById("repo-url");\n'
        'var btn = document.getElementById("analyze-btn");\n'
        'var statusArea = document.getElementById("status-area");\n'
        'var statusText = document.getElementById("status-text");\n'
        'var statusSub = document.getElementById("status-sub");\n'
        '\n'
        'form.addEventListener("submit", function(e) {\n'
        '  e.preventDefault();\n'
        '  var repo = parseUrl(inp.value);\n'
        '  if (!repo) {\n'
        '    document.getElementById("url-hint").textContent = currentLang === "ja" ? "GitHub URL\\u3092\\u5165\\u529b\\u3057\\u3066\\u304f\\u3060\\u3055\\u3044 (\\u4f8b: https://github.com/owner/repo)" : "Please enter a valid GitHub URL (e.g., https://github.com/owner/repo)";\n'
        '    document.getElementById("url-hint").style.color = "#f87171";\n'
        '    return;\n'
        '  }\n'
        '  btn.disabled = true;\n'
        '  btn.textContent = currentLang === "ja" ? "\\u5206\\u6790\\u4e2d..." : "Analyzing...";\n'
        '  inp.disabled = true;\n'
        '  statusArea.style.display = "block";\n'
        '  statusArea.classList.remove("hidden");\n'
        '  statusText.textContent = currentLang === "ja" ? "\\u30ea\\u30dd\\u30b8\\u30c8\\u30ea\\u3092\\u30af\\u30ed\\u30fc\\u30f3\\u4e2d..." : "Cloning repository...";\n'
        '\n'
        '  fetch("/api/v1/analyze/url", {\n'
        '    method: "POST",\n'
        '    headers: {"Content-Type": "application/json"},\n'
        '    body: JSON.stringify({repo_url: repo})\n'
        '  }).then(function(resp) {\n'
        '    if (resp.ok) return resp.json();\n'
        '    return resp.json().then(function(err) { throw new Error(err.detail || "Analysis failed"); });\n'
        '  }).then(function(data) {\n'
        '    window.location.href = "/dashboard/analysis/" + data.analysis_id + "?lang=" + currentLang;\n'
        '  }).catch(function(err) {\n'
        '    statusText.textContent = "Error: " + err.message;\n'
        '    statusSub.textContent = currentLang === "ja" ? "\\u3082\\u3046\\u4e00\\u5ea6\\u304a\\u8a66\\u3057\\u304f\\u3060\\u3055\\u3044" : "Please try again.";\n'
        '    btn.disabled = false;\n'
        '    btn.textContent = currentLang === "ja" ? "\\u5206\\u6790" : "Analyze";\n'
        '    inp.disabled = false;\n'
        '  });\n'
        '});\n'
        '\n'
        'inp.focus();\n'
        '</script>\n'
        '</body>\n'
        '</html>\n'
    )


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

# i18n strings for results page
_I18N = {
    "en": {
        "analysis_results": "Analysis Results",
        "analysis_not_found": "Analysis Not Found",
        "not_found_desc": "The requested analysis could not be found.",
        "return_home": "Return to home",
        "score_breakdown": "Score Breakdown",
        "dimension": "Dimension",
        "score": "Score",
        "weight": "Weight",
        "bar": "Bar",
        "tech_level_details": "Technology Level Details",
        "show_all_levels": "Show all 10 levels",
        "red_flags": "Red Flags",
        "export_pdf": "Export PDF",
        "disconnect_purge": "Disconnect &amp; Purge",
        "code_summary": "Code Analysis Summary",
        "git_summary": "Git Forensics Summary",
        "analysis_cost": "Analysis Cost",
        "total_api_cost": "Total API Cost",
        "files": "Files",
        "lines": "Lines of Code",
        "languages": "Languages",
        "wrapper_ratio": "API Wrapper Ratio",
        "tests": "Tests",
        "cicd": "CI/CD",
        "docs": "Documentation",
        "deps": "Dependencies",
        "commits": "Total Commits",
        "authors": "Unique Authors",
        "first_commit": "First Commit",
        "last_commit": "Last Commit",
        "rush_ratio": "Rush Commit Ratio",
        "yes": "Yes",
        "no": "No",
        "analyzing": "Analyzing...",
        "analysis_in_progress": "Analysis in Progress",
        "running_pipeline": "Running AI-powered due diligence pipeline...",
    },
    "ja": {
        "analysis_results": "分析結果",
        "analysis_not_found": "分析が見つかりません",
        "not_found_desc": "リクエストされた分析は見つかりませんでした。",
        "return_home": "ホームに戻る",
        "score_breakdown": "スコア内訳",
        "dimension": "評価軸",
        "score": "スコア",
        "weight": "重み",
        "bar": "バー",
        "tech_level_details": "技術レベル詳細",
        "show_all_levels": "全10段階を表示",
        "red_flags": "レッドフラグ",
        "export_pdf": "PDF出力",
        "disconnect_purge": "切断 &amp; 破棄",
        "code_summary": "コード分析サマリ",
        "git_summary": "Git履歴フォレンジック",
        "analysis_cost": "分析コスト",
        "total_api_cost": "API合計コスト",
        "files": "ファイル数",
        "lines": "コード行数",
        "languages": "言語",
        "wrapper_ratio": "APIラッパー率",
        "tests": "テスト",
        "cicd": "CI/CD",
        "docs": "ドキュメント",
        "deps": "依存関係",
        "commits": "コミット数",
        "authors": "著者数",
        "first_commit": "初回コミット",
        "last_commit": "最終コミット",
        "rush_ratio": "急造コミット率",
        "yes": "あり",
        "no": "なし",
        "analyzing": "分析中...",
        "analysis_in_progress": "分析を実行中",
        "running_pipeline": "AIデューデリジェンスパイプラインを実行中...",
    },
}

# Grade recommendations in both languages
_GRADE_REC = {
    "en": {
        "A": "Strong investment candidate. Proceed with standard terms.",
        "B": "Viable with conditions. Address flagged items before closing.",
        "C": "Significant concerns. Require remediation plan with milestones.",
        "D": "High risk. Consider pass or heavily discounted terms.",
        "F": "Do not invest. Fundamental issues detected.",
    },
    "ja": {
        "A": "有力な投資候補。標準条件で進行可能。",
        "B": "条件付きで投資可能。指摘事項の対応を確認。",
        "C": "重要な懸念あり。改善計画の提出を要求。",
        "D": "高リスク。見送りまたは大幅な条件変更を検討。",
        "F": "投資不可。根本的な問題を検出。",
    },
}


@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def analysis_page(
    analysis_id: str,
    lang: str = Query(default="en", description="Language: en or ja"),
) -> HTMLResponse:
    """Show analysis progress or completed results."""
    if lang not in ("en", "ja"):
        lang = "en"
    t = _I18N[lang]
    data = get_analysis(analysis_id)

    if data is None:
        content = f"""
        <div class="text-center py-20">
          <h1 class="text-2xl font-bold text-red-400 mb-4">{t['analysis_not_found']}</h1>
          <p class="text-slate-500">{t['not_found_desc']}</p>
          <a href="/dashboard/" class="text-accent hover:underline mt-4 inline-block">{t['return_home']}</a>
        </div>
        """
        return _render_page("Not Found", content)

    status = data.get("status", "unknown")

    if status == "running":
        return _render_progress_page(analysis_id, lang)
    elif status == "completed":
        return _render_results_page(analysis_id, data, lang)
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


def _render_progress_page(analysis_id: str, lang: str = "en") -> HTMLResponse:
    """Render the analysis in-progress page with auto-refresh."""
    t = _I18N.get(lang, _I18N["en"])
    content = f"""
    <div class="flex flex-col items-center justify-center min-h-[50vh]">
      <div class="text-center">
        <div class="w-16 h-16 border-4 border-accent border-t-transparent rounded-full
                    animate-spin mx-auto mb-8"></div>
        <h1 class="text-2xl font-bold text-white mb-4">{t['analysis_in_progress']}</h1>
        <p class="text-slate-400 mb-2">{t['running_pipeline']}</p>
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


def _render_results_page(analysis_id: str, data: dict[str, Any], lang: str = "en") -> HTMLResponse:
    """Render the completed analysis results page."""
    t = _I18N.get(lang, _I18N["en"])
    rec = _GRADE_REC.get(lang, _GRADE_REC["en"])
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
        recommendation = rec.get(grade, score.recommendation)

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
        # Map English dimension names to Japanese
        _dim_ja = {
            "Technical Originality": "技術独自性",
            "Technology Advancement": "技術先進性",
            "Implementation Depth": "実装深度",
            "Architecture Quality": "アーキテクチャ品質",
            "Claim Consistency": "主張整合性",
            "Security Posture": "セキュリティ態勢",
        }
        dims_rows = ""
        for dim in score.dimensions:
            dim_display = _dim_ja.get(dim.name, dim.name) if lang == "ja" else dim.name
            bar_color = "bg-green-500" if dim.score >= 70 else "bg-yellow-500" if dim.score >= 40 else "bg-red-500"
            dims_rows += f"""
            <tr class="border-b border-slate-800">
              <td class="py-3 font-medium text-white">{dim_display}</td>
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
          <h2 class="text-lg font-semibold text-accent mb-4">{t['score_breakdown']}</h2>
          <table class="w-full">
            <thead>
              <tr class="text-xs text-accent uppercase tracking-wider">
                <th class="text-left py-2">{t['dimension']}</th>
                <th class="text-center py-2">{t['score']}</th>
                <th class="text-center py-2">{t['weight']}</th>
                <th class="text-left py-2" style="width: 40%">{t['bar']}</th>
              </tr>
            </thead>
            <tbody>{dims_rows}</tbody>
          </table>
        </div>
        """

        # Tech Level Ratings detail
        if score.tech_ratings:
            ratings_html = ""
            for rating in score.tech_ratings:
                level_bars = ""
                for lvl in rating.criteria:
                    is_current = lvl.level == rating.level
                    bg = "bg-accent" if is_current else "bg-slate-800"
                    text_color = "text-white font-bold" if is_current else "text-slate-600"
                    border = "border border-accent" if is_current else "border border-slate-700/50"
                    indicator = " &larr;" if is_current else ""
                    level_bars += f"""
                    <div class="{bg} {border} rounded-lg px-3 py-2 text-xs {text_color}">
                      <span class="font-mono">Lv.{lvl.level}</span> {lvl.label.split(' — ')[-1] if ' — ' in lvl.label else ''}
                      <span class="block text-[10px] opacity-70 mt-0.5">{lvl.description}</span>
                      {f'<span class="text-accent">{indicator}</span>' if is_current else ''}
                    </div>
                    """

                dim_name_ja = rating.dimension_ja or rating.dimension
                dim_primary = dim_name_ja if lang == "ja" else rating.dimension
                dim_secondary = rating.dimension if lang == "ja" else dim_name_ja
                ratings_html += f"""
                <div class="bg-surface rounded-xl p-5 border border-slate-800 mb-4">
                  <div class="flex items-center justify-between mb-3">
                    <div>
                      <h3 class="font-semibold text-white">{dim_primary}</h3>
                      <span class="text-slate-500 text-xs">{dim_secondary}</span>
                    </div>
                    <div class="text-right">
                      <span class="text-2xl font-bold text-accent">Lv.{rating.level}</span>
                      <span class="text-slate-500 text-xs block">/10</span>
                    </div>
                  </div>
                  <div class="bg-slate-900 rounded-lg p-3 mb-3">
                    <p class="text-sm text-slate-300">{rating.label}</p>
                    <p class="text-xs text-slate-500 mt-1">{rating.description}</p>
                  </div>
                  <details class="group">
                    <summary class="text-xs text-slate-500 cursor-pointer hover:text-accent transition-colors">
                      {t['show_all_levels']} &darr;
                    </summary>
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-2 mt-3">
                      {level_bars}
                    </div>
                  </details>
                </div>
                """

            score_html += f"""
            <div class="mb-6">
              <h2 class="text-lg font-semibold text-accent mb-4">{t['tech_level_details']}</h2>
              {ratings_html}
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
        {t['export_pdf']}
      </a>

      <button onclick="showDisconnectModal()"
              class="inline-flex items-center justify-center gap-2 bg-red-900/50 hover:bg-red-800
                     text-red-300 font-semibold px-6 py-3 rounded-xl
                     border border-red-800 hover:border-red-600 transition-colors duration-200">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
        </svg>
        {t['disconnect_purge']}
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
      <h1 class="text-2xl font-bold text-white mb-1">{t['analysis_results']}</h1>
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
