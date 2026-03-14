"""Data models for the Due Diligence Engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Red flag severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RedFlag(BaseModel):
    """A red flag detected during analysis."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: str
    title: str
    description: str
    severity: Severity
    evidence: list[str] = Field(default_factory=list)
    file_path: str | None = None
    line_number: int | None = None

    @property
    def is_deal_breaker(self) -> bool:
        return self.severity == Severity.CRITICAL


class ScoreDimension(BaseModel):
    """A single scoring dimension (0-100 scale, weighted)."""

    name: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    rationale: str
    sub_scores: dict[str, float] = Field(default_factory=dict)
    flags: list[RedFlag] = Field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


class Score(BaseModel):
    """Complete scoring result across all dimensions."""

    dimensions: list[ScoreDimension]
    red_flags: list[RedFlag] = Field(default_factory=list)
    overall_score: float = 0.0
    grade: str = ""
    recommendation: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def compute(self) -> None:
        """Compute overall score and grade from dimensions."""
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight > 0:
            self.overall_score = round(
                sum(d.weighted_score for d in self.dimensions) / total_weight, 1
            )

        # Aggregate flags
        all_flags = list(self.red_flags)
        for dim in self.dimensions:
            all_flags.extend(dim.flags)
        self.red_flags = all_flags

        # Critical flags cap the score
        critical_count = sum(1 for f in self.red_flags if f.is_deal_breaker)
        if critical_count > 0:
            self.overall_score = min(self.overall_score, 40.0)

        # Assign grade
        if self.overall_score >= 90:
            self.grade = "A"
            self.recommendation = "Strong investment candidate. Proceed with standard terms."
        elif self.overall_score >= 75:
            self.grade = "B"
            self.recommendation = "Viable with conditions. Address flagged items before closing."
        elif self.overall_score >= 60:
            self.grade = "C"
            self.recommendation = "Significant concerns. Require remediation plan with milestones."
        elif self.overall_score >= 40:
            self.grade = "D"
            self.recommendation = "High risk. Consider pass or heavily discounted terms."
        else:
            self.grade = "F"
            self.recommendation = "Do not invest. Fundamental issues detected."


class CodeAnalysisResult(BaseModel):
    """Result from code analysis pass."""

    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    api_wrapper_ratio: float = 0.0
    test_coverage_estimate: float = 0.0
    dependency_count: int = 0
    has_ci_cd: bool = False
    has_tests: bool = False
    has_documentation: bool = False
    complexity_metrics: dict[str, Any] = Field(default_factory=dict)
    red_flags: list[RedFlag] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class DocAnalysisResult(BaseModel):
    """Result from document analysis pass."""

    claims: list[dict[str, str]] = Field(default_factory=list)
    technical_claims: list[str] = Field(default_factory=list)
    performance_claims: list[str] = Field(default_factory=list)
    architecture_claims: list[str] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class GitForensicsResult(BaseModel):
    """Result from git forensics analysis."""

    total_commits: int = 0
    unique_authors: int = 0
    first_commit_date: str | None = None
    last_commit_date: str | None = None
    commit_frequency: dict[str, int] = Field(default_factory=dict)
    rush_commit_ratio: float = 0.0
    suspicious_patterns: list[str] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class ConsistencyResult(BaseModel):
    """Result from cross-reference consistency check."""

    verified_claims: list[str] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    consistency_score: float = 0.0
    red_flags: list[RedFlag] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Complete analysis result aggregating all passes."""

    project_name: str
    analysis_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    code_analysis: CodeAnalysisResult = Field(default_factory=CodeAnalysisResult)
    doc_analysis: DocAnalysisResult = Field(default_factory=DocAnalysisResult)
    git_forensics: GitForensicsResult = Field(default_factory=GitForensicsResult)
    consistency: ConsistencyResult = Field(default_factory=ConsistencyResult)
    score: Score | None = None
    model_usage: dict[str, dict[str, int]] = Field(default_factory=dict)
    total_cost_usd: float = 0.0


class PurgeCertificate(BaseModel):
    """Certificate proving secure data deletion."""

    certificate_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    analysis_id: str
    project_name: str
    purge_timestamp: datetime = Field(default_factory=datetime.utcnow)
    files_purged: int = 0
    bytes_overwritten: int = 0
    method: str = "cryptographic_erasure"
    verification_hash: str = ""
    operator: str = ""
