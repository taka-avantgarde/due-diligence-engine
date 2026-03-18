"""Professional PDF report generator for due diligence reports.

Generates multi-page PDF reports using ReportLab with:
- Cover page with overall score and grade
- Executive summary
- Dimension breakdown table with scores
- Red flags section with severity indicators
- Architecture and code analysis findings
- Purge certificate page (if applicable)
- NDA compliance footer on every page
- Japanese language support via CID fonts

IMPORTANT: No source code is ever included in the PDF output.
Only findings, scores, and recommendations are reported.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.models import AnalysisResult, PurgeCertificate, Severity

logger = logging.getLogger(__name__)

# Register CID fonts for Japanese support
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

# Color palette (matching the dark theme of the web dashboard)
COLOR_BG_DARK = colors.HexColor("#0f172a")
COLOR_SURFACE = colors.HexColor("#1e293b")
COLOR_ACCENT = colors.HexColor("#38bdf8")
COLOR_GREEN = colors.HexColor("#22c55e")
COLOR_YELLOW = colors.HexColor("#eab308")
COLOR_ORANGE = colors.HexColor("#f97316")
COLOR_RED = colors.HexColor("#ef4444")
COLOR_TEXT = colors.HexColor("#1e293b")
COLOR_TEXT_DIM = colors.HexColor("#64748b")
COLOR_BORDER = colors.HexColor("#cbd5e1")
COLOR_WHITE = colors.white
COLOR_LIGHT_BG = colors.HexColor("#f8fafc")

# Severity color mapping
SEVERITY_COLORS = {
    Severity.CRITICAL: COLOR_RED,
    Severity.HIGH: COLOR_ORANGE,
    Severity.MEDIUM: COLOR_YELLOW,
    Severity.LOW: COLOR_GREEN,
    Severity.INFO: COLOR_ACCENT,
}

# Grade color mapping
GRADE_COLORS = {
    "A": COLOR_GREEN,
    "B": colors.HexColor("#84cc16"),
    "C": COLOR_YELLOW,
    "D": COLOR_ORANGE,
    "F": COLOR_RED,
}

# i18n strings for PDF
_PDF_I18N = {
    "en": {
        "title_prefix": "DUE DILIGENCE ENGINE",
        "report_title": "Technical Due Diligence Report",
        "analysis_id": "Analysis ID",
        "date": "Date",
        "grade_prefix": "Grade",
        "exec_summary": "Executive Summary",
        "metric": "Metric",
        "value": "Value",
        "overall_score": "Overall Score",
        "total_red_flags": "Total Red Flags",
        "critical_flags": "Critical Flags",
        "high_severity": "High Severity Flags",
        "files_analyzed": "Files Analyzed",
        "lines_of_code": "Lines of Code",
        "languages": "Languages",
        "api_cost": "API Cost",
        "score_breakdown": "Score Breakdown",
        "dimension": "Dimension",
        "score": "Score",
        "weight": "Weight",
        "weighted_score": "Weighted Score",
        "red_flags": "Red Flags",
        "codebase_metrics": "Codebase Metrics",
        "total_files": "Total Files",
        "total_lines": "Total Lines of Code",
        "wrapper_ratio": "API Wrapper Ratio",
        "test_coverage": "Test Coverage Estimate",
        "dependencies": "Dependencies",
        "has_tests": "Has Tests",
        "has_cicd": "Has CI/CD",
        "has_docs": "Has Documentation",
        "key_findings": "Key Findings",
        "git_forensics": "Git Forensics",
        "total_commits": "Total Commits",
        "unique_authors": "Unique Authors",
        "first_commit": "First Commit",
        "last_commit": "Last Commit",
        "rush_ratio": "Rush Commit Ratio",
        "suspicious_patterns": "Suspicious Patterns",
        "claim_consistency": "Claim Consistency",
        "consistency_score": "Consistency Score",
        "verified_claims": "Verified Claims",
        "unverified_claims": "Unverified Claims",
        "contradictions": "Contradictions",
        "contradictions_found": "Contradictions Found",
        "analysis_cost": "Analysis Cost",
        "total_api_cost": "Total API Cost",
        "model_tier": "Model Tier",
        "input_tokens": "Input Tokens",
        "output_tokens": "Output Tokens",
        "purge_cert_title": "Data Purge Certificate",
        "purge_cert_body": (
            "This certifies that all source code and analysis data associated with "
            "the following analysis has been cryptographically erased from this system."
        ),
        "field": "Field",
        "certificate_id": "Certificate ID",
        "project_name": "Project Name",
        "purge_timestamp": "Purge Timestamp",
        "files_purged": "Files Purged",
        "bytes_overwritten": "Bytes Overwritten",
        "deletion_method": "Deletion Method",
        "operator": "Operator",
        "verification_hash": "Verification Hash",
        "purge_footer": (
            "All source code data has been permanently deleted from this tool. "
            "Only report scores and findings have been retained."
        ),
        "nda_footer": (
            "CONFIDENTIAL - This report is subject to NDA. "
            "Do not distribute without authorization."
        ),
        "page": "Page",
        "yes": "Yes",
        "no": "No",
        "no_score": "No score was computed for this analysis.",
        "improvement_title": "Improvement Recommendations",
    },
    "ja": {
        "title_prefix": "DUE DILIGENCE ENGINE",
        "report_title": "\u6280\u8853\u30c7\u30e5\u30fc\u30c7\u30ea\u30b8\u30a7\u30f3\u30b9\u30ec\u30dd\u30fc\u30c8",
        "analysis_id": "\u5206\u6790ID",
        "date": "\u65e5\u4ed8",
        "grade_prefix": "\u30b0\u30ec\u30fc\u30c9",
        "exec_summary": "\u30a8\u30b0\u30bc\u30af\u30c6\u30a3\u30d6\u30b5\u30de\u30ea",
        "metric": "\u6307\u6a19",
        "value": "\u5024",
        "overall_score": "\u7dcf\u5408\u30b9\u30b3\u30a2",
        "total_red_flags": "\u30ec\u30c3\u30c9\u30d5\u30e9\u30b0\u5408\u8a08",
        "critical_flags": "\u91cd\u5927\u30d5\u30e9\u30b0",
        "high_severity": "\u9ad8\u30ea\u30b9\u30af\u30d5\u30e9\u30b0",
        "files_analyzed": "\u5206\u6790\u30d5\u30a1\u30a4\u30eb\u6570",
        "lines_of_code": "\u30b3\u30fc\u30c9\u884c\u6570",
        "languages": "\u8a00\u8a9e",
        "api_cost": "API\u30b3\u30b9\u30c8",
        "score_breakdown": "\u30b9\u30b3\u30a2\u5185\u8a33",
        "dimension": "\u8a55\u4fa1\u8ef8",
        "score": "\u30b9\u30b3\u30a2",
        "weight": "\u91cd\u307f",
        "weighted_score": "\u52a0\u91cd\u30b9\u30b3\u30a2",
        "red_flags": "\u30ec\u30c3\u30c9\u30d5\u30e9\u30b0",
        "codebase_metrics": "\u30b3\u30fc\u30c9\u30d9\u30fc\u30b9\u6307\u6a19",
        "total_files": "\u30d5\u30a1\u30a4\u30eb\u6570",
        "total_lines": "\u30b3\u30fc\u30c9\u884c\u6570",
        "wrapper_ratio": "API\u30e9\u30c3\u30d1\u30fc\u7387",
        "test_coverage": "\u30c6\u30b9\u30c8\u30ab\u30d0\u30ec\u30c3\u30b8\u63a8\u5b9a",
        "dependencies": "\u4f9d\u5b58\u95a2\u4fc2",
        "has_tests": "\u30c6\u30b9\u30c8",
        "has_cicd": "CI/CD",
        "has_docs": "\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8",
        "key_findings": "\u4e3b\u8981\u6240\u898b",
        "git_forensics": "Git\u5c65\u6b74\u30d5\u30a9\u30ec\u30f3\u30b8\u30c3\u30af",
        "total_commits": "\u30b3\u30df\u30c3\u30c8\u6570",
        "unique_authors": "\u8457\u8005\u6570",
        "first_commit": "\u521d\u56de\u30b3\u30df\u30c3\u30c8",
        "last_commit": "\u6700\u7d42\u30b3\u30df\u30c3\u30c8",
        "rush_ratio": "\u6025\u9020\u30b3\u30df\u30c3\u30c8\u7387",
        "suspicious_patterns": "\u7591\u308f\u3057\u3044\u30d1\u30bf\u30fc\u30f3",
        "claim_consistency": "\u4e3b\u5f35\u6574\u5408\u6027",
        "consistency_score": "\u6574\u5408\u6027\u30b9\u30b3\u30a2",
        "verified_claims": "\u691c\u8a3c\u6e08\u307f\u4e3b\u5f35",
        "unverified_claims": "\u672a\u691c\u8a3c\u306e\u4e3b\u5f35",
        "contradictions": "\u77db\u76fe",
        "contradictions_found": "\u691c\u51fa\u3055\u308c\u305f\u77db\u76fe",
        "analysis_cost": "\u5206\u6790\u30b3\u30b9\u30c8",
        "total_api_cost": "API\u5408\u8a08\u30b3\u30b9\u30c8",
        "model_tier": "\u30e2\u30c7\u30eb\u968e\u5c64",
        "input_tokens": "\u5165\u529b\u30c8\u30fc\u30af\u30f3",
        "output_tokens": "\u51fa\u529b\u30c8\u30fc\u30af\u30f3",
        "purge_cert_title": "\u30c7\u30fc\u30bf\u30d1\u30fc\u30b8\u8a3c\u660e\u66f8",
        "purge_cert_body": (
            "\u4ee5\u4e0b\u306e\u5206\u6790\u306b\u95a2\u9023\u3059\u308b\u5168\u3066\u306e\u30bd\u30fc\u30b9\u30b3\u30fc\u30c9\u304a\u3088\u3073\u5206\u6790\u30c7\u30fc\u30bf\u304c\u3001"
            "\u3053\u306e\u30b7\u30b9\u30c6\u30e0\u304b\u3089\u6697\u53f7\u5b66\u7684\u306b\u524a\u9664\u3055\u308c\u305f\u3053\u3068\u3092\u8a3c\u660e\u3057\u307e\u3059\u3002"
        ),
        "field": "\u9805\u76ee",
        "certificate_id": "\u8a3c\u660e\u66f8ID",
        "project_name": "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u540d",
        "purge_timestamp": "\u30d1\u30fc\u30b8\u65e5\u6642",
        "files_purged": "\u524a\u9664\u30d5\u30a1\u30a4\u30eb\u6570",
        "bytes_overwritten": "\u4e0a\u66f8\u304d\u30d0\u30a4\u30c8\u6570",
        "deletion_method": "\u524a\u9664\u65b9\u6cd5",
        "operator": "\u5b9f\u884c\u8005",
        "verification_hash": "\u691c\u8a3c\u30cf\u30c3\u30b7\u30e5",
        "purge_footer": (
            "\u5168\u3066\u306e\u30bd\u30fc\u30b9\u30b3\u30fc\u30c9\u30c7\u30fc\u30bf\u304c\u3053\u306e\u30c4\u30fc\u30eb\u304b\u3089\u5b8c\u5168\u306b\u524a\u9664\u3055\u308c\u307e\u3057\u305f\u3002"
            "\u30ec\u30dd\u30fc\u30c8\u306e\u30b9\u30b3\u30a2\u3068\u6240\u898b\u306e\u307f\u4fdd\u6301\u3055\u308c\u3066\u3044\u307e\u3059\u3002"
        ),
        "nda_footer": "\u6a5f\u5bc6 - \u672c\u30ec\u30dd\u30fc\u30c8\u306fNDA\u306e\u5bfe\u8c61\u3067\u3059\u3002\u8a31\u53ef\u306a\u304f\u914d\u5e03\u3057\u306a\u3044\u3067\u304f\u3060\u3055\u3044\u3002",
        "page": "\u30da\u30fc\u30b8",
        "yes": "\u3042\u308a",
        "no": "\u306a\u3057",
        "no_score": "\u3053\u306e\u5206\u6790\u306e\u30b9\u30b3\u30a2\u306f\u8a08\u7b97\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002",
        "improvement_title": "\u6539\u5584\u63d0\u6848",
    },
}

# Grade recommendations for PDF
_PDF_GRADE_REC = {
    "en": {
        "A": "Strong investment candidate. Proceed with standard terms.",
        "B": "Viable with conditions. Address flagged items before closing.",
        "C": "Significant concerns. Require remediation plan with milestones.",
        "D": "High risk. Consider pass or heavily discounted terms.",
        "F": "Do not invest. Fundamental issues detected.",
    },
    "ja": {
        "A": "\u6709\u529b\u306a\u6295\u8cc7\u5019\u88dc\u3002\u6a19\u6e96\u6761\u4ef6\u3067\u9032\u884c\u53ef\u80fd\u3002",
        "B": "\u6761\u4ef6\u4ed8\u304d\u3067\u6295\u8cc7\u53ef\u80fd\u3002\u6307\u6458\u4e8b\u9805\u306e\u5bfe\u5fdc\u3092\u78ba\u8a8d\u3002",
        "C": "\u91cd\u8981\u306a\u61f8\u5ff5\u3042\u308a\u3002\u6539\u5584\u8a08\u753b\u306e\u63d0\u51fa\u3092\u8981\u6c42\u3002",
        "D": "\u9ad8\u30ea\u30b9\u30af\u3002\u898b\u9001\u308a\u307e\u305f\u306f\u5927\u5e45\u306a\u6761\u4ef6\u5909\u66f4\u3092\u691c\u8a0e\u3002",
        "F": "\u6295\u8cc7\u4e0d\u53ef\u3002\u6839\u672c\u7684\u306a\u554f\u984c\u3092\u691c\u51fa\u3002",
    },
}

# Dimension name translations
_DIM_NAME_JA = {
    "Technical Originality": "\u6280\u8853\u72ec\u81ea\u6027",
    "Technology Advancement": "\u6280\u8853\u5148\u9032\u6027",
    "Implementation Depth": "\u5b9f\u88c5\u6df1\u5ea6",
    "Architecture Quality": "\u30a2\u30fc\u30ad\u30c6\u30af\u30c1\u30e3\u54c1\u8cea",
    "Claim Consistency": "\u4e3b\u5f35\u6574\u5408\u6027",
    "Security Posture": "\u30bb\u30ad\u30e5\u30ea\u30c6\u30a3\u614b\u52e2",
}


def _build_styles(lang: str = "en") -> dict[str, ParagraphStyle]:
    """Build custom paragraph styles for the PDF report."""
    base = getSampleStyleSheet()

    # Select font family based on language
    if lang == "ja":
        font_normal = "HeiseiMin-W3"
        font_bold = "HeiseiKakuGo-W5"
    else:
        font_normal = "Helvetica"
        font_bold = "Helvetica-Bold"

    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base["Title"],
            fontSize=28,
            textColor=COLOR_BG_DARK,
            spaceAfter=6 * mm,
            alignment=TA_CENTER,
            fontName=font_bold,
        ),
        "subtitle": ParagraphStyle(
            "CustomSubtitle",
            parent=base["Normal"],
            fontSize=14,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=4 * mm,
            alignment=TA_CENTER,
            fontName=font_normal,
        ),
        "heading1": ParagraphStyle(
            "CustomH1",
            parent=base["Heading1"],
            fontSize=18,
            textColor=COLOR_BG_DARK,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
            borderWidth=0,
            borderPadding=0,
            fontName=font_bold,
        ),
        "heading2": ParagraphStyle(
            "CustomH2",
            parent=base["Heading2"],
            fontSize=14,
            textColor=COLOR_ACCENT,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
            fontName=font_bold,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_TEXT,
            spaceAfter=3 * mm,
            leading=14,
            fontName=font_normal,
        ),
        "body_small": ParagraphStyle(
            "CustomBodySmall",
            parent=base["Normal"],
            fontSize=8,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=2 * mm,
            leading=11,
            fontName=font_normal,
        ),
        "footer": ParagraphStyle(
            "CustomFooter",
            parent=base["Normal"],
            fontSize=7,
            textColor=COLOR_TEXT_DIM,
            alignment=TA_CENTER,
            fontName=font_normal,
        ),
        "score_large": ParagraphStyle(
            "ScoreLarge",
            parent=base["Normal"],
            fontSize=48,
            textColor=COLOR_BG_DARK,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
            fontName=font_bold,
        ),
        "grade_label": ParagraphStyle(
            "GradeLabel",
            parent=base["Normal"],
            fontSize=16,
            textColor=COLOR_TEXT_DIM,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
            fontName=font_normal,
        ),
        "flag_title": ParagraphStyle(
            "FlagTitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_TEXT,
            spaceAfter=1 * mm,
            fontName=font_bold,
        ),
        "flag_desc": ParagraphStyle(
            "FlagDesc",
            parent=base["Normal"],
            fontSize=9,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=3 * mm,
            leftIndent=10,
            fontName=font_normal,
        ),
        "center": ParagraphStyle(
            "CenterBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_TEXT,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
            fontName=font_normal,
        ),
        "nda_notice": ParagraphStyle(
            "NDANotice",
            parent=base["Normal"],
            fontSize=7,
            textColor=COLOR_RED,
            alignment=TA_CENTER,
            fontName=font_normal,
        ),
    }


class PDFReportGenerator:
    """Generates professional PDF due diligence reports.

    The generated PDF contains:
    - Cover page with overall score
    - Executive summary
    - Score dimension breakdown
    - Red flags detail
    - Codebase metrics summary
    - Git forensics summary (if available)
    - Analysis cost breakdown
    - Purge certificate (if applicable)

    Source code is NEVER included in the output.
    """

    def __init__(self) -> None:
        self._styles: dict[str, ParagraphStyle] = {}
        self._lang = "en"
        self._t: dict[str, str] = {}

    def generate(
        self,
        result: AnalysisResult,
        purge_cert: PurgeCertificate | None = None,
        lang: str = "en",
    ) -> bytes:
        """Generate a PDF report as bytes.

        Args:
            result: The complete analysis result.
            purge_cert: Optional purge certificate to include.
            lang: Language code ("en" or "ja").

        Returns:
            PDF file content as bytes.
        """
        self._lang = lang if lang in ("en", "ja") else "en"
        self._styles = _build_styles(self._lang)
        self._t = _PDF_I18N.get(self._lang, _PDF_I18N["en"])

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
            title=f"Due Diligence Report: {result.project_name}",
            author="Due Diligence Engine",
        )

        story: list = []

        # Cover page
        story.extend(self._build_cover_page(result))

        # Executive summary
        story.append(PageBreak())
        story.extend(self._build_executive_summary(result))

        # Score breakdown
        story.extend(self._build_score_breakdown(result))

        # Red flags
        if result.score and result.score.red_flags:
            story.append(PageBreak())
            story.extend(self._build_red_flags_section(result))

        # Codebase metrics
        story.append(PageBreak())
        story.extend(self._build_codebase_metrics(result))

        # Git forensics
        if result.git_forensics.total_commits > 0:
            story.extend(self._build_git_forensics(result))

        # Consistency check
        story.extend(self._build_consistency_section(result))

        # Cost breakdown
        story.extend(self._build_cost_section(result))

        # Purge certificate
        if purge_cert is not None:
            story.append(PageBreak())
            story.extend(self._build_purge_certificate(purge_cert))

        # Build PDF with footer
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def generate_to_file(
        self,
        result: AnalysisResult,
        output_path: Path,
        purge_cert: PurgeCertificate | None = None,
        lang: str = "en",
    ) -> Path:
        """Generate a PDF report and save to file.

        Args:
            result: The complete analysis result.
            output_path: Path to save the PDF file.
            purge_cert: Optional purge certificate to include.
            lang: Language code ("en" or "ja").

        Returns:
            Path to the generated PDF file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = self.generate(result, purge_cert, lang=lang)
        output_path.write_bytes(pdf_bytes)
        logger.info(f"PDF report saved to {output_path}")
        return output_path

    def _dim_name(self, name: str) -> str:
        """Get dimension name in the current language."""
        if self._lang == "ja":
            return _DIM_NAME_JA.get(name, name)
        return name

    def _build_cover_page(self, result: AnalysisResult) -> list:
        """Build the cover page with logo placeholder, score, and grade."""
        s = self._styles
        t = self._t
        elements: list = []

        # Spacer for visual balance
        elements.append(Spacer(1, 4 * cm))

        # Logo placeholder
        elements.append(
            Paragraph(
                f'<font color="#38bdf8" size="12">{t["title_prefix"]}</font>',
                s["center"],
            )
        )
        elements.append(Spacer(1, 1 * cm))

        # Title
        elements.append(
            Paragraph(t["report_title"], s["title"])
        )

        # Project name
        elements.append(
            Paragraph(result.project_name, s["subtitle"])
        )

        elements.append(Spacer(1, 1.5 * cm))

        # Score display
        score = result.score
        if score is not None:
            grade_color = GRADE_COLORS.get(score.grade, COLOR_TEXT)

            score_text = f'<font color="{grade_color.hexval()}" size="60">{score.overall_score:.0f}</font>'
            elements.append(Paragraph(score_text, s["score_large"]))

            grade_text = f'<font color="{grade_color.hexval()}">{t["grade_prefix"]}: {score.grade}</font> / 100'
            elements.append(Paragraph(grade_text, s["grade_label"]))

            elements.append(Spacer(1, 8 * mm))

            # Recommendation
            rec = _PDF_GRADE_REC.get(self._lang, _PDF_GRADE_REC["en"])
            recommendation = rec.get(score.grade, score.recommendation)
            elements.append(Paragraph(recommendation, s["center"]))

        elements.append(Spacer(1, 2 * cm))

        # Metadata
        elements.append(
            Paragraph(
                f"{t['analysis_id']}: {result.analysis_id}",
                s["body_small"],
            )
        )
        elements.append(
            Paragraph(
                f"{t['date']}: {result.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
                s["body_small"],
            )
        )

        return elements

    def _build_executive_summary(self, result: AnalysisResult) -> list:
        """Build the executive summary section."""
        s = self._styles
        t = self._t
        elements: list = []

        elements.append(Paragraph(t["exec_summary"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        score = result.score
        if score is not None:
            rec = _PDF_GRADE_REC.get(self._lang, _PDF_GRADE_REC["en"])
            recommendation = rec.get(score.grade, score.recommendation)
            elements.append(Paragraph(recommendation, s["body"]))

            # Key metrics summary
            critical_count = sum(1 for f in score.red_flags if f.is_deal_breaker)
            high_count = sum(1 for f in score.red_flags if f.severity == Severity.HIGH)

            summary_data = [
                [t["metric"], t["value"]],
                [t["overall_score"], f"{score.overall_score:.0f}/100 ({score.grade})"],
                [t["total_red_flags"], str(len(score.red_flags))],
                [t["critical_flags"], str(critical_count)],
                [t["high_severity"], str(high_count)],
                [t["files_analyzed"], str(result.code_analysis.total_files)],
                [t["lines_of_code"], f"{result.code_analysis.total_lines:,}"],
                [t["languages"], str(len(result.code_analysis.languages))],
                [t["api_cost"], f"${result.total_cost_usd:.4f}"],
            ]

            table = Table(summary_data, colWidths=[7 * cm, 8 * cm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(table)
        else:
            elements.append(
                Paragraph(t["no_score"], s["body"])
            )

        return elements

    def _build_score_breakdown(self, result: AnalysisResult) -> list:
        """Build the score dimension breakdown table."""
        s = self._styles
        t = self._t
        elements: list = []

        score = result.score
        if score is None:
            return elements

        elements.append(Paragraph(t["score_breakdown"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        # Dimension table
        table_data = [[t["dimension"], t["score"], t["weight"], t["weighted_score"]]]
        for dim in score.dimensions:
            table_data.append([
                self._dim_name(dim.name),
                f"{dim.score:.0f}/100",
                f"{dim.weight:.0%}",
                f"{dim.weighted_score:.1f}",
            ])

        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

        table = Table(table_data, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_header),
            ("FONTNAME", (0, 1), (-1, -1), font_body),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)

        # Dimension rationales
        elements.append(Spacer(1, 6 * mm))
        for dim in score.dimensions:
            elements.append(
                Paragraph(f"<b>{self._dim_name(dim.name)}</b> ({dim.score:.0f}/100)", s["body"])
            )
            elements.append(Paragraph(dim.rationale, s["body_small"]))

        return elements

    def _build_red_flags_section(self, result: AnalysisResult) -> list:
        """Build the red flags detail section."""
        s = self._styles
        t = self._t
        elements: list = []

        score = result.score
        if score is None or not score.red_flags:
            return elements

        elements.append(Paragraph(t["red_flags"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_RED, spaceAfter=4 * mm)
        )

        # Group by severity
        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]

        for severity in severity_order:
            flags = [f for f in score.red_flags if f.severity == severity]
            if not flags:
                continue

            severity_color = SEVERITY_COLORS.get(severity, COLOR_TEXT)
            elements.append(
                Paragraph(
                    f'<font color="{severity_color.hexval()}">{severity.value.upper()}</font>',
                    s["heading2"],
                )
            )

            for flag in flags:
                elements.append(
                    Paragraph(
                        f'<font color="{severity_color.hexval()}">[{flag.severity.value.upper()}]</font> '
                        f"<b>{flag.title}</b> ({flag.category})",
                        s["flag_title"],
                    )
                )
                elements.append(Paragraph(flag.description, s["flag_desc"]))

                if flag.evidence:
                    evidence_label = "Evidence" if self._lang == "en" else "\u8a3c\u62e0"
                    evidence_text = f"{evidence_label}: " + "; ".join(flag.evidence[:3])
                    elements.append(Paragraph(evidence_text, s["flag_desc"]))

        return elements

    def _build_codebase_metrics(self, result: AnalysisResult) -> list:
        """Build the codebase metrics section."""
        s = self._styles
        t = self._t
        elements: list = []

        code = result.code_analysis

        elements.append(Paragraph(t["codebase_metrics"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        metrics_data = [
            [t["metric"], t["value"]],
            [t["total_files"], str(code.total_files)],
            [t["total_lines"], f"{code.total_lines:,}"],
            [t["languages"], ", ".join(f"{k} ({v})" for k, v in code.languages.items()) or "N/A"],
            [t["wrapper_ratio"], f"{code.api_wrapper_ratio:.0%}"],
            [t["test_coverage"], f"{code.test_coverage_estimate:.0%}"],
            [t["dependencies"], str(code.dependency_count)],
            [t["has_tests"], t["yes"] if code.has_tests else t["no"]],
            [t["has_cicd"], t["yes"] if code.has_ci_cd else t["no"]],
            [t["has_docs"], t["yes"] if code.has_documentation else t["no"]],
        ]

        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

        table = Table(metrics_data, colWidths=[6 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_header),
            ("FONTNAME", (0, 1), (-1, -1), font_body),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)

        # Code findings (no source code, only findings text)
        if code.findings:
            elements.append(Paragraph(t["key_findings"], s["heading2"]))
            for finding in code.findings[:20]:  # Limit to 20 findings
                elements.append(
                    Paragraph(f"&bull; {finding}", s["body_small"])
                )

        return elements

    def _build_git_forensics(self, result: AnalysisResult) -> list:
        """Build the git forensics section."""
        s = self._styles
        t = self._t
        elements: list = []

        git = result.git_forensics

        elements.append(Paragraph(t["git_forensics"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        git_data = [
            [t["metric"], t["value"]],
            [t["total_commits"], str(git.total_commits)],
            [t["unique_authors"], str(git.unique_authors)],
            [t["first_commit"], git.first_commit_date or "N/A"],
            [t["last_commit"], git.last_commit_date or "N/A"],
            [t["rush_ratio"], f"{git.rush_commit_ratio:.0%}"],
        ]

        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

        table = Table(git_data, colWidths=[6 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_header),
            ("FONTNAME", (0, 1), (-1, -1), font_body),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)

        if git.suspicious_patterns:
            elements.append(Paragraph(t["suspicious_patterns"], s["heading2"]))
            for pattern in git.suspicious_patterns:
                elements.append(
                    Paragraph(f"&bull; {pattern}", s["body_small"])
                )

        return elements

    def _build_consistency_section(self, result: AnalysisResult) -> list:
        """Build the claim consistency section."""
        s = self._styles
        t = self._t
        elements: list = []

        consistency = result.consistency

        elements.append(Paragraph(t["claim_consistency"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        consistency_data = [
            [t["metric"], t["value"]],
            [t["consistency_score"], f"{consistency.consistency_score:.0f}%"],
            [t["verified_claims"], str(len(consistency.verified_claims))],
            [t["unverified_claims"], str(len(consistency.unverified_claims))],
            [t["contradictions"], str(len(consistency.contradictions))],
        ]

        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

        table = Table(consistency_data, colWidths=[6 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_header),
            ("FONTNAME", (0, 1), (-1, -1), font_body),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)

        if consistency.contradictions:
            elements.append(Paragraph(t["contradictions_found"], s["heading2"]))
            for contradiction in consistency.contradictions:
                elements.append(
                    Paragraph(f"&bull; {contradiction}", s["body_small"])
                )

        return elements

    def _build_cost_section(self, result: AnalysisResult) -> list:
        """Build the analysis cost breakdown section."""
        s = self._styles
        t = self._t
        elements: list = []

        elements.append(Paragraph(t["analysis_cost"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        elements.append(
            Paragraph(f"{t['total_api_cost']}: <b>${result.total_cost_usd:.4f}</b>", s["body"])
        )

        if result.model_usage:
            cost_data = [[t["model_tier"], t["input_tokens"], t["output_tokens"]]]
            for tier, usage in result.model_usage.items():
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                if input_tokens > 0 or output_tokens > 0:
                    cost_data.append([
                        tier.title(),
                        f"{input_tokens:,}",
                        f"{output_tokens:,}",
                    ])

            if len(cost_data) > 1:
                font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
                font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

                table = Table(cost_data, colWidths=[5 * cm, 5 * cm, 5 * cm])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), font_header),
                    ("FONTNAME", (0, 1), (-1, -1), font_body),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                elements.append(table)

        return elements

    def _build_purge_certificate(self, cert: PurgeCertificate) -> list:
        """Build the purge certificate page."""
        s = self._styles
        t = self._t
        elements: list = []

        elements.append(Spacer(1, 2 * cm))
        elements.append(
            Paragraph(
                f'<font color="#ef4444" size="20">{t["purge_cert_title"]}</font>',
                s["center"],
            )
        )
        elements.append(Spacer(1, 1 * cm))
        elements.append(
            HRFlowable(width="100%", thickness=2, color=COLOR_RED, spaceAfter=6 * mm)
        )

        elements.append(
            Paragraph(t["purge_cert_body"], s["center"])
        )
        elements.append(Spacer(1, 8 * mm))

        cert_data = [
            [t["field"], t["value"]],
            [t["certificate_id"], cert.certificate_id],
            [t["analysis_id"], cert.analysis_id],
            [t["project_name"], cert.project_name],
            [t["purge_timestamp"], cert.purge_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")],
            [t["files_purged"], str(cert.files_purged)],
            [t["bytes_overwritten"], f"{cert.bytes_overwritten:,}"],
            [t["deletion_method"], cert.method],
            [t["operator"], cert.operator],
        ]

        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

        table = Table(cert_data, colWidths=[5 * cm, 10 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_RED),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), font_header),
            ("FONTNAME", (0, 1), (0, -1), font_header),
            ("FONTNAME", (1, 1), (-1, -1), font_body),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)

        elements.append(Spacer(1, 1 * cm))

        # Verification hash (truncated for readability)
        if cert.verification_hash:
            display_hash = cert.verification_hash[:64]
            if len(cert.verification_hash) > 64:
                display_hash += "..."
            elements.append(
                Paragraph(
                    f"{t['verification_hash']}: <font name='Courier' size='8'>{display_hash}</font>",
                    s["body_small"],
                )
            )

        elements.append(Spacer(1, 1 * cm))
        elements.append(Paragraph(t["purge_footer"], s["center"]))

        return elements

    def _add_footer(self, canvas, doc) -> None:
        """Add NDA compliance footer to every page."""
        canvas.saveState()
        page_width, page_height = A4

        # NDA notice
        font_name = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
        canvas.setFont(font_name, 7)
        canvas.setFillColor(COLOR_TEXT_DIM)
        canvas.drawCentredString(
            page_width / 2,
            1.2 * cm,
            self._t.get("nda_footer", "CONFIDENTIAL"),
        )

        # Page number
        page_label = self._t.get("page", "Page")
        canvas.drawRightString(
            page_width - 2 * cm,
            1.2 * cm,
            f"{page_label} {doc.page}",
        )

        # Separator line
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.8 * cm, page_width - 2 * cm, 1.8 * cm)

        canvas.restoreState()
