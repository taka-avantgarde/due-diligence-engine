"""Professional PDF report generator for due diligence reports.

Generates multi-page PDF reports using ReportLab with:
- Cover page with overall score and grade
- Executive summary
- Dimension breakdown table with scores
- Red flags section with severity indicators
- Architecture and code analysis findings
- Purge certificate page (if applicable)
- NDA compliance footer on every page

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


def _build_styles() -> dict[str, ParagraphStyle]:
    """Build custom paragraph styles for the PDF report."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base["Title"],
            fontSize=28,
            textColor=COLOR_BG_DARK,
            spaceAfter=6 * mm,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "CustomSubtitle",
            parent=base["Normal"],
            fontSize=14,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=4 * mm,
            alignment=TA_CENTER,
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
        ),
        "heading2": ParagraphStyle(
            "CustomH2",
            parent=base["Heading2"],
            fontSize=14,
            textColor=COLOR_ACCENT,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_TEXT,
            spaceAfter=3 * mm,
            leading=14,
        ),
        "body_small": ParagraphStyle(
            "CustomBodySmall",
            parent=base["Normal"],
            fontSize=8,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=2 * mm,
            leading=11,
        ),
        "footer": ParagraphStyle(
            "CustomFooter",
            parent=base["Normal"],
            fontSize=7,
            textColor=COLOR_TEXT_DIM,
            alignment=TA_CENTER,
        ),
        "score_large": ParagraphStyle(
            "ScoreLarge",
            parent=base["Normal"],
            fontSize=48,
            textColor=COLOR_BG_DARK,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
        ),
        "grade_label": ParagraphStyle(
            "GradeLabel",
            parent=base["Normal"],
            fontSize=16,
            textColor=COLOR_TEXT_DIM,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ),
        "flag_title": ParagraphStyle(
            "FlagTitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_TEXT,
            spaceAfter=1 * mm,
            fontName="Helvetica-Bold",
        ),
        "flag_desc": ParagraphStyle(
            "FlagDesc",
            parent=base["Normal"],
            fontSize=9,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=3 * mm,
            leftIndent=10,
        ),
        "center": ParagraphStyle(
            "CenterBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_TEXT,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
        ),
        "nda_notice": ParagraphStyle(
            "NDANotice",
            parent=base["Normal"],
            fontSize=7,
            textColor=COLOR_RED,
            alignment=TA_CENTER,
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
        self._styles = _build_styles()

    def generate(
        self,
        result: AnalysisResult,
        purge_cert: PurgeCertificate | None = None,
    ) -> bytes:
        """Generate a PDF report as bytes.

        Args:
            result: The complete analysis result.
            purge_cert: Optional purge certificate to include.

        Returns:
            PDF file content as bytes.
        """
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
    ) -> Path:
        """Generate a PDF report and save to file.

        Args:
            result: The complete analysis result.
            output_path: Path to save the PDF file.
            purge_cert: Optional purge certificate to include.

        Returns:
            Path to the generated PDF file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = self.generate(result, purge_cert)
        output_path.write_bytes(pdf_bytes)
        logger.info(f"PDF report saved to {output_path}")
        return output_path

    def _build_cover_page(self, result: AnalysisResult) -> list:
        """Build the cover page with logo placeholder, score, and grade."""
        s = self._styles
        elements: list = []

        # Spacer for visual balance
        elements.append(Spacer(1, 4 * cm))

        # Logo placeholder
        elements.append(
            Paragraph(
                '<font color="#38bdf8" size="12">DUE DILIGENCE ENGINE</font>',
                s["center"],
            )
        )
        elements.append(Spacer(1, 1 * cm))

        # Title
        elements.append(
            Paragraph("Technical Due Diligence Report", s["title"])
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

            grade_text = f'<font color="{grade_color.hexval()}">Grade: {score.grade}</font> / 100'
            elements.append(Paragraph(grade_text, s["grade_label"]))

            elements.append(Spacer(1, 8 * mm))

            # Recommendation
            elements.append(Paragraph(score.recommendation, s["center"]))

        elements.append(Spacer(1, 2 * cm))

        # Metadata
        elements.append(
            Paragraph(
                f"Analysis ID: {result.analysis_id}",
                s["body_small"],
            )
        )
        elements.append(
            Paragraph(
                f"Date: {result.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
                s["body_small"],
            )
        )

        return elements

    def _build_executive_summary(self, result: AnalysisResult) -> list:
        """Build the executive summary section."""
        s = self._styles
        elements: list = []

        elements.append(Paragraph("Executive Summary", s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        score = result.score
        if score is not None:
            elements.append(Paragraph(score.recommendation, s["body"]))

            # Key metrics summary
            critical_count = sum(1 for f in score.red_flags if f.is_deal_breaker)
            high_count = sum(1 for f in score.red_flags if f.severity == Severity.HIGH)

            summary_data = [
                ["Metric", "Value"],
                ["Overall Score", f"{score.overall_score:.0f}/100 ({score.grade})"],
                ["Total Red Flags", str(len(score.red_flags))],
                ["Critical Flags", str(critical_count)],
                ["High Severity Flags", str(high_count)],
                ["Files Analyzed", str(result.code_analysis.total_files)],
                ["Lines of Code", f"{result.code_analysis.total_lines:,}"],
                ["Languages", str(len(result.code_analysis.languages))],
                ["API Cost", f"${result.total_cost_usd:.4f}"],
            ]

            table = Table(summary_data, colWidths=[7 * cm, 8 * cm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
                Paragraph("No score was computed for this analysis.", s["body"])
            )

        return elements

    def _build_score_breakdown(self, result: AnalysisResult) -> list:
        """Build the score dimension breakdown table."""
        s = self._styles
        elements: list = []

        score = result.score
        if score is None:
            return elements

        elements.append(Paragraph("Score Breakdown", s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        # Dimension table
        table_data = [["Dimension", "Score", "Weight", "Weighted Score"]]
        for dim in score.dimensions:
            table_data.append([
                dim.name,
                f"{dim.score:.0f}/100",
                f"{dim.weight:.0%}",
                f"{dim.weighted_score:.1f}",
            ])

        table = Table(table_data, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
                Paragraph(f"<b>{dim.name}</b> ({dim.score:.0f}/100)", s["body"])
            )
            elements.append(Paragraph(dim.rationale, s["body_small"]))

        return elements

    def _build_red_flags_section(self, result: AnalysisResult) -> list:
        """Build the red flags detail section."""
        s = self._styles
        elements: list = []

        score = result.score
        if score is None or not score.red_flags:
            return elements

        elements.append(Paragraph("Red Flags", s["heading1"]))
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
                    evidence_text = "Evidence: " + "; ".join(flag.evidence[:3])
                    elements.append(Paragraph(evidence_text, s["flag_desc"]))

        return elements

    def _build_codebase_metrics(self, result: AnalysisResult) -> list:
        """Build the codebase metrics section."""
        s = self._styles
        elements: list = []

        code = result.code_analysis

        elements.append(Paragraph("Codebase Metrics", s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        metrics_data = [
            ["Metric", "Value"],
            ["Total Files", str(code.total_files)],
            ["Total Lines of Code", f"{code.total_lines:,}"],
            ["Languages", ", ".join(f"{k} ({v})" for k, v in code.languages.items()) or "N/A"],
            ["API Wrapper Ratio", f"{code.api_wrapper_ratio:.0%}"],
            ["Test Coverage Estimate", f"{code.test_coverage_estimate:.0%}"],
            ["Dependencies", str(code.dependency_count)],
            ["Has Tests", "Yes" if code.has_tests else "No"],
            ["Has CI/CD", "Yes" if code.has_ci_cd else "No"],
            ["Has Documentation", "Yes" if code.has_documentation else "No"],
        ]

        table = Table(metrics_data, colWidths=[6 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
            elements.append(Paragraph("Key Findings", s["heading2"]))
            for finding in code.findings[:20]:  # Limit to 20 findings
                elements.append(
                    Paragraph(f"&bull; {finding}", s["body_small"])
                )

        return elements

    def _build_git_forensics(self, result: AnalysisResult) -> list:
        """Build the git forensics section."""
        s = self._styles
        elements: list = []

        git = result.git_forensics

        elements.append(Paragraph("Git Forensics", s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        git_data = [
            ["Metric", "Value"],
            ["Total Commits", str(git.total_commits)],
            ["Unique Authors", str(git.unique_authors)],
            ["First Commit", git.first_commit_date or "N/A"],
            ["Last Commit", git.last_commit_date or "N/A"],
            ["Rush Commit Ratio", f"{git.rush_commit_ratio:.0%}"],
        ]

        table = Table(git_data, colWidths=[6 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
            elements.append(Paragraph("Suspicious Patterns", s["heading2"]))
            for pattern in git.suspicious_patterns:
                elements.append(
                    Paragraph(f"&bull; {pattern}", s["body_small"])
                )

        return elements

    def _build_consistency_section(self, result: AnalysisResult) -> list:
        """Build the claim consistency section."""
        s = self._styles
        elements: list = []

        consistency = result.consistency

        elements.append(Paragraph("Claim Consistency", s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        consistency_data = [
            ["Metric", "Value"],
            ["Consistency Score", f"{consistency.consistency_score:.0f}%"],
            ["Verified Claims", str(len(consistency.verified_claims))],
            ["Unverified Claims", str(len(consistency.unverified_claims))],
            ["Contradictions", str(len(consistency.contradictions))],
        ]

        table = Table(consistency_data, colWidths=[6 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
            elements.append(Paragraph("Contradictions Found", s["heading2"]))
            for contradiction in consistency.contradictions:
                elements.append(
                    Paragraph(f"&bull; {contradiction}", s["body_small"])
                )

        return elements

    def _build_cost_section(self, result: AnalysisResult) -> list:
        """Build the analysis cost breakdown section."""
        s = self._styles
        elements: list = []

        elements.append(Paragraph("Analysis Cost", s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        elements.append(
            Paragraph(f"Total API Cost: <b>${result.total_cost_usd:.4f}</b>", s["body"])
        )

        if result.model_usage:
            cost_data = [["Model Tier", "Input Tokens", "Output Tokens"]]
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
                table = Table(cost_data, colWidths=[5 * cm, 5 * cm, 5 * cm])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
        elements: list = []

        elements.append(Spacer(1, 2 * cm))
        elements.append(
            Paragraph(
                '<font color="#ef4444" size="20">Data Purge Certificate</font>',
                s["center"],
            )
        )
        elements.append(Spacer(1, 1 * cm))
        elements.append(
            HRFlowable(width="100%", thickness=2, color=COLOR_RED, spaceAfter=6 * mm)
        )

        elements.append(
            Paragraph(
                "This certifies that all source code and analysis data associated with "
                "the following analysis has been cryptographically erased from this system.",
                s["center"],
            )
        )
        elements.append(Spacer(1, 8 * mm))

        cert_data = [
            ["Field", "Value"],
            ["Certificate ID", cert.certificate_id],
            ["Analysis ID", cert.analysis_id],
            ["Project Name", cert.project_name],
            ["Purge Timestamp", cert.purge_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Files Purged", str(cert.files_purged)],
            ["Bytes Overwritten", f"{cert.bytes_overwritten:,}"],
            ["Deletion Method", cert.method],
            ["Operator", cert.operator],
        ]

        table = Table(cert_data, colWidths=[5 * cm, 10 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_RED),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
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
                    f"Verification Hash: <font name='Courier' size='8'>{display_hash}</font>",
                    s["body_small"],
                )
            )

        elements.append(Spacer(1, 1 * cm))
        elements.append(
            Paragraph(
                "All source code data has been permanently deleted from this tool. "
                "Only report scores and findings have been retained.",
                s["center"],
            )
        )
        elements.append(
            Paragraph(
                "&#20840;&#12390;&#12398;&#12477;&#12540;&#12473;&#12467;&#12540;&#12489;"
                "&#12487;&#12540;&#12479;&#12364;&#12371;&#12398;&#12484;&#12540;&#12523;"
                "&#12363;&#12425;&#23436;&#20840;&#12395;&#21066;&#38500;&#12373;&#12428;"
                "&#12414;&#12375;&#12383;&#12290;&#12524;&#12509;&#12540;&#12488;&#12398;"
                "&#12473;&#12467;&#12450;&#12392;&#25152;&#35211;&#12398;&#12415;&#20445;"
                "&#25345;&#12373;&#12428;&#12390;&#12356;&#12414;&#12377;&#12290;",
                s["center"],
            )
        )

        return elements

    @staticmethod
    def _add_footer(canvas, doc) -> None:
        """Add NDA compliance footer to every page."""
        canvas.saveState()
        page_width, page_height = A4

        # NDA notice
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(COLOR_TEXT_DIM)
        canvas.drawCentredString(
            page_width / 2,
            1.2 * cm,
            "CONFIDENTIAL - This report is subject to NDA. "
            "Do not distribute without authorization.",
        )

        # Page number
        canvas.drawRightString(
            page_width - 2 * cm,
            1.2 * cm,
            f"Page {doc.page}",
        )

        # Separator line
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.8 * cm, page_width - 2 * cm, 1.8 * cm)

        canvas.restoreState()
