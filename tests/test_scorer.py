"""Tests for the scoring engine."""

from __future__ import annotations

import pytest

from src.models import (
    AnalysisResult,
    CodeAnalysisResult,
    ConsistencyResult,
    DocAnalysisResult,
    GitForensicsResult,
    RedFlag,
    Severity,
)
from src.score.scorer import Scorer


@pytest.fixture
def scorer() -> Scorer:
    return Scorer()


def _make_result(
    total_files: int = 50,
    total_lines: int = 5000,
    api_wrapper_ratio: float = 0.1,
    has_tests: bool = True,
    has_ci_cd: bool = True,
    has_docs: bool = True,
    dependency_count: int = 20,
    total_commits: int = 200,
    unique_authors: int = 3,
    rush_commit_ratio: float = 0.0,
    consistency_score: float = 80.0,
    contradictions: int = 0,
    code_red_flags: list[RedFlag] | None = None,
    git_red_flags: list[RedFlag] | None = None,
) -> AnalysisResult:
    """Create an AnalysisResult with configurable parameters for testing."""
    return AnalysisResult(
        project_name="test-project",
        code_analysis=CodeAnalysisResult(
            total_files=total_files,
            total_lines=total_lines,
            languages={".py": 30, ".js": 15, ".ts": 5},
            api_wrapper_ratio=api_wrapper_ratio,
            has_tests=has_tests,
            has_ci_cd=has_ci_cd,
            has_documentation=has_docs,
            dependency_count=dependency_count,
            red_flags=code_red_flags or [],
        ),
        doc_analysis=DocAnalysisResult(),
        git_forensics=GitForensicsResult(
            total_commits=total_commits,
            unique_authors=unique_authors,
            rush_commit_ratio=rush_commit_ratio,
            red_flags=git_red_flags or [],
        ),
        consistency=ConsistencyResult(
            consistency_score=consistency_score,
            contradictions=["c"] * contradictions,
            verified_claims=["v"] * int(consistency_score / 10),
        ),
    )


class TestScorerBasic:
    """Basic scoring tests."""

    def test_healthy_project_scores_high(self, scorer: Scorer) -> None:
        """A project with good metrics should score 70+."""
        result = _make_result()
        score = scorer.score(result)

        assert score.overall_score >= 70
        assert score.grade in ("A", "B")

    def test_api_wrapper_scores_low(self, scorer: Scorer) -> None:
        """A project with high API wrapper ratio should score poorly on originality."""
        result = _make_result(api_wrapper_ratio=0.8, total_lines=300)
        score = scorer.score(result)

        originality = next(d for d in score.dimensions if "Originality" in d.name)
        assert originality.score < 40

    def test_no_tests_penalizes_maturity(self, scorer: Scorer) -> None:
        """Missing tests should reduce engineering maturity score."""
        with_tests = _make_result(has_tests=True)
        without_tests = _make_result(has_tests=False)

        score_with = scorer.score(with_tests)
        score_without = scorer.score(without_tests)

        maturity_with = next(d for d in score_with.dimensions if "Maturity" in d.name)
        maturity_without = next(d for d in score_without.dimensions if "Maturity" in d.name)

        assert maturity_with.score > maturity_without.score

    def test_single_author_penalized(self, scorer: Scorer) -> None:
        """Single author repository should score lower on team dimension."""
        multi = _make_result(unique_authors=5)
        single = _make_result(unique_authors=1)

        score_multi = scorer.score(multi)
        score_single = scorer.score(single)

        team_multi = next(d for d in score_multi.dimensions if "Team" in d.name)
        team_single = next(d for d in score_single.dimensions if "Team" in d.name)

        assert team_multi.score > team_single.score


class TestRedFlags:
    """Red flag detection and impact tests."""

    def test_critical_flag_caps_score(self, scorer: Scorer) -> None:
        """A critical red flag should cap the overall score at 40."""
        critical_flag = RedFlag(
            category="code_originality",
            title="Pure API wrapper",
            description="Product is entirely an API wrapper.",
            severity=Severity.CRITICAL,
        )
        result = _make_result(code_red_flags=[critical_flag])
        score = scorer.score(result)

        assert score.overall_score <= 40
        assert score.grade in ("D", "F")

    def test_multiple_red_flags_aggregated(self, scorer: Scorer) -> None:
        """All red flags from all sources should be aggregated."""
        code_flag = RedFlag(
            category="code_quality",
            title="No tests",
            description="No test files.",
            severity=Severity.MEDIUM,
        )
        git_flag = RedFlag(
            category="git",
            title="Rush commits",
            description="Dense commit clusters.",
            severity=Severity.HIGH,
        )
        result = _make_result(
            code_red_flags=[code_flag],
            git_red_flags=[git_flag],
        )
        score = scorer.score(result)

        assert len(score.red_flags) >= 2

    def test_no_red_flags_clean_result(self, scorer: Scorer) -> None:
        """A clean project should have minimal or no red flags."""
        result = _make_result()
        score = scorer.score(result)

        critical_flags = [f for f in score.red_flags if f.is_deal_breaker]
        assert len(critical_flags) == 0


class TestConsistency:
    """Consistency scoring tests."""

    def test_high_consistency_scores_well(self, scorer: Scorer) -> None:
        """High consistency score should be reflected in the dimension."""
        result = _make_result(consistency_score=90.0, contradictions=0)
        score = scorer.score(result)

        consistency_dim = next(d for d in score.dimensions if "Consistency" in d.name)
        assert consistency_dim.score >= 80

    def test_contradictions_reduce_score(self, scorer: Scorer) -> None:
        """Multiple contradictions should reduce the consistency score."""
        clean = _make_result(consistency_score=80.0, contradictions=0)
        dirty = _make_result(consistency_score=80.0, contradictions=5)

        score_clean = scorer.score(clean)
        score_dirty = scorer.score(dirty)

        cons_clean = next(d for d in score_clean.dimensions if "Consistency" in d.name)
        cons_dirty = next(d for d in score_dirty.dimensions if "Consistency" in d.name)

        assert cons_clean.score > cons_dirty.score


class TestGradeMapping:
    """Grade assignment tests."""

    def test_grade_a(self, scorer: Scorer) -> None:
        result = _make_result(
            total_lines=15000,
            unique_authors=5,
            total_commits=500,
            consistency_score=95.0,
        )
        score = scorer.score(result)
        # Should be A or B for a very healthy project
        assert score.grade in ("A", "B")

    def test_grade_f_for_terrible_project(self, scorer: Scorer) -> None:
        critical = RedFlag(
            category="test",
            title="Fake",
            description="Everything is fake.",
            severity=Severity.CRITICAL,
        )
        result = _make_result(
            total_files=2,
            total_lines=50,
            api_wrapper_ratio=0.9,
            has_tests=False,
            has_ci_cd=False,
            has_docs=False,
            total_commits=3,
            unique_authors=1,
            consistency_score=10.0,
            contradictions=5,
            code_red_flags=[critical],
        )
        score = scorer.score(result)
        assert score.grade in ("D", "F")
        assert score.overall_score <= 40

    def test_score_compute_is_idempotent(self, scorer: Scorer) -> None:
        """Calling score() twice should give the same result."""
        result = _make_result()
        score1 = scorer.score(result)
        score2 = scorer.score(result)
        assert score1.overall_score == score2.overall_score
        assert score1.grade == score2.grade


class TestWeights:
    """Verify dimension weights sum to 1.0."""

    def test_weights_sum_to_one(self, scorer: Scorer) -> None:
        result = _make_result()
        score = scorer.score(result)
        total_weight = sum(d.weight for d in score.dimensions)
        assert abs(total_weight - 1.0) < 0.01

    def test_all_six_dimensions_present(self, scorer: Scorer) -> None:
        result = _make_result()
        score = scorer.score(result)
        assert len(score.dimensions) == 6
