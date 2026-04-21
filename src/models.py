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
    tech_ratings: list["TechLevelRating"] = Field(default_factory=list)
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


class AIProviderResult(BaseModel):
    """単一AIプロバイダーの分析結果。

    各プロバイダー（Claude/Gemini/ChatGPT）が6軸スコア・レッドフラグ・
    判定結果を独立して返す。複数プロバイダーの結果をクロス検証に使用。
    """

    provider: str  # "claude", "gemini", "chatgpt"
    model_id: str
    dimension_scores: dict[str, float] = Field(default_factory=dict)  # 6軸スコア (0-100)
    red_flags: list[RedFlag] = Field(default_factory=list)
    verdict: str = ""  # "strong_invest", "invest_with_conditions", etc.
    confidence: float = 0.0
    executive_summary: str = ""
    usage: dict[str, int] = Field(default_factory=dict)  # input_tokens, output_tokens
    cost_usd: float = 0.0
    error: str | None = None  # エラー時のメッセージ


class SiteClaimModel(BaseModel):
    """サイトから抽出した主張。"""
    category: str = ""
    claim: str = ""
    source_url: str = ""
    confidence: float = 0.5


class SiteAnalysisModel(BaseModel):
    """サイト分析結果（AnalysisResultに埋め込み用）。"""
    site_url: str = ""
    pages_analyzed: int = 0
    claims: list[SiteClaimModel] = Field(default_factory=list)
    technologies_mentioned: list[str] = Field(default_factory=list)
    team_info: dict[str, Any] = Field(default_factory=dict)
    traction_claims: list[str] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class CrossValidationModel(BaseModel):
    """サイト vs コードのクロス検証結果。"""
    verified_claims: list[dict[str, str]] = Field(default_factory=list)
    unverified_claims: list[dict[str, str]] = Field(default_factory=list)
    contradictions: list[dict[str, str]] = Field(default_factory=list)
    exaggerations: list[dict[str, str]] = Field(default_factory=list)
    credibility_score: float = 50.0
    red_flags: list[RedFlag] = Field(default_factory=list)
    summary: str = ""


class AnalysisResult(BaseModel):
    """Complete analysis result aggregating all passes."""

    project_name: str
    analysis_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    code_analysis: CodeAnalysisResult = Field(default_factory=CodeAnalysisResult)
    doc_analysis: DocAnalysisResult = Field(default_factory=DocAnalysisResult)
    git_forensics: GitForensicsResult = Field(default_factory=GitForensicsResult)
    consistency: ConsistencyResult = Field(default_factory=ConsistencyResult)
    site_analysis: SiteAnalysisModel | None = None  # サイト分析結果
    cross_validation: CrossValidationModel | None = None  # サイト vs コード クロス検証
    score: Score | None = None
    ai_results: dict[str, AIProviderResult] = Field(default_factory=dict)  # provider名→結果
    model_usage: dict[str, dict[str, int]] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    consulting_report: ConsultingReport | None = None


class TechLevel(BaseModel):
    """A single level in the 10-level technology rating scale."""

    level: int = Field(ge=1, le=10)
    label: str
    description: str


class TechLevelRating(BaseModel):
    """Technology level rating for a single dimension."""

    dimension: str
    dimension_ja: str = ""
    level: int = Field(ge=1, le=10)
    label: str
    description: str
    criteria: list[TechLevel] = Field(default_factory=list)

    @property
    def score_100(self) -> float:
        """Convert 10-level to 100-point scale."""
        return self.level * 10.0


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


# ---------------------------------------------------------------------------
# Consulting Report models (for IDE AI-generated evaluation)
# ---------------------------------------------------------------------------


class SWOTItem(BaseModel):
    """A single item in a SWOT analysis quadrant."""

    point: str
    explanation: str
    business_analogy: str = ""
    business_impact: str = ""
    potential_value: str = ""
    mitigation: str = ""


class SWOTAnalysis(BaseModel):
    """SWOT analysis result."""

    strengths: list[SWOTItem] = Field(default_factory=list)
    weaknesses: list[SWOTItem] = Field(default_factory=list)
    opportunities: list[SWOTItem] = Field(default_factory=list)
    threats: list[SWOTItem] = Field(default_factory=list)


class YearProjection(BaseModel):
    """Projection for a specific time horizon."""

    projection: str
    confidence: str = "medium"
    key_milestones: list[str] = Field(default_factory=list)


class FutureOutlook(BaseModel):
    """Product/service future outlook assessment."""

    product_vision: str = ""
    viability_assessment: str = ""
    year_1: YearProjection | None = None
    year_3: YearProjection | None = None
    year_5: YearProjection | None = None


class StrategicAction(BaseModel):
    """A single strategic recommendation."""

    action: str
    rationale: str
    expected_impact: str


class StrategicAdvice(BaseModel):
    """Prioritized strategic recommendations."""

    immediate_actions: list[StrategicAction] = Field(default_factory=list)
    medium_term: list[StrategicAction] = Field(default_factory=list)
    long_term_vision: str = ""


class InvestmentThesis(BaseModel):
    """Investment recommendation with rationale."""

    recommendation: str = ""
    rationale: str = ""
    key_risks: list[str] = Field(default_factory=list)
    key_upside: list[str] = Field(default_factory=list)
    comparable_companies: list[str] = Field(default_factory=list)
    suggested_valuation_factors: str = ""


class EnhancedDimensionScore(BaseModel):
    """AI-generated score for a single evaluation dimension."""

    score: float = Field(default=0.0, ge=0, le=100)
    level: int = Field(default=1, ge=1, le=10)
    label: str = ""
    rationale: str = ""
    business_explanation: str = ""
    enables: str = ""


# ---------------------------------------------------------------------------
# Site Verification models
# ---------------------------------------------------------------------------

class SiteVerificationItem(BaseModel):
    """A single site verification check (scored 0-100)."""

    item_key: str = ""          # e.g. "feature_claim_match"
    item_name: str = ""         # EN label
    item_name_ja: str = ""      # JA label
    score: float = Field(default=0.0, ge=0, le=100)
    confidence: str = "medium"  # "high" | "medium" | "low"
    rationale: str = ""
    evidence: list[str] = Field(default_factory=list)


class SiteVerificationReport(BaseModel):
    """Cross-reference of website claims vs codebase evidence."""

    urls_analyzed: list[str] = Field(default_factory=list)
    items: list[SiteVerificationItem] = Field(default_factory=list)
    overall_credibility: float = 0.0
    summary: str = ""


# ---------------------------------------------------------------------------
# Competitive Analysis models
# ---------------------------------------------------------------------------

class CompetitorDataPoint(BaseModel):
    """A single company's position on a competitive chart."""

    name: str = ""
    x: float = 0.0       # 0-100 range
    y: float = 0.0       # 0-100 range
    z: float = 0.0       # bubble size for 3D charts, 0 otherwise
    is_target: bool = False


class MarketChart(BaseModel):
    """A single chart for a market segment."""

    chart_type: str = ""  # magic_quadrant | bcg_matrix | mckinsey_moat | security_posture | data_governance | gs_risk_return | bubble_3d
    title: str = ""
    title_ja: str = ""
    x_axis_label: str = ""
    x_axis_label_ja: str = ""
    y_axis_label: str = ""
    y_axis_label_ja: str = ""
    x_axis_rationale: str = ""
    x_axis_rationale_ja: str = ""
    y_axis_rationale: str = ""
    y_axis_rationale_ja: str = ""
    data_points: list[CompetitorDataPoint] = Field(default_factory=list)


class MarketPosition(BaseModel):
    """Competitive analysis for a single market segment."""

    market_name: str = ""
    market_name_ja: str = ""
    charts: list[MarketChart] = Field(default_factory=list)


class CompetitiveAnalysis(BaseModel):
    """Complete competitive analysis across multiple market segments."""

    target_company: str = ""
    home_country: str = ""
    markets: list[MarketPosition] = Field(default_factory=list)


class ConsultingReport(BaseModel):
    """Complete AI-generated consulting report parsed from structured JSON.

    This is populated by the IDE AI (Claude Code, Cursor, etc.) when
    ``dde prompt --pdf`` is used, then fed back to ``dde report --consulting``
    for PDF generation.
    """

    executive_summary: str = ""
    executive_summary_business: str = ""
    dimension_scores: dict[str, EnhancedDimensionScore] = Field(
        default_factory=dict,
    )
    overall_score: float = 0.0
    grade: str = ""
    swot: SWOTAnalysis = Field(default_factory=SWOTAnalysis)
    future_outlook: FutureOutlook = Field(default_factory=FutureOutlook)
    strategic_advice: StrategicAdvice = Field(default_factory=StrategicAdvice)
    investment_thesis: InvestmentThesis = Field(
        default_factory=InvestmentThesis,
    )
    red_flags: list[dict[str, Any]] = Field(default_factory=list)
    tech_level_summary: dict[str, Any] = Field(default_factory=dict)
    glossary_additions: list[dict[str, str]] = Field(default_factory=list)
    ai_model_used: str = ""
    analysis_id: str = ""
    project_name: str = ""
    site_verification: SiteVerificationReport | None = None
    competitive_analysis: CompetitiveAnalysis | None = None
    atlas_four_axis: "AtlasFourAxisEvaluation | None" = None
    implementation_matrix: "ImplementationMatrix | None" = None


# ─────────────────────────────────────────────────────────────
# Task C: Atlas 最適化評価（4軸並列評価）
# 既存6次元スコアは完全保持、その上に「Arc エンジニアリング哲学」による
# 並列評価軸を追加。合計スコアは従来6次元のみで算出（後方互換性100%）。
# ─────────────────────────────────────────────────────────────


class AtlasAxisSubItem(BaseModel):
    """Security Strength 軸のサブ項目（非公開重み、業界別動的調整）."""

    key: str = ""  # "encryption" | "privacy" | "posture" | "comms" | "layers"
    name_en: str = ""
    name_ja: str = ""
    score: float = Field(default=0.0, ge=0, le=100)
    level: int = Field(default=1, ge=1, le=10)
    weight_pct: float = 0.0  # 非公開、PDFバー比率としてのみ使用
    rationale: str = ""


class AtlasAxisScore(BaseModel):
    """Atlas 4軸のうちの1軸."""

    axis_key: str = ""  # "performance" | "stability" | "lightweight" | "security"
    name_en: str = ""
    name_ja: str = ""
    weight_pct: float = 0.0  # 25 / 20 / 5 / 50
    score: float = Field(default=0.0, ge=0, le=100)
    level: int = Field(default=1, ge=1, le=10)
    rationale: str = ""
    # security 軸のみサブ項目を持つ（暗号化30% / プライバシー8% / 態勢2% / 通信7% / レイヤー3%）
    sub_items: list[AtlasAxisSubItem] = Field(default_factory=list)


class AtlasFourAxisEvaluation(BaseModel):
    """Atlas 4軸最適化評価の全体構造."""

    axes: list[AtlasAxisScore] = Field(default_factory=list)
    overall_score: float = 0.0  # 4軸加重合計（並列参考値、既存スコアとは独立）
    industry_context: str = ""  # "messaging" | "fintech" | "medical" | "saas" | "gaming" | "other"
    summary: str = ""
    summary_ja: str = ""


# ─────────────────────────────────────────────────────────────
# Task D: Implementation Capability Matrix（第8競合チャート）
# 約30項目 × 5-10社の実装有無チェック表。4状態 (✓ / △ / ✗ / ?)。
# 暗号化カテゴリに11項目を集中させ、Arc の技術的優位性を可視化。
# ─────────────────────────────────────────────────────────────


class ImplementationStatus(str, Enum):
    """実装状況の4状態."""

    VERIFIED = "verified"              # ✓ 公開資料で実装確認済み
    CLAIMED = "claimed"                # △ 主張あり・検証未完
    NOT_IMPLEMENTED = "not_implemented"  # ✗ 明示的に未対応
    UNKNOWN = "unknown"                # ? 公開情報で判定不能


class CompanyImplementationStatus(BaseModel):
    """1社 × 1項目の実装状況."""

    company_name: str = ""
    status: ImplementationStatus = ImplementationStatus.UNKNOWN
    evidence: str = ""  # URL / citation / reasoning


class MatrixItem(BaseModel):
    """マトリックスの1行（1評価項目）."""

    category: str = ""  # "performance" | "stability" | "lightweight" | "encryption" | "privacy" | "posture" | "comms" | "layers"
    item_key: str = ""
    item_en: str = ""
    item_ja: str = ""
    statuses: list[CompanyImplementationStatus] = Field(default_factory=list)


class ImplementationMatrix(BaseModel):
    """実装能力マトリックス全体."""

    target_company: str = ""
    competitors: list[str] = Field(default_factory=list)  # 5-10社
    items: list[MatrixItem] = Field(default_factory=list)  # 約30項目
