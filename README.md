<div align="center">

# 🔍 Due Diligence Engine

### **Your IDE's AI → World-Class Tech DD Analyst**

<sub>**Zero API keys · PDF-first · OSS · CodeQL-audited**</sub>

<br/>

```
┌─────────────────────────────────────────────────────────────┐
│  $ dde prompt --pdf                                         │
│                                                             │
│  Reading codebase...                                        │
│  Evaluating across 6 dimensions...                          │
│  Building competitive landscape (7 charts × 6 markets)...   │
│  Researching implementation matrix (30 items × 10 cos.)...  │
│                                                             │
│  Score:  [■■■■■■■■■■■■■■■■■■■■■■■■■■□□□□] 82/100  Lv.8     │
│  Grade:  B  →  Viable with conditions                       │
│                                                             │
│  → ~/Downloads/dde_consulting_<project>_<date>.pdf  (22 p.) │
└─────────────────────────────────────────────────────────────┘
```

<br/>

[![License](https://img.shields.io/badge/License-Apache_2.0-000000.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-5271FF.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![CodeQL](https://img.shields.io/badge/Security-CodeQL_·_Dependabot_·_pip--audit-5271FF.svg?style=for-the-badge&logo=github&logoColor=white)](SECURITY.md)
[![PDF](https://img.shields.io/badge/Output-PDF_First-000000.svg?style=for-the-badge&logo=adobeacrobatreader&logoColor=white)](#)

[**English**](README.md) · [日本語](README.ja.md)

</div>

---

## ⚡ Quick Start

```bash
pip install --no-cache-dir git+https://github.com/taka-avantgarde/Due-diligence-engine.git
dde prompt --pdf
```

Run this in any AI-powered IDE terminal (Claude Code, Cursor, Copilot).
Your AI reads the codebase, evaluates it as a world-class technology consultant,
and writes a 22-page PDF to `~/Downloads/`. **No API keys. No cloud. No extra cost.**

---

## What Makes DDE Different

Most "AI code reviewers" check:
> *"Does it have authentication? ✓ Does it have HTTPS? ✓ Does it have tests? ✓"*

That's checkbox compliance. **DDE goes deeper:**

> *"Is the encryption Signal Protocol? Is it PQXDH with ML-KEM-1024?
> Is it built on libsignal/BoringSSL FFI, or self-rolled crypto?
> Does the team publish cryptographic research?"*

Built on the **Atlas Engineering Philosophy**: cryptographic sophistication and
deep technical originality differentiate winners. Checkbox compliance
(SOC2, MFA, WebAuthn) is hygiene, not differentiation.

---

## 🔒 Atlas Engineering Philosophy (v2.0 — encryption-dominant)

A parallel evaluation system added on top of (not replacing) the standard 6-dimension scoring.

```
4 axes — weights sum to 100%

  Performance        25%  ████████████░░░░░░░░░░░░░░░░░░░░
  Stability          20%  ██████████░░░░░░░░░░░░░░░░░░░░░░
  Lightweight         5%  ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Ultra-High Security 50% █████████████████████████░░░░░░░  ← THE CORE

  Security sub-breakdown (within 50%):
    Cryptographic Sophistication  30%  ← Signal Protocol, PQXDH, libsignal
    Privacy Protection             8%
    Communication Safety           7%
    Layer Composition              3%
    General Posture                2%  ← MFA, SOC2, etc. — minimum hygiene
```

---

## 📊 6-Dimension Standard Scoring (v1.x — preserved)

| Dimension | Weight | What It Detects |
|-----------|-------:|-----------------|
| Technical Originality | 25% | API wrapper vs. genuine IP |
| Technology Advancement | 20% | Stack modernity |
| Implementation Depth | 20% | PoC vs. production |
| Architecture Quality | 15% | Structure quality |
| Claim Consistency | 10% | Pitch vs. reality |
| Security Posture | 10% | Security maturity |

```
Grade Bands:

  0      40       60      75       90     100
  |------|--------|-------|--------|------|
   F      D        C       B        A
   ✗      ⚠        ⚡       ✓        ★
```

| Grade | Recommendation |
|-------|----------------|
| ★ A (90+)  | Strong investment candidate |
| ✓ B (75-89)| Viable with conditions |
| ⚡ C (60-74)| Significant concerns |
| ⚠ D (40-59) | High risk |
| ✗ F (<40)  | Do not invest |

Each dimension also rated **Lv.1-10** with explicit criteria.

---

## 🎯 7 Competitive Charts × 6 Markets

For each of 6 global markets (Global / US / EMEA / Japan / SEA / LATAM):

| # | Chart | What It Shows |
|---|-------|---------------|
| 1 | **Forrester Wave / Magic Quadrant** | Vision × Execution |
| 2 | **BCG Growth-Share Matrix** | Market growth × Relative share |
| 3 | **McKinsey Tech Moat** | Competitive position × Technical moat |
| 4 | **Security & Privacy Maturity** | Security implementation × Privacy readiness |
| 5 | **Data Governance & Transparency** | Data protection × Audit transparency |
| 6 | **GS Risk-Adjusted Return** | Downside risk × Upside potential |
| 7 | **Innovation vs. Commercialization** | R&D velocity × ARR traction (3D bubble) |

**6-16 competitors per chart** with axis rationale captions explaining
*why* each axis matters and *what* the composite score captures.

---

## 🆕 Implementation Capability Matrix (v2.0)

The 8th competitive chart — **30 items × 5-10 top global competitors**:

```
                       Target  Signal  WhatsApp  Telegram  iMessage  Wire
Encryption (core differentiator)
  E2E (Signal Protocol)  ○      ○       ○        △         ○         ○
  PQXDH / ML-KEM-1024    ○      ○       ×        ×         ○         ?
  Double Ratchet         ○      ○       ○        ×         ○         ○
  libsignal / BoringSSL  ○      ○       ×        ×         ○         △
  No self-rolled crypto  ○      ○       △        ×         ○         △
  Forward Secrecy + PCS  ○      ○       ○        △         ○         ○
  Zero-Knowledge proofs  △      ×       ×        ×         ×         ×
  Crypto research pubs   ○      ×       ×        ×         △         ×
  ...
```

4-state marking (Japanese tech rating standard):
- **○ verified** (publicly documented implementation)
- **△ claimed** (asserted, not verifiable)
- **× not implemented** (explicitly absent)
- **? unknown** (cannot determine — preferred over guessing)

---

## 📄 What's in the 22-Page PDF

**v1.x core (15 pages — preserved verbatim)**

| # | Section | Content |
|---|---------|---------|
| 1 | Cover | Black + Arc sky (#5271FF) accent, project name, score, grade |
| 2 | Score Dashboard | 6-dim horizontal bar chart + score barometer |
| 3 | Executive Summary | Business + technical summary |
| 4 | SWOT Analysis | 2×2 visual grid with evidence + business analogies |
| 5 | Score Breakdown | Per-dimension rationale & enablers |
| 6 | Tech Level Assessment | Lv.1-10 gauge with plain-language explanation |
| 7 | Future Outlook | 1/3/5-year projections with confidence |
| 8 | Strategic Advice | Immediate, medium, long-term |
| 9 | Investment Thesis | Recommendation, risks, upside, comparables |
| 10 | Red Flags | Severity-rated (Critical/High/Medium/Low) |
| 11 | Site Verification | 10-item credibility check (if URLs given) |
| 12-14 | Competitive Analysis | 7 charts × 6 markets with axis rationale |
| 15 | Glossary | All jargon annotated for non-engineers |

**v2.0 additions (4 new pages)**

| # | Section | Content |
|---|---------|---------|
| 16 | **Atlas 4-Axis Dashboard** | Performance/Stability/Lightweight/Ultra-Security with horizontal bars |
| 17 | **Ultra-High Security Sub-Breakdown** | 5 sub-items, encryption (30%) visually dominant |
| 18 | **Implementation Capability Matrix** | 30 items × top competitors, ○△×? marking |

---

## 🛠️ Usage

```bash
# Current directory, English PDF
dde prompt --pdf

# Japanese PDF
dde prompt --pdf --lang ja

# GitHub repo with stage context
dde prompt owner/repo --pdf --lang ja --stage seed

# Non-interactive (for AI terminals without prompt support)
dde prompt --pdf --lang ja \
  --url https://example.com \
  --url https://docs.example.com

# Direct BYOK multi-AI cross-verification (optional)
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_AI_API_KEY=AIza...
export OPENAI_API_KEY=sk-...
dde analyze owner/repo
```

---

## 🔐 Security & OSS Philosophy

| Guarantee | Implementation |
|-----------|----------------|
| **Local-only processing** | `dde prompt` never sends data anywhere |
| **No source code in reports** | PDFs contain findings only |
| **API 0-day retention** | `dde analyze` uses no-retention endpoints |
| **Automated security CI** | CodeQL · Dependabot · pip-audit · safety · osv-scanner · gitleaks |
| **Branch protection** | `main` requires PR + CI + secret push protection |
| **Private repo access via PAT** | Used in memory once, never stored |

Vulnerability reports: see [SECURITY.md](SECURITY.md) — 48h response SLA.

### Why OSS is a security feature, not a risk

Open-source means every line is auditable. No hidden backdoors. No black-box scoring.
This is the same philosophy as Signal and libsignal: **transparency *is* trust**.

---

## 📜 License

[Apache License 2.0](LICENSE) — Copyright © 2026 Takayuki Miyano / Atlas Associates

---

<div align="center">

**Powered by Due Diligence Engine — Takayuki Miyano / Atlas Associates**

`v0.2.0` — Black + `#5271FF` brand identity · Tech-first aesthetics

</div>
