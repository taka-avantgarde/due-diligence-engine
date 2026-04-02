<div align="center">

# Due Diligence Engine

**Your IDE's AI Becomes a Due Diligence Analyst.**

Run `dde prompt` in your terminal — Claude Code, Cursor, or Copilot reads the codebase and generates a full investment-grade evaluation. Zero API keys. Zero extra cost.

For deeper analysis, DDE also runs Claude, Gemini, and ChatGPT **in parallel** — cross-verifying to produce a bias-resistant score.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![AI](https://img.shields.io/badge/AI-Claude_%7C_Gemini_%7C_ChatGPT-orange.svg)](https://github.com/taka-avantgarde/due-diligence-engine)
[![IDE](https://img.shields.io/badge/IDE_AI-Claude_Code_%7C_Cursor_%7C_Copilot-blueviolet.svg)](https://github.com/taka-avantgarde/due-diligence-engine)

[English](README.md) | [日本語](README.ja.md)

</div>

---

## Two Ways to Use DDE

| | Method | What It Does | Cost |
|---|--------|-------------|------|
| 🖥️ | **From your AI terminal** (Claude Code / Cursor / Copilot) | Run `dde prompt --pdf` → AI reads the code, evaluates it, and generates a consulting-grade PDF automatically | Free (no API keys) |
| 🌐 | **From the Web dashboard** | Paste a GitHub URL → Multi-AI (Claude + Gemini + ChatGPT) cross-verification | Free with BYOK |

> **Which should I use?** If you already have an AI-powered IDE, `dde prompt --pdf` is the fastest path — zero setup, zero cost, PDF delivered locally. The Web dashboard is ideal when you want multi-provider cross-verification or a shareable report.

---

## Multi-AI Cross-Verification

```
         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │   Claude     │  │   Gemini    │  │  ChatGPT    │
         │  (Anthropic) │  │  (Google)   │  │  (OpenAI)   │
         └──────┬───────┘  └──────┬──────┘  └──────┬──────┘
                │                 │                 │
                └────────┬────────┴────────┬────────┘
                   ┌─────▼─────────────────▼─────┐
                   │   Cross-Verification Engine  │
                   └──────────────┬───────────────┘
                         ┌────────▼────────┐
                         │  Unified Score   │
                         │  6-Dimension     │
                         └─────────────────┘
```

---

## Try It Now

**Fastest way** — in your AI terminal (Claude Code, Cursor, etc.):
```bash
pip install --no-cache-dir git+https://github.com/taka-avantgarde/Due-diligence-engine.git
dde prompt --pdf
```

That's it. You'll be prompted to select a language (1: English, 2: 日本語) before analysis begins. The AI reads your codebase, evaluates it as a world-class consultant, and generates a PDF — all automatically.

```bash
# Or specify a GitHub repo
dde prompt owner/repo --pdf --lang ja
```

**Web dashboard**: https://due-diligence-engine.web.app/dashboard/

> `dde prompt` is free (no API keys). `--pdf` mode produces a consulting-grade PDF via your IDE's AI. For multi-provider cross-verification, use `dde analyze` with your own API keys — **BYOK (Bring Your Own Key)**: Claude, Gemini, and/or ChatGPT.

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-AI Cross-Verification** | Claude + Gemini + ChatGPT evaluate independently, then cross-verify |
| **`dde prompt --pdf` — Consulting PDF** | AI reads codebase → SWOT, scoring, future outlook, investment thesis → PDF generated automatically. Zero API keys |
| **`dde prompt` — IDE AI Integration** | Generate structured prompts for Claude Code / Cursor / Copilot. Zero API keys needed |
| **BYOK (Bring Your Own Key)** | Use your own API keys — Claude, Gemini, or ChatGPT. 1 provider or all 3. No vendor lock-in |
| **Plain-Language Glossary** | All technical terms annotated for non-technical investors ("Translation Device" mode) |
| **Match Rate Visualization** | Claims vs. code reality — status bar shows how honest the team is |
| **GitHub Private Repo Access** | PAT-based access — startups grant temporary read-only access |
| **AI-Washing Detection** | Detect thin API wrappers disguised as "proprietary AI" |
| **Git Forensics** | Analyze commit history for suspicious patterns (rush commits before DD) |
| **10-Level Tech Rating** | Each dimension rated Lv.1–10 with clear criteria |
| **Stage-Aware Evaluation** | Seed / Series A / Series B / Growth — criteria adjust to startup stage |
| **PDF Export** | Professional investment committee-ready PDF reports |
| **Disconnect & Purge** | One-click data erasure + purge certificate |
| **Bilingual** | English / 日本語 — CLI (`--lang`) and dashboard |

---

## Scoring Framework

### Final Score Formula

```
Final Score = Heuristic (30%) + AI Average (70%)
```

### Score Barometer

```
  0          40          60          75          90        100
  |----------|-----------|-----------|-----------|----------|
  F          D           C           B           A
  Do Not    High Risk   Concerns    Viable      Strong
  Invest               Noted      w/Conditions Candidate
```

| Score | Grade | Recommendation |
|-------|-------|----------------|
| 90–100 | 🏆 **A** | Strong investment candidate |
| 75–89  | ✅ **B** | Viable with conditions |
| 60–74  | ⚡ **C** | Significant concerns — review required |
| 40–59  | ⚠️ **D** | High risk |
| 0–39   | 🚫 **F** | Do not invest |

---

### 6 Dimensions

| Dimension | Weight | What It Detects |
|-----------|--------|----------------|
| Technical Originality | 25% | API wrapper vs. genuine IP |
| Technology Advancement | 20% | Stack modernity |
| Implementation Depth | 20% | PoC vs. production |
| Architecture Quality | 15% | Structure quality |
| Claim Consistency | 10% | Pitch vs. reality |
| Security Posture | 10% | Security maturity |

---

### 10-Level Tech Rating

Each dimension is rated on a **Lv.1–10** scale with explicit criteria:

```
Lv.1 ──── Lv.2 ──── Lv.3 ──── Lv.4 ──── Lv.5 ──── Lv.6 ──── Lv.7 ──── Lv.8 ──── Lv.9 ──── Lv.10
 ▓          ▓▓         ▓▓▓        ▓▓▓▓       ▓▓▓▓▓      ▓▓▓▓▓▓     ▓▓▓▓▓▓▓    ▓▓▓▓▓▓▓▓   ▓▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓▓▓
Worst                                       Baseline                                                  Best
```

| Level | Technical Originality | Implementation Depth | Architecture Quality |
|-------|-----------------------|---------------------|---------------------|
| Lv.1  | Pure copy / no original code | UI mockup only | Spaghetti code |
| Lv.3  | Multi-API glue logic | Working prototype | Basic layering |
| Lv.5  | Extended framework + partial IP | Beta — basic tests | Clean separation |
| Lv.7  | Core tech fully original | Production-grade + monitoring | Microservices |
| Lv.10 | Frontier / world-first | Mission-critical, DR complete | Distributed systems |

---

### Example Output — "NeuralPay" (Fintech AI startup)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DUE DILIGENCE ENGINE  ·  NeuralPay / neuralpay/core-api
  Analyzed by: Claude + Gemini + ChatGPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OVERALL SCORE                          GRADE
  ┌────────────────────────────┐         ┌───────┐
  │  ████████████████░░░░  78  │         │   B   │
  └────────────────────────────┘         └───────┘
  ▲ Viable with conditions

  Score Barometer:
  0          40          60         [75]        90        100
  |----------|-----------|-----------|----●------|----------|
  F          D           C           B           A
                                     ^here

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  6-DIMENSION BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Technical Originality   (25%)   Lv.7 / 10
  ████████████████████░░░░░░░░░░  72   ← Custom ML model, not a wrapper

  Technology Advancement  (20%)   Lv.8 / 10
  ████████████████████████░░░░░░  84   ← Rust + TypeScript, modern stack

  Implementation Depth    (20%)   Lv.6 / 10
  ██████████████████░░░░░░░░░░░░  61   ← Beta-level; tests present but thin

  Architecture Quality    (15%)   Lv.7 / 10
  ████████████████████░░░░░░░░░░  73   ← Clean micro-services, some gaps

  Claim Consistency       (10%)   Lv.5 / 10
  ██████████████░░░░░░░░░░░░░░░░  54   ⚠ "SOC2" claimed, no evidence in code

  Security Posture        (10%)   Lv.6 / 10
  ██████████████████░░░░░░░░░░░░  62   ← TLS everywhere, but no pen-test docs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AI PROVIDER SCORES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Claude   (Anthropic)  ████████████████████░░░░░░  80
  Gemini   (Google)     ███████████████████░░░░░░░░  77
  ChatGPT  (OpenAI)     ████████████████████░░░░░░░  79
  ─────────────────────────────────────────────────────
  AI Consensus                                    78.7  ✓ High agreement

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RED FLAGS (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⚠️  [MEDIUM] Compliance claim mismatch
      Pitch deck: "SOC2 Type II certified"
      Codebase:   No audit logs, no compliance tooling found

  ⚠️  [LOW]    Git forensics: 40% of commits in final 2 weeks before DD
      Pattern suggests rushed cleanup prior to investor review

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ B — Viable with conditions
  Technology stack and core ML model are genuinely original.
  Resolve SOC2 claim discrepancy and address test coverage
  before proceeding to term sheet.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Quick Start

```bash
git clone https://github.com/taka-avantgarde/due-diligence-engine.git
cd due-diligence-engine
pip install -e .
```

### Configuration

```bash
# AI Providers (configure 1, 2, or all 3)
export ANTHROPIC_API_KEY="sk-ant-..."     # Claude
export GOOGLE_AI_API_KEY="AIza..."        # Gemini
export OPENAI_API_KEY="sk-..."            # ChatGPT

# Optional: GitHub OAuth for private repo access
export GITHUB_CLIENT_ID="your-github-oauth-app-id"
export GITHUB_CLIENT_SECRET="your-github-oauth-app-secret"
```

### CLI Usage

```bash
# Generate consulting-grade PDF (in AI terminal — Claude Code, Cursor, etc.)
dde prompt --pdf                                    # Current directory
dde prompt --pdf --lang ja                          # Japanese PDF
dde prompt owner/repo --pdf --lang ja --stage seed  # GitHub repo

# Generate evaluation prompt only (no PDF)
dde prompt
dde prompt owner/repo --lang ja --stage seed

# Full analysis with AI APIs (BYOK)
dde analyze https://github.com/some-startup/their-product

# Local-only heuristic analysis (free, no AI)
dde analyze some-startup/repo --skip-ai

# Generate PDF from AI evaluation JSON (used internally by --pdf mode)
dde report --consulting result.json --pdf --lang ja
```

### Web Dashboard

```bash
dde serve
# Open http://localhost:8000/dashboard/
```

---

## Use from Your AI Terminal (Claude Code, Cursor, etc.)

### One-Command PDF Generation

```bash
pip install --no-cache-dir git+https://github.com/taka-avantgarde/Due-diligence-engine.git
dde prompt --pdf --lang ja
```

Analyzes the current directory by default. Or specify a repo: `dde prompt owner/repo --pdf`

The AI autonomously:
1. Reads the codebase
2. Evaluates as a world-class technology consultant
3. Generates a consulting-grade PDF to `~/Downloads/`

No API keys. Language selection prompted first (1/2). Then tool-consent prompts from your IDE — that's all.

**Output:** `~/Downloads/dde_consulting_<project>_<date>.pdf`
- English: `dde_consulting_NeuralPay_2026-04-02.pdf`
- Japanese: `dde_consulting_NeuralPay_2026年04月02日.pdf`

### What's in the PDF

| Page | Section | Content |
|------|---------|---------|
| 1 | **Cover** | Project name, overall score, grade badge |
| 2 | **Score Dashboard** | Overall score (large) + 6-dimension horizontal bar chart with evaluation criteria descriptions + score barometer (F→A) |
| 3 | **Business Summary** | Executive summary readable by non-engineers, with investment grade badge + AI model attribution |
| 4 | **SWOT Analysis** | Strengths, Weaknesses, Opportunities, Threats — evidence-based, with business analogies |
| 5 | **Score Breakdown** | Detailed 6-dimension table with rationale, business explanation, and what each score enables |
| 6 | **Tech Level Assessment** | Visual gauge bar (Lv.1-10) with plain-language explanation |
| 7 | **Future Outlook** | Product vision + 1/3/5-year projections with confidence levels and milestones |
| 8 | **Strategic Advice** | Immediate actions, medium-term priorities, long-term vision |
| 9 | **Investment Thesis** | Recommendation with risks, upside potential, and comparable companies |
| 10 | **Red Flags** | Severity-rated issues with business impact |
| 11 | **Glossary** | All technical terms annotated for non-technical readers |

### Prompt-Only Mode (no PDF)

If you prefer text output instead of PDF, omit `--pdf`:

```bash
dde prompt owner/repo --lang ja

# Save to file or copy to clipboard
dde prompt . -o prompt.md
dde prompt . --copy
```

### How `--pdf` Mode Works

```
┌──────────────────────────────────────────────────────────┐
│  Your IDE (VS Code / JetBrains / etc.)                   │
│                                                          │
│  ┌──────────────────────────────────┐                    │
│  │  AI Terminal                     │                    │
│  │  (Claude Code / Cursor / etc.)   │                    │
│  │                                  │                    │
│  │  $ dde prompt --pdf              │  ┌──────────────┐  │
│  │      ↓                           │  │ DDE Engine   │  │
│  │  1. Heuristic data collected ────┼─▶│ (local, no   │  │
│  │     + JSON schema + instructions │  │  AI API)     │  │
│  │      ↓                           │  └──────────────┘  │
│  │  2. AI reads code + evaluates    │                    │
│  │      ↓                           │                    │
│  │  3. AI saves JSON + runs:        │                    │
│  │     dde report --consulting ─────┼─▶ PDF generated   │
│  │      ↓                           │                    │
│  │  4. PDF file path shown          │                    │
│  └──────────────────────────────────┘                    │
│                                                          │
│  Cost: $0 extra — uses your existing AI subscription     │
└──────────────────────────────────────────────────────────┘
```

> **Zero additional cost** — `dde prompt` runs entirely locally (no AI API calls). The evaluation is performed by your IDE's existing AI subscription. `--pdf` mode instructs the AI to generate a structured JSON evaluation, then calls `dde report --consulting` to produce a professional PDF. BYOK is also supported via `dde analyze` for direct API-based analysis.

---

## Private Repository Access (PAT)

For private repos, provide a **GitHub Personal Access Token**:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → check **`repo`** scope → set 7-day expiration
3. Copy the token (`ghp_...`) and paste it into the dashboard

**Security:** PAT is used once in-memory for `git clone`, then immediately discarded. Never stored.

---


## Data Security

| Guarantee | Implementation |
|-----------|---------------|
| No cloud storage | All data processed in encrypted tmpfs |
| No raw code in reports | PDF contains findings only, never source code |
| Cryptographic erasure | 3-pass random overwrite + purge certificate |
| API 0-day retention | Anthropic / Google / OpenAI API calls — no data retention |

---

## Deployment

| Option | Cost | Description |
|--------|------|-------------|
| `dde prompt --pdf` | Free | IDE AI evaluates + generates consulting PDF — zero API keys |
| `dde prompt` | Free | IDE AI evaluates (text output) — zero API keys |
| Local CLI | Free | `dde analyze owner/repo --skip-ai` |
| BYOK CLI | Free + API costs | Your own API keys, full AI analysis |
| BYOK Dashboard | Free + API costs | Web UI with GitHub PAT support |

---

## Roadmap

- [x] Multi-AI analysis engine (Claude / Gemini / ChatGPT BYOK)
- [x] BYOK API key input on web dashboard
- [x] Provider score comparison (per-provider breakdown)
- [x] Bilingual dashboard (English / 日本語)
- [x] PDF report export
- [x] Disconnect & Purge with certificate
- [x] `dde prompt` — IDE AI integration (Claude Code / Cursor / Copilot)
- [x] `dde prompt --pdf` — Consulting-grade PDF (SWOT, future outlook, investment thesis)
- [x] Score dashboard with horizontal bar charts and score barometer
- [x] PDF saved to `~/Downloads/` with localized date stamps (EN/JA)
- [x] Automated EN/JA PDF generation tests (13 tests)
- [x] Professional gray/dark blue color palette with Atlas Associates credit
- [x] Language selection by number (1: English, 2: 日本語) — forced before analysis
- [x] Evaluation criteria descriptions on each score bar
- [x] CID font rendering fix for Japanese tables and gauges
- [x] Plain-language glossary for non-technical readers
- [x] Match rate visualization (claims vs. code)
- [x] Stage-aware evaluation (seed / series_a / series_b / growth)
- [x] Investor question auto-generation
- [ ] Technical Debt + Maintainability axes
- [ ] Batch analysis mode (portfolio-wide DD)
- [ ] Historical tracking (re-analyze over time)

---

## Disclaimer

This tool provides **technical analysis to assist investment decisions**. It is not investment advice. Always consult qualified professionals for investment decisions.

---

## License

[Apache License 2.0](LICENSE) — Copyright 2026 Takayuki Miyano / Atlas Associates

---

<div align="center">

**Powered by Due Diligence Engine — Takayuki Miyano / Atlas Associates**

Built with Claude (Anthropic) + Gemini (Google) + ChatGPT (OpenAI)

</div>
