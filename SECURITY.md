# Security Policy

## Supported Versions

Only the latest release on `main` is actively maintained. Please always use the latest version.

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

### Preferred: Private Disclosure

- **Email**: security@atlasassociates.io
- **Subject**: `[DDE Security] <short description>`
- **Response SLA**: 48 hours for initial acknowledgment

### Alternative: GitHub Security Advisory

Use the ["Report a vulnerability"](https://github.com/taka-avantgarde/Due-diligence-engine/security/advisories/new) button on the Security tab to submit privately.

## Scope

### In Scope
- `dde` CLI commands (`prompt`, `analyze`, `report`, `serve`)
- PDF generation pipeline
- BYOK API key handling
- Dependency supply chain
- GitHub Actions workflows

### Out of Scope
- Issues in upstream dependencies (report to the respective project)
- Issues requiring physical access to the developer's machine
- Social engineering attacks
- Denial-of-service against `due-diligence-engine.web.app` (being deprecated)

## Disclosure Policy

- **Coordinated Disclosure**: 90 days from initial report to public disclosure
- Faster disclosure possible if patch released sooner
- Credit given in SECURITY_HALL_OF_FAME.md (opt-in)

## What to Include in a Report

1. **Description**: What is the vulnerability?
2. **Impact**: What can an attacker do?
3. **Reproduction**: Minimal steps to reproduce
4. **Affected versions**: Which DDE releases are affected
5. **Suggested fix**: (Optional) How you'd fix it

## Security Measures Already in Place

- ✅ `.env` in `.gitignore` — API keys never committed
- ✅ BYOK keys stay in memory only (never written to disk)
- ✅ `dde prompt` runs entirely locally (no network calls to external services)
- ✅ Dependabot for dependency updates
- ✅ CodeQL static analysis on every PR
- ✅ `pip-audit` and `safety` scans in CI
- ✅ Signed releases via Sigstore (planned)
- ✅ Branch protection on `main` (PR + review required)

## Bug Bounty

We currently do not operate a paid bug bounty program, but acknowledge contributions publicly.

## Cryptographic Commitments

DDE itself does not handle encrypted data. However:

- BYOK API keys are transmitted only to the respective AI provider (Anthropic / Google / OpenAI) over TLS 1.3
- Generated PDF reports contain no user source code — only findings
- PDF metadata does not include user identifiers beyond what the user explicitly provides

---

**Maintainer**: Takayuki Miyano / Atlas Associates
**Last Updated**: 2026-04-21
