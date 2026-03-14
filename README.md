<div align="center">

# Due Diligence Engine

**AI-Powered Technical Due Diligence for Venture Capital**

Verify startup technical claims. Detect AI-washing. Score with confidence.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Claude](https://img.shields.io/badge/AI-Claude_Opus_4.6-orange.svg)](https://anthropic.com)

[English](README.md) | [日本語](README.ja.md)

</div>

---

## What is this?

**Due Diligence Engine** is a CLI tool that helps VCs and investors technically verify startup claims under NDA. It temporarily ingests confidential materials (source code, architecture docs, demos), analyzes them using Claude Opus 4.6, generates a scored report with architecture visualizations, and then **completely purges all ingested data**.

### The Problem

- Startups claim "proprietary AI" — but is it just a GPT wrapper?
- Technical due diligence takes weeks and costs $50K+ with consultants
- Non-technical investors can't verify engineering claims
- NDA-protected materials require strict data handling

### The Solution

```
Ingest → Analyze → Score → Report → Purge
  5min     10min    auto    auto     auto
```

Total time: **~15 minutes** vs. weeks with traditional Tech DD.

---

## Features

| Feature | Description |
|---------|-------------|
| **Code Reality Check** | AST analysis to verify AI logic actually exists in the codebase |
| **AI-Washing Detection** | Detect thin API wrappers disguised as "proprietary AI" |
| **Git Forensics** | Analyze commit history for suspicious patterns (rush commits before DD) |
| **Doc-Code Consistency** | Cross-reference technical documents against actual implementation |
| **Architecture Visualization** | Auto-generate Mermaid diagrams of real system architecture |
| **100-Point Scoring** | Weighted scoring across 6 dimensions with RED FLAG detection |
| **NDA-Safe Data Purge** | Cryptographic erasure with verifiable purge certificates |
| **Slide Generation** | Investment committee-ready HTML/PDF slides |

---

## Scoring Framework

```
┌─────────────────────────────────────────────┐
│            SCORING DIMENSIONS               │
├─────────────────────────────────────────────┤
│  Technical Reality    ████████░░  /25        │
│  Originality          ████████░░  /20        │
│  Scalability          ████████░░  /15        │
│  Team Engineering     ████████░░  /15        │
│  Security Posture     ████████░░  /10        │
│  Business Alignment   ████████░░  /15        │
├─────────────────────────────────────────────┤
│  TOTAL                            /100       │
│                                             │
│  90-100  ✅ STRONG    — Exceptional          │
│  80-89   ✅ SOLID     — Investment-ready     │
│  60-79   ⚠️ CAUTION  — Gaps identified      │
│  40-59   🔴 CONCERN  — Significant issues    │
│  0-39    🔴 CRITICAL — Major red flags       │
└─────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (Claude Opus 4.6)

### Installation

```bash
git clone https://github.com/your-username/due-diligence-engine.git
cd due-diligence-engine
pip install -e .
```

### Configuration

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### Usage

```bash
# Analyze a startup's source code
dde analyze --source /path/to/startup-code --docs /path/to/tech-docs

# Analyze with specific output format
dde analyze --source /path/to/repo --output report --format html

# View the generated scorecard
dde report --latest

# Verify data purge
dde purge --verify

# View leaderboard (80+ scores only)
dde leaderboard
```

---

## How It Works

```
                    ┌──────────────────┐
                    │   NDA Materials  │
                    │  (Code/Docs/API) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  1. INGEST       │
                    │  Encrypted tmpfs │
                    │  RAM-only store  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────────┐ ┌───▼──────────┐
     │ Code Analysis  │ │ Doc Review │ │ Git Forensics│
     │ AST / Deps /   │ │ Claims vs  │ │ Commit       │
     │ API Detection  │ │ Reality    │ │ Patterns     │
     └────────┬───────┘ └───┬────────┘ └───┬──────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼─────────┐
                    │ 2. ANALYZE       │
                    │ Claude Opus 4.6  │
                    │ Deep reasoning   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ 3. SCORE         │
                    │ 100-point scale  │
                    │ RED FLAG detect  │
                    └────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                │                         │
       ┌────────▼───────┐      ┌─────────▼────────┐
       │ 4. REPORT      │      │ 5. PURGE         │
       │ MD / HTML / PDF│      │ Crypto-erase     │
       │ Slides         │      │ Purge certificate│
       └────────────────┘      └──────────────────┘
```

---

## Output Examples

### Scorecard

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Company:   [REDACTED]
 Date:      2026-03-14
 Overall:   62 / 100  ⚠️ CAUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Technical Reality    ████████░░  16/25
 Originality          ███░░░░░░░   6/20
 Scalability          ████████░░  12/15
 Team Engineering     ██████░░░░  12/15
 Security Posture     ████████░░   8/10
 Business Alignment   ████░░░░░░   8/15
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RED FLAGS:
 • "Proprietary LLM" claim — codebase shows
   OpenAI API wrapper with minimal prompt eng.
 • 80% of git commits in last 2 weeks
   (suspected rush development before DD)
 • No test coverage for core ML pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Architecture Slide (auto-generated)

Real architecture discovered from code analysis, presented as investment committee-ready Mermaid diagrams with gap annotations.

---

## Data Security & NDA Compliance

| Guarantee | Implementation |
|-----------|---------------|
| **No cloud storage** | All data processed locally in encrypted tmpfs |
| **API data handling** | Anthropic 0-day retention policy for API calls |
| **Cryptographic erasure** | `shred` + encrypted volume destruction |
| **Purge certificate** | SHA-256 hash log proving data existed and was destroyed |
| **No raw code in reports** | Reports contain findings only, never source code |
| **Audit trail** | Timestamped log of all operations for compliance |

---

## Project Structure

```
due-diligence-engine/
├── src/
│   ├── ingest/           # Secure data intake
│   ├── analyze/          # Claude-powered analysis
│   │   ├── code.py       # AST & dependency analysis
│   │   ├── docs.py       # Document claim extraction
│   │   ├── git.py        # Git history forensics
│   │   └── consistency.py # Cross-reference checker
│   ├── score/            # Scoring engine
│   ├── report/           # Report & slide generation
│   ├── purge/            # Secure data destruction
│   └── cli.py            # CLI interface
├── templates/
│   ├── evaluation.md     # Evaluation framework
│   ├── scorecard.html    # Scorecard template
│   └── slides/           # Slide templates
├── leaderboard.json      # 80+ scores (name, score, date only)
├── pyproject.toml
└── README.md
```

---

## Deployment Options

### Option 1: Self-Hosted CLI (OSS / Free)

Use your own Anthropic API key. Full control, no data leaves your machine (except API calls).

```bash
pip install due-diligence-engine
export ANTHROPIC_API_KEY="sk-..."
dde analyze --source /path/to/repo
```

### Option 2: SaaS API (Managed Service)

For VCs who prefer not to manage API keys and infrastructure. **Pricing: 2x API cost** (transparent markup).

```bash
# No Anthropic key needed — we handle it
dde analyze --source /path/to/repo --saas --api-key "dde_your_key"
```

#### SaaS Pricing

| Tier | Monthly Base | Per-Analysis | Included | Features |
|------|-------------|-------------|----------|----------|
| **Starter** | - | API cost × 2 (min $0.50) | 5 repos/mo | Score + Basic Report |
| **Professional** | - | API cost × 2 (min $0.50) | 25 repos/mo | + Slides + PDF + Git Forensics |
| **Enterprise** | Custom | API cost × 2 | Unlimited | + Purge Certificate + Priority Support |

#### Cost Example (Per Analysis)

```
Hybrid model analysis of a 10,000-line codebase:

  Haiku  (scan)    →  $0.50 API cost  →  $1.00 charged
  Sonnet (analyze) →  $4.00 API cost  →  $8.00 charged
  Opus   (judge)   →  $7.00 API cost  →  $14.00 charged
  ──────────────────────────────────────────────────
  Total              $11.50 API cost  →  $23.00 charged
```

#### Start the SaaS Server

```bash
export STRIPE_API_KEY="sk_..."
export ANTHROPIC_API_KEY="sk-..."
dde serve --host 0.0.0.0 --port 8000
```

---

## Roadmap

- [x] Core evaluation framework design
- [x] CLI tool with secure ingest pipeline
- [x] Claude Opus 4.6 hybrid integration (Haiku → Sonnet → Opus)
- [x] Code analysis engine (AST + dependency graph)
- [x] Git forensics module
- [x] Scoring engine with RED FLAG detection
- [x] SaaS API with Stripe billing (2x pricing)
- [ ] HTML/PDF slide generation
- [ ] Cryptographic purge with certificates
- [ ] Leaderboard management
- [ ] Web dashboard for VC teams
- [ ] Batch analysis mode (portfolio-wide DD)

---

## Disclaimer

This tool provides **technical analysis to assist investment decisions**. It is not investment advice. Scores are based on automated analysis of provided materials and should be used as one input among many in the due diligence process. Always consult qualified professionals for investment decisions.

---

## License

[Apache License 2.0](LICENSE) — See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with [Claude Opus 4.6](https://anthropic.com) by Anthropic**

</div>
