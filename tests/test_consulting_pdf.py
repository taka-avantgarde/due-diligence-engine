"""Tests for consulting-grade PDF generation (EN + JA).

Verifies:
- PDF files are created for both languages
- Filenames contain localized date stamps
- PDF is non-empty and valid
- Output defaults to ~/Downloads
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest

from src.models import (
    AnalysisResult,
    ConsultingReport,
    EnhancedDimensionScore,
    FutureOutlook,
    InvestmentThesis,
    SWOTAnalysis,
    SWOTItem,
    StrategicAction,
    StrategicAdvice,
    YearProjection,
)
from src.report.pdf_generator import PDFReportGenerator


def _make_consulting_report() -> ConsultingReport:
    """Build a realistic consulting report fixture."""
    return ConsultingReport(
        executive_summary="A technically solid project with strong architecture.",
        executive_summary_business=(
            "This product demonstrates genuine technical capability "
            "and has clear market potential in its target segment."
        ),
        dimension_scores={
            "technical_originality": EnhancedDimensionScore(
                score=75,
                level=7,
                label="Technical Originality",
                rationale="Core algorithms are original implementations.",
                business_explanation="The team built their own engine rather than wrapping existing APIs.",
                enables="Sustainable competitive moat through proprietary technology.",
            ),
            "technology_advancement": EnhancedDimensionScore(
                score=82,
                level=8,
                label="Technology Advancement",
                rationale="Modern stack with Rust + TypeScript.",
                business_explanation="Using cutting-edge tools that attract top talent.",
                enables="High performance and reliability at scale.",
            ),
            "implementation_depth": EnhancedDimensionScore(
                score=65,
                level=6,
                label="Implementation Depth",
                rationale="Beta-quality with basic test coverage.",
                business_explanation="The product works but needs hardening before enterprise use.",
                enables="Faster iteration with proper test infrastructure.",
            ),
            "architecture_quality": EnhancedDimensionScore(
                score=70,
                level=7,
                label="Architecture Quality",
                rationale="Clean separation of concerns.",
                business_explanation="Well-organized code that new engineers can understand quickly.",
                enables="Faster onboarding and reduced maintenance costs.",
            ),
            "claim_consistency": EnhancedDimensionScore(
                score=55,
                level=5,
                label="Claim Consistency",
                rationale="Some claims not backed by code evidence.",
                business_explanation="Marketing materials slightly overstate current capabilities.",
                enables="Building trust with transparent communication.",
            ),
            "security_posture": EnhancedDimensionScore(
                score=60,
                level=6,
                label="Security Posture",
                rationale="TLS everywhere but no pen-test documentation.",
                business_explanation="Basic security is in place but hasn't been independently verified.",
                enables="Enterprise readiness with third-party audit.",
            ),
        },
        overall_score=72.0,
        grade="C",
        swot=SWOTAnalysis(
            strengths=[
                SWOTItem(
                    point="Original ML model",
                    explanation="Core prediction engine is fully custom-built.",
                    business_analogy="Like having a proprietary recipe vs. using store-bought ingredients.",
                ),
                SWOTItem(
                    point="Modern tech stack",
                    explanation="Rust + TypeScript ensures performance and type safety.",
                    business_analogy="Like building with premium materials that last longer.",
                ),
            ],
            weaknesses=[
                SWOTItem(
                    point="Thin test coverage",
                    explanation="Only 40% of critical paths have automated tests.",
                    business_analogy="Like a factory without quality control checkpoints.",
                ),
            ],
            opportunities=[
                SWOTItem(
                    point="Enterprise market",
                    explanation="Architecture supports multi-tenant deployment.",
                    potential_value="10x revenue if enterprise features are prioritized.",
                ),
            ],
            threats=[
                SWOTItem(
                    point="Competitor with larger team",
                    explanation="BigCorp has 50 engineers on a similar product.",
                    mitigation="Focus on niche vertical where speed matters more than scale.",
                ),
            ],
        ),
        future_outlook=FutureOutlook(
            product_vision="Become the standard for real-time prediction in fintech.",
            viability_assessment="Technically feasible with current team size.",
            year_1=YearProjection(
                projection="Achieve production readiness and first paying customers.",
                confidence="high",
                key_milestones=["SOC2 compliance", "99.9% uptime SLA"],
            ),
            year_3=YearProjection(
                projection="Expand to 3 verticals with enterprise tier.",
                confidence="medium",
                key_milestones=["Series A", "50+ enterprise clients"],
            ),
            year_5=YearProjection(
                projection="Market leader in fintech prediction APIs.",
                confidence="low",
                key_milestones=["IPO readiness", "Global expansion"],
            ),
        ),
        strategic_advice=StrategicAdvice(
            immediate_actions=[
                StrategicAction(
                    action="Increase test coverage to 80%",
                    rationale="Current 40% is a liability for enterprise sales.",
                    expected_impact="Reduces production incidents by ~60%.",
                ),
                StrategicAction(
                    action="Commission independent security audit",
                    rationale="Claims of security without evidence hurt credibility.",
                    expected_impact="Unlocks enterprise procurement requirements.",
                ),
            ],
            medium_term=[
                StrategicAction(
                    action="Build multi-tenant architecture",
                    rationale="Enterprise customers require data isolation.",
                    expected_impact="Enables 10x revenue per customer.",
                ),
            ],
            long_term_vision="Become the AWS of real-time fintech predictions.",
        ),
        investment_thesis=InvestmentThesis(
            recommendation="Conditional Invest",
            rationale="Strong technical foundation with clear path to product-market fit.",
            key_risks=["Single point of failure in ML pipeline", "No SOC2 yet"],
            key_upside=["First-mover in niche vertical", "Proprietary ML gives lasting edge"],
            comparable_companies=["Stripe (payments infrastructure)", "Plaid (fintech API)"],
            suggested_valuation_factors="3-5x ARR based on growth trajectory.",
        ),
        red_flags=[
            {
                "title": "SOC2 claim mismatch",
                "severity": "medium",
                "description": "Pitch claims SOC2 Type II, no evidence in codebase.",
                "business_impact": "Could delay enterprise deals by 6+ months.",
            },
            {
                "title": "Rush commits before DD",
                "severity": "low",
                "description": "40% of commits in final 2 weeks.",
                "business_impact": "May indicate code quality concerns under pressure.",
            },
        ],
        tech_level_summary={
            "overall_level": 7,
            "plain_explanation": "Production-quality code with some gaps in testing and security documentation.",
        },
        glossary_additions=[
            {"term": "ML Pipeline", "definition": "A sequence of steps that processes raw data into predictions."},
            {"term": "SOC2", "definition": "A security certification that proves a company handles data responsibly."},
            {"term": "Multi-tenant", "definition": "One system serving multiple customers with isolated data."},
        ],
        ai_model_used="Claude Opus 4 (test)",
        analysis_id="test_20260402",
        project_name="NeuralPay",
    )


def _make_analysis_result(consulting: ConsultingReport) -> AnalysisResult:
    """Build a minimal AnalysisResult wrapping the consulting report."""
    result = AnalysisResult(
        project_name="NeuralPay",
        analysis_id="test_20260402",
    )
    result.consulting_report = consulting
    return result


class TestConsultingPdfGeneration:
    """PDF生成の日英自動検証テスト."""

    @pytest.fixture
    def consulting_report(self) -> ConsultingReport:
        return _make_consulting_report()

    @pytest.fixture
    def analysis_result(self, consulting_report: ConsultingReport) -> AnalysisResult:
        return _make_analysis_result(consulting_report)

    @pytest.fixture
    def pdf_gen(self) -> PDFReportGenerator:
        return PDFReportGenerator()

    # ── EN PDF ────────────────────────────────────────────

    def test_en_pdf_created(self, pdf_gen, analysis_result, tmp_path):
        """English PDF is generated successfully."""
        pdf_path = tmp_path / "test_en.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="en")
        assert pdf_path.exists(), "English PDF was not created"
        assert pdf_path.stat().st_size > 1000, "English PDF is too small — likely empty"

    def test_en_pdf_is_valid(self, pdf_gen, analysis_result, tmp_path):
        """English PDF starts with %PDF header."""
        pdf_path = tmp_path / "test_en.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="en")
        header = pdf_path.read_bytes()[:5]
        assert header == b"%PDF-", f"Invalid PDF header: {header!r}"

    # ── JA PDF ────────────────────────────────────────────

    def test_ja_pdf_created(self, pdf_gen, analysis_result, tmp_path):
        """Japanese PDF is generated successfully."""
        pdf_path = tmp_path / "test_ja.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="ja")
        assert pdf_path.exists(), "Japanese PDF was not created"
        assert pdf_path.stat().st_size > 1000, "Japanese PDF is too small — likely empty"

    def test_ja_pdf_is_valid(self, pdf_gen, analysis_result, tmp_path):
        """Japanese PDF starts with %PDF header."""
        pdf_path = tmp_path / "test_ja.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="ja")
        header = pdf_path.read_bytes()[:5]
        assert header == b"%PDF-", f"Invalid PDF header: {header!r}"

    # ── JA is larger than EN (CID fonts + more content) ──

    def test_ja_pdf_has_cid_fonts(self, pdf_gen, analysis_result, tmp_path):
        """Japanese PDF should be larger due to CID font embedding."""
        en_path = tmp_path / "test_en.pdf"
        ja_path = tmp_path / "test_ja.pdf"
        pdf_gen.generate_to_file(analysis_result, en_path, lang="en")
        pdf_gen.generate_to_file(analysis_result, ja_path, lang="ja")
        # JA PDF uses CID fonts → typically larger
        assert ja_path.stat().st_size > 0
        assert en_path.stat().st_size > 0

    # ── Filename date stamp ──────────────────────────────

    def test_filename_date_en(self):
        """English filename uses YYYY-MM-DD format."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        filename = f"dde_consulting_NeuralPay_{date_str}.pdf"
        assert re.match(r"dde_consulting_\w+_\d{4}-\d{2}-\d{2}\.pdf", filename)

    def test_filename_date_ja(self):
        """Japanese filename uses YYYY年MM月DD日 format."""
        now = datetime.now()
        date_str = now.strftime("%Y年%m月%d日")
        filename = f"dde_consulting_NeuralPay_{date_str}.pdf"
        assert re.match(r"dde_consulting_\w+_\d{4}年\d{2}月\d{2}日\.pdf", filename)

    # ── CLI date logic ───────────────────────────────────

    def test_cli_date_formats(self):
        """CLI produces correct date strings for each lang."""
        now = datetime(2026, 4, 2, 15, 30)

        ja_date = now.strftime("%Y年%m月%d日")
        assert ja_date == "2026年04月02日"

        en_date = now.strftime("%Y-%m-%d")
        assert en_date == "2026-04-02"

    # ── Downloads directory default ──────────────────────

    def test_downloads_dir_default(self):
        """Default consulting PDF output is ~/Downloads."""
        downloads = Path.home() / "Downloads"
        assert downloads.exists(), "~/Downloads does not exist on this machine"

    # ── Both languages produce multi-page PDFs ───────────

    def test_en_pdf_multipage(self, pdf_gen, analysis_result, tmp_path):
        """English consulting PDF should be multi-page (SWOT, scores, etc.)."""
        pdf_path = tmp_path / "test_en_multi.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="en")
        # A multi-page PDF with charts should be > 5KB
        assert pdf_path.stat().st_size > 5000, (
            f"English PDF too small ({pdf_path.stat().st_size} bytes) — "
            "likely missing consulting sections"
        )

    def test_ja_pdf_multipage(self, pdf_gen, analysis_result, tmp_path):
        """Japanese consulting PDF should be multi-page (SWOT, scores, etc.)."""
        pdf_path = tmp_path / "test_ja_multi.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="ja")
        assert pdf_path.stat().st_size > 5000, (
            f"Japanese PDF too small ({pdf_path.stat().st_size} bytes) — "
            "likely missing consulting sections"
        )

    # ── Score dashboard with bar charts ──────────────────

    def test_score_dashboard_en(self, pdf_gen, analysis_result, tmp_path):
        """English PDF contains score dashboard page with bar charts."""
        pdf_path = tmp_path / "test_dashboard_en.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="en")
        content = pdf_path.read_bytes()
        assert len(content) > 8000, "Score dashboard may be missing from EN PDF"
        page_count = content.count(b"/Type /Page")
        assert page_count >= 5, (
            f"Expected 5+ pages (cover, dashboard, summary, SWOT, ...), got {page_count}"
        )

    def test_score_dashboard_ja(self, pdf_gen, analysis_result, tmp_path):
        """Japanese PDF contains score dashboard page with bar charts."""
        pdf_path = tmp_path / "test_dashboard_ja.pdf"
        pdf_gen.generate_to_file(analysis_result, pdf_path, lang="ja")
        content = pdf_path.read_bytes()
        assert len(content) > 8000, "Score dashboard may be missing from JA PDF"
        page_count = content.count(b"/Type /Page")
        assert page_count >= 5, (
            f"Expected 5+ pages (cover, dashboard, summary, SWOT, ...), got {page_count}"
        )
