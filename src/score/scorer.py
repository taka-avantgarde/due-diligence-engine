"""100-point scoring engine with 6 dimensions and RED FLAG detection.

Dimensions (weights sum to 1.0):
1. Code Originality     (0.25) - Is this real IP or an API wrapper?
2. Technical Depth      (0.20) - Implementation sophistication
3. Engineering Maturity (0.15) - CI/CD, tests, code quality
4. Claim Consistency    (0.15) - Do docs match code?
5. Team & Process       (0.15) - Git history, bus factor
6. Security Posture     (0.10) - Security practices
"""

from __future__ import annotations

from src.models import (
    AnalysisResult,
    RedFlag,
    Score,
    ScoreDimension,
    Severity,
)


# Dimension definitions with weights
DIMENSIONS = {
    "code_originality": {
        "name": "Code Originality",
        "weight": 0.25,
    },
    "technical_depth": {
        "name": "Technical Depth",
        "weight": 0.20,
    },
    "engineering_maturity": {
        "name": "Engineering Maturity",
        "weight": 0.15,
    },
    "claim_consistency": {
        "name": "Claim Consistency",
        "weight": 0.15,
    },
    "team_process": {
        "name": "Team & Process",
        "weight": 0.15,
    },
    "security_posture": {
        "name": "Security Posture",
        "weight": 0.10,
    },
}


class Scorer:
    """Computes a comprehensive due diligence score from analysis results."""

    def score(self, result: AnalysisResult) -> Score:
        """Compute the full score from an AnalysisResult.

        Args:
            result: The complete analysis result.

        Returns:
            Score object with dimensions, red flags, grade, and recommendation.
        """
        dimensions = [
            self._score_code_originality(result),
            self._score_technical_depth(result),
            self._score_engineering_maturity(result),
            self._score_claim_consistency(result),
            self._score_team_process(result),
            self._score_security_posture(result),
        ]

        # Collect all red flags from all sources
        all_flags: list[RedFlag] = []
        all_flags.extend(result.code_analysis.red_flags)
        all_flags.extend(result.doc_analysis.red_flags)
        all_flags.extend(result.git_forensics.red_flags)
        all_flags.extend(result.consistency.red_flags)

        score = Score(dimensions=dimensions, red_flags=all_flags)
        score.compute()
        return score

    def _score_code_originality(self, result: AnalysisResult) -> ScoreDimension:
        """Score code originality (0-100). High API wrapper ratio = low score."""
        code = result.code_analysis
        base_score = 100.0

        # API wrapper ratio penalty (major factor)
        if code.api_wrapper_ratio > 0.7:
            base_score -= 60
        elif code.api_wrapper_ratio > 0.5:
            base_score -= 40
        elif code.api_wrapper_ratio > 0.3:
            base_score -= 20
        elif code.api_wrapper_ratio > 0.1:
            base_score -= 10

        # Minimal codebase penalty
        if code.total_lines < 500:
            base_score -= 20
        elif code.total_lines < 2000:
            base_score -= 10

        # Thin wrapper findings penalty
        wrapper_findings = sum(
            1 for f in code.findings if "thin API wrapper" in f.lower()
        )
        base_score -= min(wrapper_findings * 5, 20)

        base_score = max(base_score, 0)

        rationale_parts = []
        if code.api_wrapper_ratio > 0.3:
            rationale_parts.append(
                f"API wrapper ratio of {code.api_wrapper_ratio:.0%} indicates "
                f"limited original implementation."
            )
        if code.total_lines < 2000:
            rationale_parts.append(
                f"Small codebase ({code.total_lines} lines) for a production product."
            )
        if not rationale_parts:
            rationale_parts.append("Codebase shows signs of genuine implementation.")

        return ScoreDimension(
            name=DIMENSIONS["code_originality"]["name"],
            score=base_score,
            weight=DIMENSIONS["code_originality"]["weight"],
            rationale=" ".join(rationale_parts),
            sub_scores={
                "api_wrapper_ratio": max(0, 100 - code.api_wrapper_ratio * 100),
                "codebase_size": min(100, code.total_lines / 100),
            },
            flags=[f for f in code.red_flags if f.category == "code_originality"],
        )

    def _score_technical_depth(self, result: AnalysisResult) -> ScoreDimension:
        """Score technical implementation depth."""
        code = result.code_analysis
        base_score = 50.0  # Start neutral

        # Language diversity bonus
        if len(code.languages) >= 3:
            base_score += 10
        elif len(code.languages) >= 2:
            base_score += 5

        # Codebase size bonus
        if code.total_lines > 10000:
            base_score += 20
        elif code.total_lines > 5000:
            base_score += 15
        elif code.total_lines > 2000:
            base_score += 10

        # Dependency management
        if 5 <= code.dependency_count <= 50:
            base_score += 10
        elif code.dependency_count > 100:
            base_score -= 5  # Excessive dependencies

        # Complex findings (positive indicator)
        complexity_findings = sum(
            1 for f in code.findings if "complexity" in f.lower()
        )
        if 0 < complexity_findings <= 5:
            base_score += 5  # Some complexity is good

        base_score = min(max(base_score, 0), 100)

        return ScoreDimension(
            name=DIMENSIONS["technical_depth"]["name"],
            score=base_score,
            weight=DIMENSIONS["technical_depth"]["weight"],
            rationale=(
                f"Codebase has {code.total_lines} lines across "
                f"{len(code.languages)} languages with {code.dependency_count} dependencies."
            ),
            sub_scores={
                "codebase_size": min(100, code.total_lines / 100),
                "language_diversity": min(100, len(code.languages) * 25),
            },
        )

    def _score_engineering_maturity(self, result: AnalysisResult) -> ScoreDimension:
        """Score engineering practices maturity."""
        code = result.code_analysis
        base_score = 0.0

        if code.has_tests:
            base_score += 30
        if code.has_ci_cd:
            base_score += 30
        if code.has_documentation:
            base_score += 20

        # File count as proxy for project structure
        if code.total_files > 20:
            base_score += 10
        if code.total_files > 50:
            base_score += 10

        base_score = min(base_score, 100)

        rationale_parts = []
        if code.has_tests:
            rationale_parts.append("Has test suite.")
        else:
            rationale_parts.append("No tests detected.")
        if code.has_ci_cd:
            rationale_parts.append("CI/CD configured.")
        else:
            rationale_parts.append("No CI/CD pipeline.")
        if code.has_documentation:
            rationale_parts.append("Documentation present.")
        else:
            rationale_parts.append("Minimal documentation.")

        return ScoreDimension(
            name=DIMENSIONS["engineering_maturity"]["name"],
            score=base_score,
            weight=DIMENSIONS["engineering_maturity"]["weight"],
            rationale=" ".join(rationale_parts),
            sub_scores={
                "tests": 100 if code.has_tests else 0,
                "ci_cd": 100 if code.has_ci_cd else 0,
                "documentation": 100 if code.has_documentation else 0,
            },
            flags=[f for f in code.red_flags if f.category in ("code_quality", "engineering_maturity")],
        )

    def _score_claim_consistency(self, result: AnalysisResult) -> ScoreDimension:
        """Score consistency between documentation claims and code evidence."""
        consistency = result.consistency
        base_score = consistency.consistency_score

        # Contradiction penalty
        base_score -= len(consistency.contradictions) * 10
        base_score = max(base_score, 0)

        return ScoreDimension(
            name=DIMENSIONS["claim_consistency"]["name"],
            score=base_score,
            weight=DIMENSIONS["claim_consistency"]["weight"],
            rationale=(
                f"{len(consistency.verified_claims)} verified, "
                f"{len(consistency.unverified_claims)} unverified, "
                f"{len(consistency.contradictions)} contradictions found."
            ),
            sub_scores={
                "verified_ratio": consistency.consistency_score,
                "contradiction_count": max(0, 100 - len(consistency.contradictions) * 20),
            },
            flags=consistency.red_flags,
        )

    def _score_team_process(self, result: AnalysisResult) -> ScoreDimension:
        """Score team capability and development process from git history."""
        git = result.git_forensics
        base_score = 50.0  # Start neutral

        # Commit history depth
        if git.total_commits > 500:
            base_score += 20
        elif git.total_commits > 100:
            base_score += 15
        elif git.total_commits > 50:
            base_score += 10
        elif git.total_commits < 10:
            base_score -= 20

        # Team size
        if git.unique_authors >= 5:
            base_score += 15
        elif git.unique_authors >= 3:
            base_score += 10
        elif git.unique_authors >= 2:
            base_score += 5
        elif git.unique_authors == 1:
            base_score -= 10

        # Rush commit penalty
        if git.rush_commit_ratio > 0.3:
            base_score -= 20
        elif git.rush_commit_ratio > 0.1:
            base_score -= 10

        # Suspicious patterns penalty
        base_score -= len(git.suspicious_patterns) * 10

        base_score = min(max(base_score, 0), 100)

        return ScoreDimension(
            name=DIMENSIONS["team_process"]["name"],
            score=base_score,
            weight=DIMENSIONS["team_process"]["weight"],
            rationale=(
                f"{git.total_commits} commits by {git.unique_authors} authors. "
                f"Rush ratio: {git.rush_commit_ratio:.0%}."
            ),
            sub_scores={
                "commit_depth": min(100, git.total_commits),
                "team_size": min(100, git.unique_authors * 20),
            },
            flags=git.red_flags,
        )

    def _score_security_posture(self, result: AnalysisResult) -> ScoreDimension:
        """Score security practices."""
        code = result.code_analysis
        base_score = 60.0  # Start slightly positive

        # Check for security-related red flags
        security_flags = [
            f for f in code.red_flags if "security" in f.category.lower()
        ]
        base_score -= len(security_flags) * 15

        # Basic positive indicators
        if code.has_ci_cd:
            base_score += 10  # CI often includes security checks
        if code.has_tests:
            base_score += 10

        # Excessive dependencies = larger attack surface
        if code.dependency_count > 100:
            base_score -= 10
        elif code.dependency_count > 50:
            base_score -= 5

        base_score = min(max(base_score, 0), 100)

        return ScoreDimension(
            name=DIMENSIONS["security_posture"]["name"],
            score=base_score,
            weight=DIMENSIONS["security_posture"]["weight"],
            rationale=(
                f"Security assessment based on {code.dependency_count} dependencies "
                f"and {len(security_flags)} security-specific findings."
            ),
            sub_scores={
                "dependency_risk": max(0, 100 - code.dependency_count),
                "security_flags": max(0, 100 - len(security_flags) * 25),
            },
        )
