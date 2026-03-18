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

**Due Diligence Engine** is a CLI + Web tool that helps VCs and investors technically verify startup claims under NDA. It connects to private GitHub repositories via OAuth, analyzes source code using Claude Opus 4.6, generates scored reports with architecture visualizations, and then **completely purges all ingested data** with a verifiable purge certificate.

### The Problem

- Startups claim "proprietary AI" — but is it just a GPT wrapper?
- Technical due diligence takes weeks and costs $50K+ with consultants
- Non-technical investors can't verify engineering claims
- NDA-protected materials require strict data handling

### The Solution

```
Connect → Analyze → Score → Report → Disconnect & Purge
  1min      10min    auto    auto         1click
```

Total time: **~15 minutes** vs. weeks with traditional Tech DD.

---

## Try It Now (No Setup Required)

Want to see how it works before setting up your own API key? Try our hosted demo:

**https://due-diligence-engine.web.app/dashboard/**

Just paste any public GitHub URL and click Analyze. No API key needed for basic analysis.

---

## Just Paste the URL

```bash
dde analyze https://github.com/some-startup/their-product
```

That's it. One command. Full technical due diligence.

### For VCs

```
Step 1: Get the startup's GitHub repo URL
Step 2: dde analyze <URL>
Step 3: Review the scorecard
```

### For Startups (Prove Your Tech)

Add this to your repo — VCs can trigger it anytime:

```yaml
# .github/workflows/dde.yml
name: Technical Due Diligence
on: workflow_dispatch
jobs:
  dd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: taka-avantgarde/due-diligence-engine@main
        with:
          skip_ai: 'true'
```

VCs click **"Run workflow"** on the startup's repo → instant DD report.

---

## Features

| Feature | Description |
|---------|-------------|
| **GitHub Private Repo Access** | OAuth integration — startups grant temporary access to their private repos |
| **Code Reality Check** | AST analysis to verify AI logic actually exists in the codebase |
| **AI-Washing Detection** | Detect thin API wrappers disguised as "proprietary AI" |
| **Git Forensics** | Analyze commit history for suspicious patterns (rush commits before DD) |
| **Doc-Code Consistency** | Cross-reference technical documents against actual implementation |
| **Architecture Visualization** | Auto-generate Mermaid diagrams of real system architecture |
| **10-Level Tech Rating** | Each dimension rated Lv.1-10 with clear criteria (technology-focused, no team eval) |
| **100-Point Scoring** | Weighted scoring across 6 tech dimensions with RED FLAG detection |
| **PDF Export** | Professional investment committee-ready PDF reports |
| **Disconnect & Purge** | One-click GitHub disconnect + cryptographic data erasure + purge certificate |
| **Web Dashboard** | Browser-based UI for non-technical VCs |

---

## Scoring Framework

Technology-focused evaluation only. No team/process assessment.

### 6 Dimensions with 10-Level Rating

| Dimension | Weight | What It Detects |
|-----------|--------|----------------|
| Technical Originality | 25% | API wrapper vs. genuine IP (Lv.1 Copy ... Lv.10 Frontier) |
| Technology Advancement | 20% | Stack modernity (Lv.1 Legacy ... Lv.10 Visionary) |
| Implementation Depth | 20% | PoC vs. production (Lv.1 Mockup ... Lv.10 Mission-Critical) |
| Architecture Quality | 15% | Structure quality (Lv.1 Spaghetti ... Lv.10 Distributed) |
| Claim Consistency | 10% | Pitch vs. reality (Lv.1 Fabricated ... Lv.10 Transparent) |
| Security Posture | 10% | Security maturity (Lv.1 Negligent ... Lv.10 Military-Grade) |

### Grading

| Score | Grade | Recommendation |
|-------|-------|---------------|
| 90-100 | A | Strong investment candidate |
| 75-89 | B | Viable with conditions |
| 60-74 | C | Significant concerns |
| 40-59 | D | High risk |
| 0-39 | F | Do not invest |

### Pricing

| Plan | API Key | Cost | For |
|------|---------|------|-----|
| **BYOK** | Your own | **FREE** | Technical VCs |
| **SaaS** | Managed | **2x API cost** | Non-technical VCs |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (Claude Opus 4.6)
- GitHub OAuth App (for private repo access)

### Installation

```bash
git clone https://github.com/taka-avantgarde/due-diligence-engine.git
cd due-diligence-engine
pip install -e .
```

### Configuration

```bash
export ANTHROPIC_API_KEY="your-api-key"

# Optional: for private repo access via GitHub OAuth
export GITHUB_CLIENT_ID="your-github-oauth-app-id"
export GITHUB_CLIENT_SECRET="your-github-oauth-app-secret"
```

### Private Repository Access — PAT (Personal Access Token)

For private repositories, the startup provides a **GitHub PAT (Personal Access Token)** to DDE.
A PAT is a token string that acts as a password substitute for GitHub API / git operations. DDE supports two types:

---

#### Option A: Classic PAT (Recommended for simplicity)

Classic PATs grant access to **all repositories** the token owner can access. Simple to create but broader scope.

1. Open GitHub → click your **profile icon** (top-right) → **Settings**
2. Left sidebar → scroll down → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. Click **Generate new token** → **Generate new token (classic)**
5. Configure:

   | Setting | Value |
   |---------|-------|
   | **Note** | `DDE DD Analysis` (any descriptive name) |
   | **Expiration** | `7 days` (recommended — set to match your DD timeline) |
   | **Select scopes** | Check **`repo`** (Full control of private repositories) |

   > Note: The `repo` scope includes both read and write access. DDE only performs `git clone --depth 1` (read-only). The token is used once in-memory and immediately discarded.

6. Click **Generate token**
7. **Copy the token** (`ghp_...`) — it will only be shown once
8. Paste the token into the DDE dashboard "Private repo?" section alongside your repo URL

**Direct link:** [github.com/settings/tokens](https://github.com/settings/tokens)

---

#### Option B: Fine-grained PAT (More secure, per-repo scope)

Fine-grained PATs can be scoped to **specific repositories** with **read-only** permissions. More secure but requires Organization approval for Org repos.

1. Open GitHub → **profile icon** → **Settings**
2. Left sidebar → **Developer settings**
3. **Personal access tokens** → **Fine-grained tokens**
4. Click **Generate new token**
5. Configure:

   | Setting | Value |
   |---------|-------|
   | **Token name** | `DDE DD Analysis` |
   | **Expiration** | `7 days` (recommended) |
   | **Resource owner** | Select the Organization that owns the repo (e.g., `Your-Org`) |
   | **Repository access** | **Only select repositories** → choose the target repo |

6. Expand **Permissions** → **Repository permissions**:

   | Permission | Access level |
   |------------|-------------|
   | **Contents** | **Read-only** |
   | **Metadata** | **Read-only** (auto-selected) |

   > All other permissions should remain **No access**.

7. Click **Generate token**
8. **Copy the token** (`github_pat_...`) — it will only be shown once
9. Paste into the DDE dashboard

**Direct link:** [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta)

**Important for Organization repos:**
- The Org admin must enable Fine-grained PATs: Org Settings → Personal access tokens → **Allow access via fine-grained personal access tokens**
- If "Require administrator approval" is enabled, the admin must approve the token in **Pending requests** before it works

---

#### Which PAT type should I use?

| | Classic PAT (`ghp_...`) | Fine-grained PAT (`github_pat_...`) |
|---|---|---|
| **Ease of setup** | Simple (2 clicks) | More steps required |
| **Repo scope** | All repos you can access | Specific repos only |
| **Permissions** | `repo` = read+write | Contents: Read-only |
| **Org approval** | Not required | May require admin approval |
| **Best for** | Quick DD, personal repos | Org repos, security-conscious startups |

#### Security Guarantee

- Your PAT is **never stored** on DDE servers
- It is used **once in-memory** for `git clone --depth 1`, then immediately discarded
- No credentials are persisted to disk, database, or logs
- All cloned source code is cryptographically erased after analysis (purge certificate provided)

### Usage — CLI

```bash
# Analyze from GitHub URL (just paste the URL!)
dde analyze https://github.com/some-startup/their-repo

# Short form (owner/repo)
dde analyze some-startup/their-repo

# Specific branch
dde analyze https://github.com/some-startup/their-repo/tree/develop

# Local directory
dde analyze /path/to/startup-code

# Zip archive
dde analyze /path/to/startup-code.zip

# With options
dde analyze some-startup/repo --name "Startup X" --format html --format md

# Skip AI (local analysis only, free)
dde analyze some-startup/repo --skip-ai

# View leaderboard (80+ scores only)
dde leaderboard
```

### Usage — Web Dashboard (for Private Repos)

```bash
# Start the web server
dde serve

# Open http://localhost:8000/dashboard/
```

The Web Dashboard provides:
1. **Connect with GitHub** — OAuth flow to access startup's private repos
2. **Select & Analyze** — Choose a repo and run analysis
3. **View Results** — Scorecard, RED FLAGS, architecture diagrams
4. **Export PDF** — Download investment committee-ready report
5. **Disconnect & Purge** — Revoke access + cryptographic data erasure

---

## How It Works

```
                    ┌──────────────────┐
                    │  GitHub Private  │
                    │  Repo (via OAuth)│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  1. INGEST       │
                    │  Shallow clone   │
                    │  Encrypted store │
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
                    │ Haiku → Sonnet   │
                    │ → Opus (hybrid)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ 3. SCORE         │
                    │ 100-point scale  │
                    │ RED FLAG detect  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────────┐ ┌───▼──────────┐
     │ 4. REPORT      │ │ 5. PDF     │ │ 6. PURGE     │
     │ MD / HTML      │ │ Export     │ │ Disconnect   │
     │ Slides         │ │ (no code)  │ │ + Crypto-del │
     └────────────────┘ └────────────┘ │ + Certificate│
                                       └──────────────┘
```

---

## Private Repo Workflow (VC ↔ Startup)

```
Step 1: VC sends startup an access request link
Step 2: Startup approves GitHub OAuth (grants repo access)
Step 3: DDE clones repo into encrypted temp directory
Step 4: Analysis runs (Haiku → Sonnet → Opus)
Step 5: VC reviews scorecard + downloads PDF
Step 6: VC clicks "Disconnect & Purge"
         ├─ GitHub OAuth token revoked
         ├─ All source code crypto-erased
         ├─ Purge certificate generated
         └─ Only scores & findings retained (no code)
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

### PDF Report

Professional PDF with cover page, score breakdown, RED FLAGS, architecture findings, and NDA compliance footer. **Contains zero source code** — only analysis findings and recommendations.

### Disconnect & Purge Confirmation

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PURGE CERTIFICATE
 Certificate ID: dde_purge_a1b2c3d4
 Date:           2026-03-14T15:30:00Z
 Files purged:   847
 Bytes erased:   12,345,678
 Method:         3-pass random overwrite
 GitHub token:   REVOKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Data Security & NDA Compliance

| Guarantee | Implementation |
|-----------|---------------|
| **No cloud storage** | All data processed locally in encrypted tmpfs |
| **OAuth tokens encrypted** | Fernet encryption, in-memory only (never written to disk) |
| **API data handling** | Anthropic 0-day retention policy for API calls |
| **Cryptographic erasure** | 3-pass random overwrite + encrypted volume destruction |
| **Purge certificate** | SHA-256 signed certificate proving data existed and was destroyed |
| **GitHub disconnect** | OAuth token revoked via GitHub API on disconnect |
| **No raw code in reports** | PDF/MD reports contain findings only, never source code |
| **Audit trail** | Timestamped log of all operations for compliance |

---

## Project Structure

```
due-diligence-engine/
├── src/
│   ├── ingest/              # Secure data intake (local, zip, GitHub URL)
│   ├── analyze/             # Claude-powered analysis
│   │   ├── code.py          # AST & dependency analysis
│   │   ├── docs.py          # Document claim extraction
│   │   ├── git_forensics.py # Git history forensics
│   │   ├── consistency.py   # Cross-reference checker
│   │   └── engine.py        # Hybrid model orchestrator
│   ├── score/               # 100-point scoring engine
│   ├── report/
│   │   ├── generator.py     # MD/HTML report generation
│   │   ├── slides.py        # Architecture visualization
│   │   └── pdf_generator.py # Professional PDF export
│   ├── purge/               # Cryptographic data destruction
│   ├── saas/
│   │   ├── app.py           # FastAPI endpoints
│   │   ├── dashboard.py     # Web dashboard UI
│   │   ├── github_oauth.py  # GitHub OAuth integration
│   │   ├── billing.py       # Stripe billing (2x pricing)
│   │   └── auth.py          # API key authentication
│   └── cli.py               # CLI interface
├── templates/
│   ├── evaluation.md        # Evaluation framework
│   ├── scorecard.html       # Scorecard template
│   └── dashboard.html       # Web dashboard template
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
dde analyze owner/repo
```

### Option 2: Self-Hosted Web Dashboard (OSS / Free)

Run the full web dashboard locally with GitHub OAuth for private repos.

```bash
export ANTHROPIC_API_KEY="sk-..."
export GITHUB_CLIENT_ID="..."
export GITHUB_CLIENT_SECRET="..."
dde serve
# Open http://localhost:8000/dashboard/
```

### Option 3: SaaS API (Managed Service)

For VCs who prefer not to manage API keys and infrastructure. **Pricing: 2x API cost** (transparent markup).

#### SaaS Pricing

| Tier | Monthly Base | Per-Analysis | Included | Features |
|------|-------------|-------------|----------|----------|
| **Starter** | - | API cost x 2 (min $0.50) | 5 repos/mo | Score + Basic Report |
| **Professional** | - | API cost x 2 (min $0.50) | 25 repos/mo | + Slides + PDF + Git Forensics |
| **Enterprise** | Custom | API cost x 2 | Unlimited | + Purge Certificate + Priority Support |

#### Cost Example (Per Analysis)

```
Hybrid model analysis of a 10,000-line codebase:

  Haiku  (scan)    →  $0.50 API cost  →  $1.00 charged
  Sonnet (analyze) →  $4.00 API cost  →  $8.00 charged
  Opus   (judge)   →  $7.00 API cost  →  $14.00 charged
  ──────────────────────────────────────────────────
  Total              $11.50 API cost  →  $23.00 charged
```

---

## Roadmap

- [x] Core evaluation framework design
- [x] CLI tool with secure ingest pipeline
- [x] Claude Opus 4.6 hybrid integration (Haiku -> Sonnet -> Opus)
- [x] Code analysis engine (AST + dependency graph)
- [x] Git forensics module
- [x] Scoring engine with RED FLAG detection
- [x] SaaS API with Stripe billing (2x pricing)
- [x] GitHub URL direct analysis (`dde analyze owner/repo`)
- [x] GitHub OAuth for private repo access
- [x] Web dashboard with Connect/Analyze/Disconnect flow
- [x] PDF report export (no source code included)
- [x] Disconnect & Purge with certificate generation
- [ ] Leaderboard management
- [ ] Batch analysis mode (portfolio-wide DD)
- [ ] Startup-side access approval portal

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
