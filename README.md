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
│  Evaluating across 5 dimensions (equal 20% weights)...      │
│  Building competitive landscape (7 charts × 6 markets)...   │
│  Researching implementation matrix (30 items × 10 cos.)...  │
│  Writing competitor selection rationales...                 │
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

[![GitHub stars](https://img.shields.io/github/stars/taka-avantgarde/Due-diligence-engine?style=flat-square&color=5271FF)](https://github.com/taka-avantgarde/Due-diligence-engine/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/taka-avantgarde/Due-diligence-engine?style=flat-square&color=000000)](https://github.com/taka-avantgarde/Due-diligence-engine/issues)
[![Last Commit](https://img.shields.io/github/last-commit/taka-avantgarde/Due-diligence-engine?style=flat-square&color=5271FF)](https://github.com/taka-avantgarde/Due-diligence-engine/commits/main)
[![Version](https://img.shields.io/badge/version-v0.3.0-000000?style=flat-square)](https://github.com/taka-avantgarde/Due-diligence-engine/releases)

[![Repo Views](https://komarev.com/ghpvc/?username=taka-avantgarde&repo=Due-diligence-engine&color=5271FF&style=flat-square&label=Repo+Views)](https://github.com/taka-avantgarde/Due-diligence-engine)
[![Unique Visitors](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Ftaka-avantgarde%2FDue-diligence-engine&count_bg=%23000000&title_bg=%235271FF&icon=github.svg&icon_color=%23FFFFFF&title=Unique+Visitors&edge_flat=true)](https://github.com/taka-avantgarde/Due-diligence-engine)

[**English**](README.md) · [日本語](README.ja.md)

</div>

---

## ⚡ Quick Start

```bash
python3 -m pip install --no-cache-dir git+https://github.com/taka-avantgarde/Due-diligence-engine.git
dde prompt --pdf
```

Run this in any AI-powered IDE terminal (Claude Code, Cursor, Copilot).
Your AI reads the codebase, evaluates it as a world-class technology consultant,
and writes a 24-page PDF to `~/Downloads/`. **No API keys. No cloud. No extra cost.**

---

## 💭 How to Get the Best Results

> **TL;DR**: Launch the highest-tier AI you have access to in your IDE terminal,
> paste the command, and wait 10-20 minutes. That's it.

**Recommended setup:**

- **Spin up the most capable model available** in your IDE (Claude Opus 4.x, GPT-5, Gemini 2.5 Pro, etc.)
- **Paste `dde prompt --pdf`** into the terminal
- **Go grab a coffee** ☕ — the AI will read hundreds of files, evaluate across
  9+ dimensions, research 5-10 competitors globally, and build a 24-page consulting PDF
- **Expected time**: **10-20 minutes** (longer for large codebases or deeper models)

**Why this approach?**

| Concern | Answer |
|---------|--------|
| 🔐 **Data leakage?** | None. Everything runs inside your IDE's AI sandbox — no 3rd-party servers, no telemetry. DDE itself is 100% local Python |
| 💰 **Cost?** | $0 extra. Uses your existing IDE AI subscription |
| 🔑 **API keys?** | Not needed. Your IDE already handles AI auth |
| ⚙️ **Setup?** | Just `python3 -m pip install`. No config, no accounts |
| 🎁 **Catch?** | There isn't one. DDE is a **hobby project** — built and open-sourced for fun. Use it freely |

> **Made by a solo dev as a hobby.** If it helps you, that's enough reward. Star the repo if you like it ⭐

---

## 👥 Who Is This For?

| User | Use Case | Time Saved |
|------|----------|-----------|
| **VC Tech Partners** | Pre-investment technical DD on portfolio candidates | 2-5 days → 30 min |
| **CTOs / Engineering Leads** | Internal tech audit before board meetings | 1 week → 1 hour |
| **M&A Technical Advisors** | Due diligence on acquisition targets | 1-2 weeks → 1 day |
| **Independent DD Consultants** | Boutique firm tech evaluations | scale: 1→10 clients/week |
| **Founders** | Self-assessment before fundraising | objective view of own codebase |
| **Corporate Innovation** | Vendor / startup partnership evaluation | ad-hoc → systematic |

> Built for engineers and technical decision-makers who already use AI in their daily workflow.

---

## 🆚 vs. Other Tools

|   | DDE | Manual DD | Generic AI Code Review | SaaS DD Platforms |
|---|:---:|:---:|:---:|:---:|
| **Cost** | $0 (uses your IDE AI) | $$$$ (consultant fees) | API fees | $$$$ (subscription) |
| **Privacy** | Local-only | Local | Sends code to vendor | Sends code to vendor |
| **Output** | 24-page consulting PDF | Custom report | Inline comments | Web dashboard |
| **Crypto Depth** | PQXDH / Signal Protocol level | Depends on consultant | Generic | Generic |
| **Competitive Charts** | 7 + Implementation Matrix | Manual research | None | Limited |
| **Setup Time** | 1 command | Weeks | Minutes | Days (account/onboarding) |
| **Customization** | Full source access | Yes | Limited | Vendor-locked |

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

## 🔒 Atlas Engineering Philosophy (encryption-dominant parallel view)

A parallel evaluation system added alongside the standard 5-dimension scoring.

```
4 axes — weights sum to 100%

  Performance        25%  ████████████░░░░░░░░░░░░░░░░░░░░
  Stability          20%  ██████████░░░░░░░░░░░░░░░░░░░░░░
  Lightweight         5%  ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Security Strength 50% █████████████████████████░░░░░░░  ← THE CORE

  Security sub-breakdown (within 50%):
    Cryptographic Sophistication  30%  ← Signal Protocol, PQXDH, libsignal
    Privacy Protection             8%
    Communication Safety           7%
    Layer Composition              3%
    General Posture                2%  ← MFA, SOC2, etc. — minimum hygiene
```

---

## 📊 5-Dimension Standard Scoring (v0.3 — balanced, equal weights)

| Dimension | Weight | What It Detects |
|-----------|-------:|-----------------|
| Technical Originality | 20% | API wrapper vs. genuine IP |
| Technology Advancement | 20% | Stack modernity |
| Implementation Depth | 20% | PoC vs. production |
| Architecture Quality (incl. Security Posture) | 20% | Structure quality + security maturity |
| Claim Consistency | 20% | Pitch vs. reality |

> **v0.3 change**: Security Posture was merged into Architecture Quality. Security is now evaluated as an integral part of production-grade architecture, not a separate silo.

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

## 🆕 Implementation Capability Matrix

The 8th competitive chart — **~30 items × 5-10 top global competitors**:

```
                        Target   Comp. A   Comp. B   Comp. C   Comp. D   ...
Encryption (core differentiator)
  Feature 1              ○        ○         ×         △         ○
  Feature 2              ○        ○         ×         ×         ○
  Feature 3              ○        ○         ○         ×         ○
  Feature 4              ○        ×         ×         △         △
  ...
Privacy & Compliance
  Feature 1              ○        △         ○         ×         △
  Feature 2              ○        ○         △         ×         ×
  ...
```

Items and competitors are **chosen dynamically per target's industry**
(messaging, fintech, medical, gaming, SaaS, IoT, etc.).

4-state marking (Japanese tech rating standard):
- **○ verified** (publicly documented implementation)
- **△ claimed** (asserted, not verifiable)
- **× not implemented** (explicitly absent)
- **? unknown** (cannot determine — preferred over guessing)

Plus **competitor selection rationales** — 3-5 lines each explaining why each
specific competitor was chosen as a comparison target (HQ, market position, category).

---

## 📄 What's in the 24-Page PDF

| # | Section | Content |
|---|---------|---------|
| 1 | Cover | Black + Arc sky (#5271FF) accent, project name, score, grade |
| 2 | Score Dashboard | **5-dim** horizontal bar chart (20% each) + score barometer |
| 3 | Executive Summary | Business + technical summary |
| 4 | SWOT Analysis | 2×2 visual grid with evidence + business analogies |
| 5 | Score Breakdown | Per-dimension rationale & enablers |
| 6 | Tech Level Assessment | **5-dim** Lv.1-10 bar chart + overall gauge |
| 7 | Future Outlook | 1/3/5-year projections with confidence |
| 8 | Strategic Advice | Immediate, medium, long-term |
| 9 | Investment Thesis | Recommendation, risks, upside, comparables |
| 10 | Red Flags | Severity-rated (Critical/High/Medium/Low) |
| 11 | Site Verification | 9-item credibility check (if URLs given) |
| 12-14 | Competitive Analysis | 7 charts × 6 markets with axis rationale |
| 15 | **🆕 Competitor Selection Rationales** | 3-5 line explanation per competitor (why chosen, HQ, position) |
| 16 | **Implementation Capability Matrix** | ~30 items × top competitors, ○△×? marking |
| 17 | **Atlas 4-Axis Dashboard** | Performance / Stability / Lightweight / Security Strength |
| 18 | **Security Sub-Breakdown + Glossary** | 5 sub-items with non-engineer glossary (MFA/SOC2/libsignal/PQXDH…) |
| 19-24 | Glossary · Consistency · Cost · Purge Cert | Standard appendix sections |

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

## ❓ FAQ

**Q: Does DDE send my code anywhere?**
A: No. `dde prompt` runs entirely locally — it generates a structured prompt that your IDE's AI reads. The AI evaluates the code in-place. The optional `dde analyze` (BYOK) sends to AI providers using their no-retention endpoints only.

**Q: Why is it free? What's the catch?**
A: There is no catch. DDE is OSS (Apache 2.0) and uses your existing IDE AI subscription (Claude Code / Cursor / Copilot). No telemetry, no upsell.

**Q: Can I use it in CI?**
A: Yes — see [`action.yml`](action.yml). Add the GitHub Action to PRs for automated DD scoring.

**Q: How accurate are the competitive charts?**
A: Charts are AI-researched from public sources (whitepapers, GitHub, blogs, SOC2 reports). Confidence depends on competitor transparency. Use `?` (unknown) liberally — false positives damage credibility more than gaps.

**Q: Why "Atlas Engineering Philosophy"?**
A: DDE is built by Atlas Associates, the company behind Arc Messenger (E2EE messaging with libsignal + PQXDH). The 4-axis evaluation reflects what we actually look for when evaluating tech.

**Q: Can I customize the scoring weights?**
A: The 5-dimension weights are equal 20% each (balanced, simple, interpretable). Atlas 4-axis weights (25/20/5/50) reflect Atlas philosophy and are also fixed. Sub-item weights within Security Strength adjust by industry context.

**Q: What if my project isn't security-critical?**
A: The 5-dimension score (Architecture Quality includes Security Posture at a balanced 20%) is your primary score. The Atlas 4-axis is a parallel reference view — both are shown.

---

## 🗺️ Roadmap

**Recently shipped (v0.3.0)**
- ✅ 5-dimension scoring (equal 20% weights, Security merged into Architecture)
- ✅ Competitor Selection Rationales (3-5 line explanation per competitor)
- ✅ Non-engineer glossary on Security Sub-Breakdown page (MFA/SOC2/libsignal/PQXDH)
- ✅ AIDD-era stance: no penalty for AI usage or high-velocity commits
- ✅ Visitor counter badges (komarev + hits.seeyoufarm)
- ✅ PDF layout: KeepTogether, 6-dim tech bar chart, SWOT 2×2 grid

**Previously shipped (v0.2.0)**
- ✅ Atlas 4-axis Optimization Assessment ("Security Strength" 50%)
- ✅ Implementation Capability Matrix (8th competitive chart)
- ✅ Web dashboard fully removed (CLI + PDF only)
- ✅ Black + Arc sky (#5271FF) brand identity
- ✅ Typography system overhaul (leading, hierarchy)
- ✅ Security CI hardening (CodeQL, Dependabot, gitleaks)

**Planned (v0.4.0+)**
- 🚧 Batch mode — analyze a portfolio of repos in one command
- 🚧 Historical tracking — re-analyze and show score deltas over time
- 🚧 Slack/Discord notification adapter
- 🚧 Industry-specific evaluation packs (medical, fintech, gaming presets)
- 🚧 PyPI / Homebrew distribution

Open an [issue](https://github.com/taka-avantgarde/Due-diligence-engine/issues) to suggest features or report bugs.

---

## 🤝 Contributing

Contributions welcome! The codebase is small and well-tested:

```bash
git clone https://github.com/taka-avantgarde/Due-diligence-engine
cd Due-diligence-engine
python3 -m pip install -e ".[dev]"
pytest
```

- **Bug reports**: please include `dde --version` output and a minimal reproduction
- **Feature requests**: open a GitHub Discussion first to gauge interest
- **Pull requests**: ensure all tests pass + add new tests for new features

---

## 📜 License

[Apache License 2.0](LICENSE) — Copyright © 2026 Takayuki Miyano / Atlas Associates

---

<div align="center">

**Powered by Due Diligence Engine — Takayuki Miyano / Atlas Associates**

`v0.3.0` — 5-dimension scoring · Competitor rationales · AIDD-era philosophy

</div>
