<div align="center">

# Due Diligence Engine

**3 AIs Cross-Validate. One Verdict You Can Trust.**

Why rely on a single AI's opinion? DDE runs Claude, Gemini, and ChatGPT **in parallel** — each evaluates independently, then cross-verifies to produce a unified, bias-resistant investment score.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![AI](https://img.shields.io/badge/AI-Claude_%7C_Gemini_%7C_ChatGPT-orange.svg)](https://github.com/taka-avantgarde/due-diligence-engine)

[English](README.md) | [日本語](README.ja.md)

</div>

---

## Multi-AI Cross-Verification + Site Credibility Analysis

> **One AI can be wrong. Three AIs cross-checking each other dramatically reduce blind spots.**
> **Now with Site vs Code cross-validation — detect exaggerations before they cost you.**

```
         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │   Claude     │  │   Gemini    │  │  ChatGPT    │
         │  (Anthropic) │  │  (Google)   │  │  (OpenAI)   │
         └──────┬───────┘  └──────┬──────┘  └──────┬──────┘
                │                 │                 │
                └────────┬────────┴────────┬────────┘
                   ┌─────▼─────────────────▼─────┐
                   │   Cross-Verification Engine  │
                   │   + Site Credibility Check   │
                   └──────────────┬───────────────┘
                         ┌────────▼────────┐
                         │  Unified Score   │
                         │  + Credibility   │
                         └─────────────────┘
```

---

## Try It Now

**https://due-diligence-engine.web.app/dashboard/**

Paste any public GitHub URL and click Analyze. Optionally add a product website URL for cross-validation.

> Basic analysis (local code scan) is free. For AI-powered analysis, configure your own API keys (BYOK) or use Pro Analysis.

---

## Pricing

| Plan | Cost | AI Providers | Features |
|------|------|-------------|----------|
| **Free (Local Only)** | Free | None | Code structure, git forensics, dependency scan |
| **BYOK** | Free (API costs billed to you) | Claude / Gemini / ChatGPT (1-3 providers) | Full AI analysis + cross-verification |
| **Pro Analysis (Japan)** | **¥3,000 / company** | Claude + Gemini (managed) | AI auto-report + real-time online meeting support |

> **BYOK:** One API key is enough to start. Add more providers for cross-verification. Typical cost: ~$10-15/analysis depending on codebase size.
>
> **Pro Analysis (日本のみ):** 1社¥3,000で自動レポート生成 + オンライン会議でリアルタイムサポート。お気軽にお問い合わせください。
>
> **[Atlas Associates](https://www.atlasassociates.io/)** — support@atlasassociates.io

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-AI Cross-Verification** | Claude + Gemini + ChatGPT evaluate independently, then cross-verify |
| **Site vs Code Cross-Validation** | Scrape product website → extract claims → verify against actual source code |
| **Credibility Score** | 0-100 score measuring how truthful a startup's site claims are vs their code |
| **Exaggeration Detection** | Flag unrealistic performance claims, buzzword density, missing tech evidence |
| **BYOK (Bring Your Own Key)** | Use your own API keys — 1 provider or all 3. No vendor lock-in |
| **GitHub Private Repo Access** | PAT-based access — startups grant temporary read-only access |
| **AI-Washing Detection** | Detect thin API wrappers disguised as "proprietary AI" |
| **Git Forensics** | Analyze commit history for suspicious patterns (rush commits before DD) |
| **10-Level Tech Rating** | Each dimension rated Lv.1-10 with clear criteria |
| **PDF Export** | Professional investment committee-ready PDF reports |
| **Disconnect & Purge** | One-click data erasure + purge certificate |
| **Pro Analysis Service** | ¥3,000/company with real-time online meeting support (Japan only) |
| **Bilingual Dashboard** | English / 日本語 toggle |

---

## Scoring Framework

### 6 Dimensions

| Dimension | Weight | What It Detects |
|-----------|--------|----------------|
| Technical Originality | 25% | API wrapper vs. genuine IP |
| Technology Advancement | 20% | Stack modernity |
| Implementation Depth | 20% | PoC vs. production |
| Architecture Quality | 15% | Structure quality |
| Claim Consistency | 10% | Pitch vs. reality |
| Security Posture | 10% | Security maturity |

### Final Score

```
Final Score = Heuristic (30%) + AI Average (70%)
```

| Score | Grade | Recommendation |
|-------|-------|---------------|
| 90-100 | A | Strong investment candidate |
| 75-89 | B | Viable with conditions |
| 60-74 | C | Significant concerns |
| 40-59 | D | High risk |
| 0-39 | F | Do not invest |

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

# Optional: for managed Pro Analysis service
export STRIPE_API_KEY="sk_live_..."
```

### CLI Usage

```bash
# Analyze from GitHub URL
dde analyze https://github.com/some-startup/their-product

# Local-only (free, no AI)
dde analyze some-startup/repo --skip-ai
```

### Web Dashboard

```bash
dde serve
# Open http://localhost:8000/dashboard/
```

---

## Private Repository Access (PAT)

For private repos, provide a **GitHub Personal Access Token**:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → check **`repo`** scope → set 7-day expiration
3. Copy the token (`ghp_...`) and paste it into the dashboard

**Security:** PAT is used once in-memory for `git clone`, then immediately discarded. Never stored.

---

## Site Cross-Validation (NEW)

Add a product/service URL alongside the GitHub repo to enable credibility analysis:

1. **Crawl** — DDE scrapes up to 10 pages (about, team, pricing, features, etc.)
2. **Extract Claims** — Technology, performance, traction, security, and funding claims
3. **Cross-Validate** — Compare site claims against actual source code
4. **Score** — Generate a Credibility Score (0-100) with verified/unverified/contradicted claims

### What It Detects

- **Technology mismatches** — "We use React + ML" but codebase is Python-only with no ML code
- **Security claim contradictions** — "E2EE encrypted" but no encryption code found
- **Exaggerated performance** — "1000x faster" claims without benchmarks
- **Buzzword inflation** — Excessive marketing buzzwords vs. thin technical substance
- **Missing evidence** — Many tech claims but no documentation, tests, or CI/CD

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
| Local CLI | Free | `dde analyze owner/repo --skip-ai` |
| BYOK CLI | Free + API costs | Your own API keys, full AI analysis |
| BYOK Dashboard | Free + API costs | Web UI with GitHub PAT support |
| Pro Analysis (Japan) | ¥3,000/company | Managed AI analysis + online meeting support |

---

## Roadmap

- [x] Multi-AI analysis engine (Claude / Gemini / ChatGPT BYOK)
- [x] BYOK API key input on web dashboard
- [x] Provider score comparison (per-provider breakdown)
- [x] Site vs Code cross-validation engine
- [x] Credibility scoring with contradiction detection
- [x] Pro Analysis service (¥3,000/company, Japan only)
- [x] Bilingual dashboard (English / 日本語)
- [x] PDF report export
- [x] Disconnect & Purge with certificate
- [ ] AI-enhanced site analysis (send site claims to AI for deeper evaluation)
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
