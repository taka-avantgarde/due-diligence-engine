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
| 🖥️ | **From your AI terminal** (Claude Code / Cursor / Copilot) | Run `dde prompt` → your IDE's AI reads the code and generates a full evaluation | Free (no API keys) |
| 🌐 | **From the Web dashboard** | Paste a GitHub URL → Multi-AI (Claude + Gemini + ChatGPT) cross-verification | Free with BYOK |

> **Which should I use?** If you already have an AI-powered IDE, `dde prompt` is the fastest path — zero setup, zero cost. The Web dashboard is ideal when you want multi-provider cross-verification or a shareable report.

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

**Fastest way** — in your AI terminal:
```bash
pip install git+https://github.com/taka-avantgarde/Due-diligence-engine.git
dde prompt owner/repo
```

**Web dashboard**: https://due-diligence-engine.web.app/dashboard/

> `dde prompt` is free (no API keys). For AI-powered cross-verification, use `dde analyze` with your own API keys — **BYOK (Bring Your Own Key)**: Claude, Gemini, and/or ChatGPT.

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-AI Cross-Verification** | Claude + Gemini + ChatGPT evaluate independently, then cross-verify |
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
# Generate evaluation prompt for your IDE AI (no API keys needed)
dde prompt .
dde prompt owner/repo --lang ja --stage seed

# Full analysis with AI APIs (BYOK)
dde analyze https://github.com/some-startup/their-product

# Local-only heuristic analysis (free, no AI)
dde analyze some-startup/repo --skip-ai
```

### Web Dashboard

```bash
dde serve
# Open http://localhost:8000/dashboard/
```

---

## Use from Your AI Terminal (Claude Code, Cursor, etc.)

Already using AI in your IDE? Run `dde prompt` to generate a structured evaluation prompt — then let **your IDE's AI** analyze it. No API keys needed.

### 1. Setup (one-time)

```bash
pip install git+https://github.com/taka-avantgarde/Due-diligence-engine.git
```

### 2. Generate Prompt & Evaluate

```bash
# Generate an evaluation prompt for your project
dde prompt .

# Or for any public GitHub repo
dde prompt owner/repo

# Japanese output with startup stage context
dde prompt owner/repo --lang ja --stage seed

# Save to file or copy to clipboard
dde prompt . -o prompt.md
dde prompt . --copy
```

### 3. Paste into Your AI Terminal

Just paste the generated prompt into Claude Code, Cursor, Copilot, or any AI terminal.
The AI will read your codebase, evaluate all 6 dimensions, and generate a full report with:

- **Status bar scoring** — visual 100-point evaluation per dimension
- **Plain-language explanations** — no engineering jargon, readable by non-technical investors
- **Strengths & what they enable** — "Because of X, users can do Y"
- **Improvements** — "If you do X, Y becomes possible"
- **Service site cross-validation** — paste a URL to check if claims match code
- **Investor questions** — ready-to-use questions for startup meetings

### How It Works

```
┌──────────────────────────────────────────────────────────┐
│  Your IDE (VS Code / JetBrains / etc.)                   │
│                                                          │
│  ┌──────────────────────────────────┐                    │
│  │  AI Terminal                     │                    │
│  │  (Claude Code / Cursor / etc.)   │                    │
│  │                                  │                    │
│  │  $ dde prompt .                  │  ┌──────────────┐  │
│  │      ↓                           │  │ DDE Engine   │  │
│  │  Heuristic data collected ───────┼─▶│ (local, no   │  │
│  │  + evaluation instructions       │  │  AI API)     │  │
│  │      ↓                           │  └──────────────┘  │
│  │  AI reads prompt + codebase      │                    │
│  │      ↓                           │                    │
│  │  Full evaluation report with     │                    │
│  │  scores, strengths, questions    │                    │
│  └──────────────────────────────────┘                    │
│                                                          │
│  Cost: $0 extra — uses your existing AI subscription     │
└──────────────────────────────────────────────────────────┘
```

> **Zero additional cost** — `dde prompt` runs entirely locally (no AI API calls). The evaluation is performed by your IDE's existing AI subscription. BYOK (Bring Your Own Key) is also supported via `dde analyze` for direct API-based analysis.

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
| `dde prompt` | Free | IDE AI evaluates — zero API keys needed |
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

[Apache License 2.0](LICENSE)

---

<div align="center">

**Powered by Claude (Anthropic) + Gemini (Google) + ChatGPT (OpenAI)**

</div>
