"""Main analysis orchestrator using hybrid model strategy.

Strategy: Haiku (fast scan) -> Sonnet (deep analyze) -> Opus (final judge)
This balances cost and quality by using cheaper models for initial passes
and reserving the most capable model for final judgment.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import anthropic

from src.analyze.code import CodeAnalyzer
from src.analyze.consistency import ConsistencyAnalyzer
from src.analyze.docs import DocAnalyzer
from src.analyze.git_forensics import GitForensicsAnalyzer
from src.config import MODELS, Config, estimate_cost
from src.ingest.secure_loader import SecureLoader
from src.models import AnalysisResult, RedFlag, Severity
from src.score.scorer import Scorer

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """Orchestrates the full due diligence analysis pipeline.

    Uses a three-tier model strategy:
    1. Haiku: Fast initial scan and file classification
    2. Sonnet: Deep analysis of code patterns and claims
    3. Opus: Final judgment, scoring rationale, and recommendation
    """

    def __init__(self, config: Config, loader: SecureLoader) -> None:
        self._config = config
        self._loader = loader
        self._client: anthropic.Anthropic | None = None
        self._usage: dict[str, dict[str, int]] = {
            "haiku": {"input_tokens": 0, "output_tokens": 0},
            "sonnet": {"input_tokens": 0, "output_tokens": 0},
            "opus": {"input_tokens": 0, "output_tokens": 0},
        }

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._config.anthropic_api_key)
        return self._client

    def run(
        self,
        project_name: str,
        repo_path: Path | None = None,
        skip_git: bool = False,
    ) -> AnalysisResult:
        """Execute the full analysis pipeline.

        Args:
            project_name: Name of the project being analyzed.
            repo_path: Path to git repo (for git forensics). If None, skips git analysis.
            skip_git: If True, skip git forensics entirely.

        Returns:
            Complete AnalysisResult with scores and findings.
        """
        result = AnalysisResult(project_name=project_name)

        # Phase 1: Local analysis (no API calls)
        logger.info("Phase 1: Running local analysis...")
        code_analyzer = CodeAnalyzer(self._loader)
        result.code_analysis = code_analyzer.analyze()

        doc_analyzer = DocAnalyzer(self._loader)
        result.doc_analysis = doc_analyzer.analyze()

        if not skip_git and repo_path and (repo_path / ".git").exists():
            git_analyzer = GitForensicsAnalyzer(repo_path)
            result.git_forensics = git_analyzer.analyze()

        consistency_analyzer = ConsistencyAnalyzer()
        result.consistency = consistency_analyzer.analyze(
            result.code_analysis, result.doc_analysis
        )

        # Phase 2: AI-enhanced analysis (Haiku scan -> Sonnet analyze -> Opus judge)
        if self._config.anthropic_api_key:
            logger.info("Phase 2: Running AI-enhanced analysis...")
            ai_findings = self._run_ai_analysis(result)
            self._merge_ai_findings(result, ai_findings)
        else:
            logger.warning("No API key configured. Skipping AI-enhanced analysis.")

        # Phase 3: Scoring
        logger.info("Phase 3: Computing scores...")
        scorer = Scorer()
        result.score = scorer.score(result)

        # Record usage and cost
        result.model_usage = self._usage
        result.total_cost_usd = self._compute_total_cost()

        return result

    def _run_ai_analysis(self, result: AnalysisResult) -> dict[str, Any]:
        """Run the three-tier AI analysis pipeline."""
        findings: dict[str, Any] = {
            "haiku_scan": {},
            "sonnet_analysis": {},
            "opus_judgment": {},
        }

        # Prepare summary for AI models
        summary = self._build_analysis_summary(result)

        # Tier 1: Haiku scan - fast classification and initial flags
        logger.info("  Tier 1: Haiku scan...")
        findings["haiku_scan"] = self._haiku_scan(summary)

        # Tier 2: Sonnet analysis - deep pattern analysis
        logger.info("  Tier 2: Sonnet deep analysis...")
        findings["sonnet_analysis"] = self._sonnet_analyze(summary, findings["haiku_scan"])

        # Tier 3: Opus judgment - final verdict
        logger.info("  Tier 3: Opus final judgment...")
        findings["opus_judgment"] = self._opus_judge(summary, findings["sonnet_analysis"])

        return findings

    def _haiku_scan(self, summary: str) -> dict[str, Any]:
        """Tier 1: Fast scan with Haiku for initial classification."""
        model = MODELS["haiku"]

        prompt = f"""You are a technical due diligence scanner. Quickly classify this project
and identify obvious red flags.

PROJECT ANALYSIS SUMMARY:
{summary}

Respond in JSON format:
{{
  "project_type": "api_wrapper|genuine_product|framework|library|tool",
  "complexity_level": "trivial|simple|moderate|complex|enterprise",
  "immediate_red_flags": ["flag1", "flag2"],
  "areas_needing_deep_analysis": ["area1", "area2"],
  "initial_risk_level": "low|medium|high|critical"
}}"""

        try:
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=model.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage("haiku", response.usage)
            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Haiku scan failed: {e}")
            return {"error": str(e)}

    def _sonnet_analyze(self, summary: str, haiku_result: dict) -> dict[str, Any]:
        """Tier 2: Deep analysis with Sonnet."""
        model = MODELS["sonnet"]

        prompt = f"""You are a senior technical due diligence analyst. Perform a deep analysis
of this AI startup's technology.

PROJECT ANALYSIS SUMMARY:
{summary}

INITIAL SCAN RESULTS (from fast pass):
{json.dumps(haiku_result, indent=2)}

Analyze the following dimensions in detail:
1. Code Originality: Is this genuine IP or an API wrapper?
2. Technical Depth: Is the implementation sophisticated or superficial?
3. Engineering Maturity: CI/CD, tests, documentation, code quality
4. Claim Verification: Do documentation claims match code evidence?
5. Team Capability: What does the commit history reveal about the team?
6. Security Posture: Are there security concerns?

Respond in JSON format:
{{
  "dimensions": {{
    "code_originality": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "technical_depth": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "engineering_maturity": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "claim_verification": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "team_capability": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "security_posture": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }}
  }},
  "additional_red_flags": [
    {{"title": "...", "description": "...", "severity": "critical|high|medium|low"}}
  ],
  "strengths": ["..."],
  "weaknesses": ["..."]
}}"""

        try:
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=model.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage("sonnet", response.usage)
            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Sonnet analysis failed: {e}")
            return {"error": str(e)}

    def _opus_judge(self, summary: str, sonnet_result: dict) -> dict[str, Any]:
        """Tier 3: Final judgment with Opus."""
        model = MODELS["opus"]

        prompt = f"""You are the final arbiter in a technical due diligence process for an
AI startup investment. You must deliver a definitive verdict.

PROJECT SUMMARY:
{summary}

DETAILED ANALYSIS (from deep analysis pass):
{json.dumps(sonnet_result, indent=2)}

Deliver your final judgment:
1. Overall assessment: Is this a sound technical investment?
2. Deal-breaker analysis: Are there any findings that should block investment?
3. Specific conditions: What must be addressed before/after investment?
4. Comparable analysis: How does this compare to typical startups at this stage?

Respond in JSON format:
{{
  "verdict": "strong_invest|invest_with_conditions|cautious|pass|strong_pass",
  "confidence": 0-100,
  "executive_summary": "2-3 sentence summary for investment committee",
  "deal_breakers": ["..."],
  "conditions": ["..."],
  "strengths_to_leverage": ["..."],
  "risks_to_monitor": ["..."],
  "comparable_assessment": "..."
}}"""

        try:
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=model.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage("opus", response.usage)
            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Opus judgment failed: {e}")
            return {"error": str(e)}

    def _build_analysis_summary(self, result: AnalysisResult) -> str:
        """Build a text summary of all analysis results for AI models."""
        lines = [
            f"Project: {result.project_name}",
            f"",
            f"=== CODE ANALYSIS ===",
            f"Total files: {result.code_analysis.total_files}",
            f"Total lines: {result.code_analysis.total_lines}",
            f"Languages: {result.code_analysis.languages}",
            f"API wrapper ratio: {result.code_analysis.api_wrapper_ratio:.1%}",
            f"Has tests: {result.code_analysis.has_tests}",
            f"Has CI/CD: {result.code_analysis.has_ci_cd}",
            f"Has docs: {result.code_analysis.has_documentation}",
            f"Dependencies: {result.code_analysis.dependency_count}",
            f"Code findings: {result.code_analysis.findings[:10]}",
            f"Code red flags: {len(result.code_analysis.red_flags)}",
            f"",
            f"=== DOCUMENT ANALYSIS ===",
            f"Total claims: {len(result.doc_analysis.claims)}",
            f"Performance claims: {len(result.doc_analysis.performance_claims)}",
            f"Architecture claims: {len(result.doc_analysis.architecture_claims)}",
            f"Technical claims: {len(result.doc_analysis.technical_claims)}",
            f"Doc red flags: {len(result.doc_analysis.red_flags)}",
            f"",
            f"=== GIT FORENSICS ===",
            f"Total commits: {result.git_forensics.total_commits}",
            f"Unique authors: {result.git_forensics.unique_authors}",
            f"First commit: {result.git_forensics.first_commit_date}",
            f"Last commit: {result.git_forensics.last_commit_date}",
            f"Rush commit ratio: {result.git_forensics.rush_commit_ratio:.1%}",
            f"Suspicious patterns: {result.git_forensics.suspicious_patterns}",
            f"Git red flags: {len(result.git_forensics.red_flags)}",
            f"",
            f"=== CONSISTENCY CHECK ===",
            f"Verified claims: {len(result.consistency.verified_claims)}",
            f"Unverified claims: {len(result.consistency.unverified_claims)}",
            f"Contradictions: {len(result.consistency.contradictions)}",
            f"Consistency score: {result.consistency.consistency_score:.1f}%",
            f"",
            f"=== RED FLAGS SUMMARY ===",
        ]

        all_flags = (
            result.code_analysis.red_flags
            + result.doc_analysis.red_flags
            + result.git_forensics.red_flags
            + result.consistency.red_flags
        )
        for flag in all_flags:
            lines.append(f"  [{flag.severity.value}] {flag.title}: {flag.description[:100]}")

        return "\n".join(lines)

    def _merge_ai_findings(
        self, result: AnalysisResult, ai_findings: dict[str, Any]
    ) -> None:
        """Merge AI-generated findings back into the analysis result."""
        sonnet = ai_findings.get("sonnet_analysis", {})

        # Add AI-detected red flags
        for flag_data in sonnet.get("additional_red_flags", []):
            if isinstance(flag_data, dict) and "title" in flag_data:
                severity_map = {
                    "critical": Severity.CRITICAL,
                    "high": Severity.HIGH,
                    "medium": Severity.MEDIUM,
                    "low": Severity.LOW,
                }
                result.code_analysis.red_flags.append(
                    RedFlag(
                        category="ai_detected",
                        title=flag_data.get("title", "Unknown"),
                        description=flag_data.get("description", ""),
                        severity=severity_map.get(
                            flag_data.get("severity", "medium"), Severity.MEDIUM
                        ),
                    )
                )

    def _track_usage(self, tier: str, usage: Any) -> None:
        """Track token usage for cost computation."""
        if hasattr(usage, "input_tokens"):
            self._usage[tier]["input_tokens"] += usage.input_tokens
            self._usage[tier]["output_tokens"] += usage.output_tokens

    def _compute_total_cost(self) -> float:
        """Compute total API cost across all tiers."""
        total = 0.0
        for tier, tokens in self._usage.items():
            total += estimate_cost(
                tier, tokens["input_tokens"], tokens["output_tokens"]
            )
        return round(total, 4)


def _parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON from Claude's response, handling markdown code blocks."""
    # Strip markdown code block if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"raw_response": text, "parse_error": True}
