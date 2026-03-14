# Due Diligence Evaluation Framework

## Overview

This framework evaluates AI startups across 6 dimensions on a 100-point scale.
Each dimension has a weight reflecting its importance to investment decisions.

---

## Dimension 1: Code Originality (Weight: 25%)

**What it measures:** Is this genuine intellectual property or a thin wrapper around third-party APIs?

### Scoring Rubric

| Score Range | Description |
|-------------|-------------|
| 90-100 | Novel algorithms, custom models, significant original implementation |
| 70-89  | Substantial custom logic built on top of standard frameworks |
| 50-69  | Mix of original code and API integrations with meaningful processing |
| 30-49  | Primarily API calls with some custom business logic |
| 0-29   | Pure API wrapper with minimal custom code |

### Key Indicators
- API wrapper ratio (% of files containing only API calls)
- Presence of custom algorithms, data structures, or models
- Ratio of business logic to boilerplate/glue code
- Evidence of domain-specific innovation

### Red Flag Triggers
- **CRITICAL**: API wrapper ratio > 70% with claims of proprietary technology
- **HIGH**: No custom algorithms despite "AI-powered" marketing claims
- **MEDIUM**: Heavy reliance on a single third-party API

---

## Dimension 2: Technical Depth (Weight: 20%)

**What it measures:** Is the implementation sophisticated and production-ready?

### Scoring Rubric

| Score Range | Description |
|-------------|-------------|
| 90-100 | Enterprise-grade architecture, sophisticated algorithms, performance optimization |
| 70-89  | Well-structured codebase with good separation of concerns |
| 50-69  | Functional implementation with some architectural patterns |
| 30-49  | Basic implementation, minimal architecture |
| 0-29   | Prototype-quality code, no architecture |

### Key Indicators
- Codebase size and complexity metrics
- Language diversity appropriate to the problem domain
- Dependency management maturity
- Error handling and edge case coverage
- Performance-critical code paths

---

## Dimension 3: Engineering Maturity (Weight: 15%)

**What it measures:** Does the team follow professional engineering practices?

### Scoring Rubric

| Score Range | Description |
|-------------|-------------|
| 90-100 | Comprehensive test suite, CI/CD, documentation, monitoring |
| 70-89  | Good test coverage, automated deployment, README and docs |
| 50-69  | Some tests, basic CI, minimal documentation |
| 30-49  | Few tests, no CI/CD, sparse documentation |
| 0-29   | No tests, no automation, no documentation |

### Key Indicators
- Test suite existence and estimated coverage
- CI/CD pipeline configuration
- Documentation quality and completeness
- Code review process evidence (PR templates, review comments)
- Linting and formatting configuration

### Red Flag Triggers
- **HIGH**: No tests in a production-deployed application
- **MEDIUM**: No CI/CD with claims of "continuous deployment"

---

## Dimension 4: Claim Consistency (Weight: 15%)

**What it measures:** Do documentation and pitch claims match the actual code?

### Scoring Rubric

| Score Range | Description |
|-------------|-------------|
| 90-100 | All claims verified, conservative and accurate documentation |
| 70-89  | Most claims verified, minor discrepancies |
| 50-69  | Some claims verified, several unverifiable |
| 30-49  | Multiple contradictions between claims and code |
| 0-29   | Systematic misrepresentation of capabilities |

### Key Indicators
- Verified vs. unverified claims ratio
- Number of direct contradictions
- Presence of buzzwords without substance
- Performance claims with/without benchmarks

### Red Flag Triggers
- **CRITICAL**: Claims proprietary technology but code is an API wrapper
- **HIGH**: Performance claims with no benchmarks or evidence
- **MEDIUM**: Excessive buzzword usage without technical substance

---

## Dimension 5: Team & Process (Weight: 15%)

**What it measures:** What does the development history reveal about the team?

### Scoring Rubric

| Score Range | Description |
|-------------|-------------|
| 90-100 | Large team, consistent development over months/years, healthy patterns |
| 70-89  | Multiple contributors, steady commit history |
| 50-69  | Small team, some gaps in development, but genuine history |
| 30-49  | Single author, irregular patterns, short history |
| 0-29   | Suspicious patterns, potential fake history, last-minute cramming |

### Key Indicators
- Commit count and frequency
- Number of unique contributors
- Development timeline length
- Commit message quality
- Rush commit detection
- Bus factor risk

### Red Flag Triggers
- **CRITICAL**: Suspiciously uniform commit intervals (bot-generated)
- **HIGH**: Rush commit clusters (20+ commits in 24 hours)
- **HIGH**: Date tampering between author and commit dates
- **MEDIUM**: Single-author repository with 50+ commits

---

## Dimension 6: Security Posture (Weight: 10%)

**What it measures:** Are security practices appropriate for the domain?

### Scoring Rubric

| Score Range | Description |
|-------------|-------------|
| 90-100 | Security-first design, encryption, audit logging, vulnerability scanning |
| 70-89  | Good security practices, dependency updates, input validation |
| 50-69  | Basic security measures, some gaps |
| 30-49  | Minimal security consideration |
| 0-29   | Known vulnerabilities, hardcoded secrets, no input validation |

### Key Indicators
- Dependency count and update frequency
- Presence of security scanning in CI
- Input validation patterns
- Secret management practices
- Encryption usage where appropriate

### Red Flag Triggers
- **CRITICAL**: Hardcoded API keys or secrets in repository
- **HIGH**: Known vulnerable dependencies
- **MEDIUM**: No input validation on user-facing endpoints

---

## Overall Grade Mapping

| Score | Grade | Recommendation |
|-------|-------|---------------|
| 90-100 | A | Strong investment candidate. Proceed with standard terms. |
| 75-89  | B | Viable with conditions. Address flagged items before closing. |
| 60-74  | C | Significant concerns. Require remediation plan with milestones. |
| 40-59  | D | High risk. Consider pass or heavily discounted terms. |
| 0-39   | F | Do not invest. Fundamental issues detected. |

## Red Flag Escalation Rules

- Any **CRITICAL** red flag caps the overall score at 40 (Grade D maximum)
- 3+ **HIGH** red flags cap the score at 60 (Grade C maximum)
- Red flags from the **Claim Consistency** dimension carry extra weight as they indicate potential misrepresentation
