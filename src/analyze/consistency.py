"""Cross-reference consistency checker between documentation claims and code."""

from __future__ import annotations

import re

from src.models import (
    CodeAnalysisResult,
    ConsistencyResult,
    DocAnalysisResult,
    RedFlag,
    Severity,
)


class ConsistencyAnalyzer:
    """Cross-references documentation claims against code evidence."""

    def analyze(
        self,
        code_result: CodeAnalysisResult,
        doc_result: DocAnalysisResult,
    ) -> ConsistencyResult:
        """Check consistency between what docs claim and what code shows.

        Args:
            code_result: Results from code analysis.
            doc_result: Results from document analysis.

        Returns:
            ConsistencyResult with verified/unverified claims and contradictions.
        """
        result = ConsistencyResult()

        self._check_test_claims(code_result, doc_result, result)
        self._check_architecture_claims(code_result, doc_result, result)
        self._check_ci_claims(code_result, doc_result, result)
        self._check_scale_claims(code_result, doc_result, result)
        self._check_proprietary_claims(code_result, doc_result, result)

        # Compute consistency score
        total = len(result.verified_claims) + len(result.unverified_claims)
        if total > 0:
            result.consistency_score = (
                len(result.verified_claims) / total * 100
            )
        else:
            result.consistency_score = 50.0  # neutral if no claims to verify

        # Overall contradiction flag
        if len(result.contradictions) >= 3:
            result.red_flags.append(
                RedFlag(
                    category="consistency",
                    title="Multiple documentation contradictions",
                    description=(
                        f"Found {len(result.contradictions)} contradictions between "
                        f"documentation claims and actual codebase evidence."
                    ),
                    severity=Severity.CRITICAL,
                    evidence=result.contradictions[:5],
                )
            )

        return result

    def _check_test_claims(
        self,
        code: CodeAnalysisResult,
        docs: DocAnalysisResult,
        result: ConsistencyResult,
    ) -> None:
        """Verify claims about testing."""
        test_claims = [
            c for c in docs.technical_claims
            if re.search(r"test|coverage|CI|continuous", c, re.IGNORECASE)
        ]

        for claim in test_claims:
            if code.has_tests:
                result.verified_claims.append(f"Testing claim verified: {claim[:80]}")
            else:
                result.contradictions.append(
                    f"Claims testing but no tests found: {claim[:80]}"
                )
                result.red_flags.append(
                    RedFlag(
                        category="consistency",
                        title="Test claim contradicted by code",
                        description=f"Documentation claims testing capability but no test files exist.",
                        severity=Severity.HIGH,
                        evidence=[claim[:200]],
                    )
                )

    def _check_architecture_claims(
        self,
        code: CodeAnalysisResult,
        docs: DocAnalysisResult,
        result: ConsistencyResult,
    ) -> None:
        """Verify architecture-related claims."""
        microservice_claims = [
            c for c in docs.architecture_claims
            if re.search(r"microservice|distributed|scalable", c, re.IGNORECASE)
        ]

        for claim in microservice_claims:
            # If claiming microservices but only a few files, flag it
            if code.total_files < 20:
                result.contradictions.append(
                    f"Claims distributed architecture but codebase has only "
                    f"{code.total_files} files: {claim[:80]}"
                )
            else:
                result.unverified_claims.append(
                    f"Architecture claim needs manual verification: {claim[:80]}"
                )

    def _check_ci_claims(
        self,
        code: CodeAnalysisResult,
        docs: DocAnalysisResult,
        result: ConsistencyResult,
    ) -> None:
        """Verify CI/CD claims."""
        ci_claims = [
            c for c in docs.technical_claims
            if re.search(r"CI/CD|continuous (integration|deployment|delivery)", c, re.IGNORECASE)
        ]

        for claim in ci_claims:
            if code.has_ci_cd:
                result.verified_claims.append(f"CI/CD claim verified: {claim[:80]}")
            else:
                result.contradictions.append(
                    f"Claims CI/CD but no pipeline config found: {claim[:80]}"
                )

    def _check_scale_claims(
        self,
        code: CodeAnalysisResult,
        docs: DocAnalysisResult,
        result: ConsistencyResult,
    ) -> None:
        """Verify scalability claims against code evidence."""
        scale_claims = [
            c for c in docs.performance_claims
            if re.search(r"\d+[kKmM]\+?\s*(user|request|transaction)", c, re.IGNORECASE)
        ]

        for claim in scale_claims:
            # Check if there's infrastructure code to support scale claims
            infra_indicators = any(
                f["path"] for f in code.complexity_metrics.get("files", [])
            ) if isinstance(code.complexity_metrics.get("files"), list) else False

            if not infra_indicators and code.total_files < 30:
                result.unverified_claims.append(
                    f"Scale claim unverifiable from code alone: {claim[:80]}"
                )

    def _check_proprietary_claims(
        self,
        code: CodeAnalysisResult,
        docs: DocAnalysisResult,
        result: ConsistencyResult,
    ) -> None:
        """Verify proprietary technology claims."""
        proprietary_claims = [
            c for c in docs.architecture_claims
            if re.search(r"proprietary|custom|novel|patent", c, re.IGNORECASE)
        ]

        for claim in proprietary_claims:
            if code.api_wrapper_ratio > 0.5:
                result.contradictions.append(
                    f"Claims proprietary tech but high API wrapper ratio "
                    f"({code.api_wrapper_ratio:.0%}): {claim[:80]}"
                )
                result.red_flags.append(
                    RedFlag(
                        category="consistency",
                        title="Proprietary claim vs API wrapper evidence",
                        description=(
                            f"Documentation claims proprietary technology, but "
                            f"{code.api_wrapper_ratio:.0%} of code files are API wrappers."
                        ),
                        severity=Severity.CRITICAL,
                        evidence=[claim[:200]],
                    )
                )
            else:
                result.unverified_claims.append(
                    f"Proprietary claim needs deeper review: {claim[:80]}"
                )
