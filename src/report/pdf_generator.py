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
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.models import AIProviderResult, AnalysisResult, PurgeCertificate, Severity

logger = logging.getLogger(__name__)

# Register CID fonts for Japanese support
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

# Color palette — Arc brand: black + sky blue (#5271FF)
COLOR_BG_DARK = colors.HexColor("#000000")       # pure black (cover)
COLOR_SURFACE = colors.HexColor("#0a0a14")       # near-black surface
COLOR_ACCENT = colors.HexColor("#5271FF")        # Arc sky — primary brand
COLOR_ACCENT_DARK = colors.HexColor("#3854CC")   # Arc sky darker (hover/pressed)
COLOR_ACCENT_LIGHT = colors.HexColor("#E8EDFF")  # Arc sky tint (backgrounds)
COLOR_GREEN = colors.HexColor("#4a6741")         # muted green (retained for SWOT only)
COLOR_YELLOW = colors.HexColor("#8a7a3a")        # muted gold (severity)
COLOR_ORANGE = colors.HexColor("#7a5a3a")        # muted brown (severity)
COLOR_RED = colors.HexColor("#8b3a3a")           # muted dark red (severity)
COLOR_TEXT = colors.HexColor("#000000")          # pure black
COLOR_TEXT_DIM = colors.HexColor("#6b7280")      # gray-500
COLOR_BORDER = colors.HexColor("#d1d5db")        # gray-300
COLOR_WHITE = colors.white
COLOR_LIGHT_BG = colors.HexColor("#f3f4f6")      # gray-100

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
    "A": colors.HexColor("#2d5a3d"),     # dark green
    "B": colors.HexColor("#5271FF"),     # dark blue
    "C": colors.HexColor("#5a5a3a"),     # dark gold
    "D": colors.HexColor("#6b4a2a"),     # dark brown
    "F": colors.HexColor("#6b2a2a"),     # dark red
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
        # Consulting report sections
        "business_summary": "Executive Business Summary",
        "swot_analysis": "SWOT Analysis",
        "strengths": "Strengths",
        "weaknesses": "Weaknesses",
        "opportunities": "Opportunities",
        "threats": "Threats",
        "tech_level": "Technology Level Assessment",
        "future_outlook": "Future Outlook",
        "product_vision": "Product Vision",
        "viability": "Viability Assessment",
        "year_1": "Year 1",
        "year_3": "Year 3",
        "year_5": "Year 5",
        "confidence": "Confidence",
        "milestones": "Key Milestones",
        "strategic_advice": "Strategic Advice",
        "immediate_actions": "Immediate Actions",
        "medium_term": "Medium-Term Priorities",
        "long_term_vision": "Long-Term Vision",
        "investment_thesis": "Investment Thesis",
        "recommendation": "Recommendation",
        "key_risks": "Key Risks",
        "key_upside": "Key Upside",
        "comparable_companies": "Comparable Companies",
        "valuation_factors": "Valuation Factors",
        "glossary": "Glossary",
        "term": "Term",
        "definition": "Definition",
        "ai_model": "AI Model Used",
        "enables": "Enables",
        "action": "Action",
        "rationale": "Rationale",
        "impact": "Expected Impact",
        "invest_strong": "Strong Invest",
        "invest_conditions": "Invest with Conditions",
        "invest_cautious": "Cautious",
        "invest_pass": "Pass",
        "invest_strong_pass": "Strong Pass",
        "score_dashboard": "Score Dashboard",
        "score_dashboard_subtitle": "6-Dimension Evaluation at a Glance",
        # Site Verification
        "site_verification": "Site Verification",
        "site_verification_subtitle": "Website Claims vs Codebase Evidence",
        "overall_credibility": "Overall Credibility",
        "sv_urls_analyzed": "URLs Analyzed",
        "sv_summary": "Summary",
        # Competitive Analysis
        "competitive_analysis": "Competitive Analysis",
        "competitive_subtitle": "Market Positioning Charts",
        # Chart type names
        "chart_magic_quadrant": "Forrester Wave / Magic Quadrant",
        "chart_bcg_matrix": "BCG Growth-Share Matrix",
        "chart_mckinsey_moat": "Tech Moat Analysis",
        "chart_gs_risk_return": "Risk-Adjusted Return Analysis",
        "chart_bubble_3d": "Innovation vs. Commercialization",
        "chart_security_posture": "Security & Privacy Maturity",
        "chart_data_governance": "Data Governance & Transparency",
        # Quadrant labels — Magic Quadrant / Forrester Wave
        "leaders": "Leaders",
        "challengers": "Strong Performers",
        "visionaries": "Contenders",
        "niche_players": "Challengers",
        # Quadrant labels — BCG Matrix
        "stars": "Stars",
        "cash_cows": "Cash Cows",
        "question_marks": "Question Marks",
        "dogs": "Dogs",
        # Quadrant labels — Tech Moat
        "fortress": "Fortress",
        "innovator": "Innovator",
        "commodity": "Commodity",
        "fast_follower": "Fast Follower",
        # Quadrant labels — Security Posture
        "privacy_leader": "Privacy Leader",
        "security_fortress": "Security Fortress",
        "compliance_risk": "Compliance Risk",
        "exposed": "Exposed",
        # Quadrant labels — Data Governance
        "trust_leader": "Trust Leader",
        "opaque_fortress": "Opaque Fortress",
        "transparent_vuln": "Transparent / Vuln",
        "high_risk": "High Risk",
        # Risk-Return / Bubble zones
        "sweet_spot": "Sweet Spot",
        "avoid": "Avoid",
        # Confidence badges
        "confidence_high": "H",
        "confidence_medium": "M",
        "confidence_low": "L",
        # Atlas Optimization Assessment (v2.0)
        "atlas_four_axis": "Atlas Optimization Assessment",
        "atlas_subtitle": "Arc engineering philosophy — 4-axis evaluation (parallel to 6-dimension scoring)",
        "atlas_overall": "Atlas Composite Score",
        "atlas_industry_context": "Industry Context",
        "axis_performance": "Performance",
        "axis_stability": "Stability",
        "axis_lightweight": "Lightweight",
        "axis_security": "Security Strength",
        # Security sub-breakdown
        "security_breakdown": "Security Strength — Sub-Breakdown",
        "security_breakdown_subtitle": "Encryption sophistication is the core differentiator (30% of 50%)",
        "subitem_encryption": "Cryptographic Sophistication",
        "subitem_privacy": "Privacy Protection",
        "subitem_posture": "Basic Hygiene (MFA / SOC2 etc.)",
        "subitem_comms": "Communication Safety",
        "subitem_layers": "Layer Composition",
        # Implementation Capability Matrix (v2.0)
        "impl_matrix": "Implementation Capability Matrix",
        "impl_matrix_subtitle": "30 items × top global competitors — verified / claimed / not implemented / unknown",
        "impl_legend_verified": "Verified",
        "impl_legend_claimed": "Claimed",
        "impl_legend_not_impl": "Not Implemented",
        "impl_legend_unknown": "Unknown",
        # Matrix categories
        "matcat_performance": "Performance",
        "matcat_stability": "Stability",
        "matcat_lightweight": "Lightweight",
        "matcat_encryption": "Encryption (Core Differentiator)",
        "matcat_privacy": "Privacy",
        "matcat_posture": "Basic Hygiene",
        "matcat_comms": "Communication Safety",
        "matcat_layers": "Layer Composition",
        # Competitor Selection Rationales (v0.3.1)
        "competitor_rationales": "Competitor Selection Rationales",
        "competitor_rationales_subtitle": "Why these specific competitors were chosen as comparison targets",
        "rationale_category": "Category",
        "rationale_hq": "HQ",
        "rationale_position": "Market Position",
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
        "improvement_title": "改善提案",
        # Consulting report sections
        "business_summary": "ビジネスサマリー",
        "swot_analysis": "SWOT分析",
        "strengths": "強み",
        "weaknesses": "弱み",
        "opportunities": "機会",
        "threats": "脅威",
        "tech_level": "技術レベル評価",
        "future_outlook": "将来性評価",
        "product_vision": "プロダクトビジョン",
        "viability": "実現可能性",
        "year_1": "1年後",
        "year_3": "3年後",
        "year_5": "5年後",
        "confidence": "信頼度",
        "milestones": "主要マイルストーン",
        "strategic_advice": "戦略アドバイス",
        "immediate_actions": "即座のアクション",
        "medium_term": "中期優先事項",
        "long_term_vision": "長期ビジョン",
        "investment_thesis": "投資判断",
        "recommendation": "推奨度",
        "key_risks": "主要リスク",
        "key_upside": "アップサイド",
        "comparable_companies": "類似企業",
        "valuation_factors": "バリュエーション要因",
        "glossary": "用語集",
        "term": "用語",
        "definition": "定義",
        "ai_model": "使用AIモデル",
        "enables": "これにより可能になること",
        "action": "アクション",
        "rationale": "根拠",
        "impact": "期待される効果",
        "invest_strong": "強く投資推奨",
        "invest_conditions": "条件付き投資",
        "invest_cautious": "慎重",
        "invest_pass": "見送り",
        "invest_strong_pass": "強く見送り",
        "score_dashboard": "スコアダッシュボード",
        "score_dashboard_subtitle": "6次元評価の概要",
        # Site Verification
        "site_verification": "サイト検証",
        "site_verification_subtitle": "Webサイト主張 vs コードベース検証",
        "overall_credibility": "総合信頼性",
        "sv_urls_analyzed": "分析URL",
        "sv_summary": "サマリー",
        # Competitive Analysis
        "competitive_analysis": "競合分析",
        "competitive_subtitle": "市場ポジショニングチャート",
        # Chart type names
        "chart_magic_quadrant": "Forrester Wave / マジック・クアドラント",
        "chart_bcg_matrix": "BCG 成長・シェアマトリックス",
        "chart_mckinsey_moat": "テクノロジーモート分析",
        "chart_gs_risk_return": "リスク調整リターン分析",
        "chart_bubble_3d": "イノベーション vs 商業化",
        "chart_security_posture": "セキュリティ＆プライバシー成熟度",
        "chart_data_governance": "データガバナンス＆透明性",
        # Quadrant labels — Forrester Wave
        "leaders": "リーダー",
        "challengers": "ストロングパフォーマー",
        "visionaries": "コンテンダー",
        "niche_players": "チャレンジャー",
        # Quadrant labels — BCG Matrix
        "stars": "花形",
        "cash_cows": "金のなる木",
        "question_marks": "問題児",
        "dogs": "負け犬",
        # Quadrant labels — Tech Moat
        "fortress": "要塞",
        "innovator": "イノベーター",
        "commodity": "コモディティ",
        "fast_follower": "ファストフォロワー",
        # Quadrant labels — Security Posture
        "privacy_leader": "プライバシーリーダー",
        "security_fortress": "セキュリティ要塞",
        "compliance_risk": "コンプライアンスリスク",
        "exposed": "脆弱",
        # Quadrant labels — Data Governance
        "trust_leader": "信頼リーダー",
        "opaque_fortress": "不透明な要塞",
        "transparent_vuln": "透明だが脆弱",
        "high_risk": "高リスク",
        # Risk-Return / Bubble zones
        "sweet_spot": "最適ゾーン",
        "avoid": "回避",
        # Confidence badges
        "confidence_high": "H",
        "confidence_medium": "M",
        "confidence_low": "L",
        # Atlas 最適化評価 (v2.0)
        "atlas_four_axis": "Atlas 最適化評価",
        "atlas_subtitle": "Arc エンジニアリング哲学 — 4軸並列評価（既存6次元と並列）",
        "atlas_overall": "Atlas 総合スコア",
        "atlas_industry_context": "業界コンテキスト",
        "axis_performance": "高速化",
        "axis_stability": "安定化",
        "axis_lightweight": "軽量化",
        "axis_security": "セキュリティ強度",
        # セキュリティ内訳
        "security_breakdown": "セキュリティ強度 — サブ内訳",
        "security_breakdown_subtitle": "暗号化技術の高度さが核心差別化（50%中30%）",
        "subitem_encryption": "暗号化技術の高度さ",
        "subitem_privacy": "プライバシー保護",
        "subitem_posture": "基本衛生（MFA・SOC2等）",
        "subitem_comms": "通信の安全",
        "subitem_layers": "レイヤー構成",
        # 実装能力マトリックス (v2.0)
        "impl_matrix": "実装能力マトリックス",
        "impl_matrix_subtitle": "30項目 × グローバルトップ競合 — 実装確認済 / 主張あり / 未実装 / 不明",
        "impl_legend_verified": "実装確認済",
        "impl_legend_claimed": "主張あり",
        "impl_legend_not_impl": "未実装",
        "impl_legend_unknown": "不明",
        # マトリックスカテゴリ
        "matcat_performance": "高速化",
        "matcat_stability": "安定化",
        "matcat_lightweight": "軽量化",
        "matcat_encryption": "暗号化（核心差別化）",
        "matcat_privacy": "プライバシー",
        "matcat_posture": "基本衛生",
        "matcat_comms": "通信の安全",
        "matcat_layers": "レイヤー構成",
        # 競合選定理由 (v0.3.1)
        "competitor_rationales": "競合選定理由",
        "competitor_rationales_subtitle": "なぜこの競合企業群を比較対象に選んだのか",
        "rationale_category": "カテゴリ",
        "rationale_hq": "本社",
        "rationale_position": "市場ポジション",
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
    "Technical Originality": "技術独自性",
    "Technology Advancement": "技術先進性",
    "Implementation Depth": "実装深度",
    "Architecture Quality": "アーキテクチャ品質",
    "Architecture Quality (incl. Security)": "アーキテクチャ品質（セキュリティ含む）",
    "Claim Consistency": "主張整合性",
    # v0.3: Security Posture was merged into Architecture Quality; kept here for backward compat
    "Security Posture": "セキュリティ態勢",
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

    # ── Typography system (v2.0 — explicit leading, hierarchical sizes) ──
    # All styles below specify `leading` explicitly to prevent overlap.
    # Size hierarchy: 28 (title) / 20 (H1) / 14 (H2) / 11 (H3) / 10 (body) /
    # 9 (body_dim) / 8.5 (small) / 7.5 (caption) / 7 (footer).
    # Leading: fontSize × 1.3-1.5 generally; body × 1.6 for Japanese readability.
    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base["Title"],
            fontSize=28,
            leading=36,
            textColor=COLOR_BG_DARK,
            spaceAfter=6 * mm,
            alignment=TA_CENTER,
            fontName=font_bold,
        ),
        "subtitle": ParagraphStyle(
            "CustomSubtitle",
            parent=base["Normal"],
            fontSize=14,
            leading=20,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=4 * mm,
            alignment=TA_CENTER,
            fontName=font_normal,
        ),
        "heading1": ParagraphStyle(
            "CustomH1",
            parent=base["Heading1"],
            fontSize=20,                # was 18 — bigger for impact
            leading=26,
            textColor=COLOR_BG_DARK,
            spaceBefore=10 * mm,        # was 8mm — more breathing room
            spaceAfter=5 * mm,
            borderWidth=0,
            borderPadding=0,
            fontName=font_bold,
        ),
        "heading2": ParagraphStyle(
            "CustomH2",
            parent=base["Heading2"],
            fontSize=14,
            leading=18,
            textColor=COLOR_ACCENT,     # Arc sky #5271FF
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
            fontName=font_bold,
        ),
        "heading3": ParagraphStyle(
            "CustomH3",
            parent=base["Normal"],
            fontSize=11,
            leading=14,
            textColor=COLOR_TEXT,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            fontName=font_bold,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=base["Normal"],
            fontSize=10,
            leading=16,                 # was 14 — JA needs more (1.6 ratio)
            textColor=COLOR_TEXT,
            spaceAfter=3 * mm,
            fontName=font_normal,
        ),
        "body_small": ParagraphStyle(
            "CustomBodySmall",
            parent=base["Normal"],
            fontSize=8.5,               # was 8 — slightly larger for readability
            leading=12,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=2 * mm,
            fontName=font_normal,
        ),
        "caption": ParagraphStyle(
            "CustomCaption",
            parent=base["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=1 * mm,
            fontName=font_normal,
        ),
        "footer": ParagraphStyle(
            "CustomFooter",
            parent=base["Normal"],
            fontSize=7,
            leading=9,
            textColor=COLOR_TEXT_DIM,
            alignment=TA_CENTER,
            fontName=font_normal,
        ),
        "score_large": ParagraphStyle(
            "ScoreLarge",
            parent=base["Normal"],
            fontSize=48,
            leading=56,
            textColor=COLOR_BG_DARK,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
            fontName=font_bold,
        ),
        "grade_label": ParagraphStyle(
            "GradeLabel",
            parent=base["Normal"],
            fontSize=16,
            leading=22,
            textColor=COLOR_TEXT_DIM,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
            fontName=font_normal,
        ),
        "flag_title": ParagraphStyle(
            "FlagTitle",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT,
            spaceAfter=1 * mm,
            fontName=font_bold,
        ),
        "flag_desc": ParagraphStyle(
            "FlagDesc",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=3 * mm,
            leftIndent=10,
            fontName=font_normal,
        ),
        "center": ParagraphStyle(
            "CenterBody",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
            fontName=font_normal,
        ),
        "body_dim": ParagraphStyle(
            "CustomBodyDim",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=COLOR_TEXT_DIM,
            spaceAfter=2 * mm,
            fontName=font_normal,
        ),
        "nda_notice": ParagraphStyle(
            "NDANotice",
            parent=base["Normal"],
            fontSize=7,
            leading=10,
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

        cr = result.consulting_report

        # Cover page
        story.extend(self._build_cover_page(result))

        # --- Consulting report sections (if available) ---
        if cr is not None:
            # Score dashboard (bar chart overview) — first page after cover
            story.append(PageBreak())
            story.extend(self._build_score_dashboard(cr))

            # Business summary
            story.append(PageBreak())
            story.extend(self._build_business_summary(cr))

            # SWOT
            story.append(PageBreak())
            story.extend(self._build_swot_page(cr))

            # Score breakdown + Tech level (combined — they belong together visually)
            story.append(PageBreak())
            story.extend(self._build_consulting_scores(cr))
            # Tech level flows naturally after scores; PDF engine will page-break if needed
            story.extend(self._build_tech_level_page(cr))

            # Future outlook + Strategic advice + Investment thesis flow together
            # (removed forced PageBreaks between — let PDF engine handle overflow naturally
            #  to avoid sparse half-empty pages)
            story.append(PageBreak())
            story.extend(self._build_future_outlook_page(cr))
            story.extend(self._build_strategic_advice_page(cr))
            story.extend(self._build_investment_thesis_page(cr))

            # Red flags — allowed to flow with investment thesis if space permits
            if cr.red_flags:
                story.extend(self._build_consulting_red_flags(cr))

            # Site Verification
            if cr.site_verification and cr.site_verification.items:
                story.append(PageBreak())
                story.extend(self._build_site_verification_page(cr))

            # Competitive Analysis
            if cr.competitive_analysis and cr.competitive_analysis.markets:
                story.extend(self._build_competitive_analysis_pages(cr))

            # Atlas Optimization Assessment (v2.0)
            if cr.atlas_four_axis and cr.atlas_four_axis.axes:
                story.append(PageBreak())
                story.extend(self._build_atlas_four_axis_page(cr))
                # Security sub-breakdown only if security axis has sub_items
                security_axis = next(
                    (a for a in cr.atlas_four_axis.axes if a.axis_key == "security"),
                    None,
                )
                if security_axis and security_axis.sub_items:
                    story.append(PageBreak())
                    story.extend(self._build_atlas_security_breakdown_page(cr, security_axis))

            # Competitor Selection Rationales (v0.3.1)
            if cr.competitor_rationales:
                story.append(PageBreak())
                story.extend(self._build_competitor_rationales_page(cr))

            # Implementation Capability Matrix (v2.0)
            if cr.implementation_matrix and cr.implementation_matrix.items:
                story.extend(self._build_implementation_matrix_page(cr))

        else:
            # Standard report flow (no consulting data)
            # Executive summary
            story.append(PageBreak())
            story.extend(self._build_executive_summary(result))

            # Score breakdown
            story.extend(self._build_score_breakdown(result))

            # Multi-AI provider results
            if result.ai_results:
                story.extend(self._build_ai_provider_section(result))

            # Red flags
            if result.score and result.score.red_flags:
                story.append(PageBreak())
                story.extend(self._build_red_flags_section(result))

        # Heuristic sections — only when NOT in consulting-only mode
        # (consulting PDF gets its data from AI evaluation, not heuristics)
        has_heuristic_data = (
            result.code_analysis.total_files > 0
            or result.git_forensics.total_commits > 0
        )

        if has_heuristic_data:
            # Codebase metrics
            story.append(PageBreak())
            story.extend(self._build_codebase_metrics(result))

            # Git forensics
            if result.git_forensics.total_commits > 0:
                story.extend(self._build_git_forensics(result))

            # Consistency check
            story.extend(self._build_consistency_section(result))

        # Glossary (consulting only)
        if cr is not None:
            story.append(PageBreak())
            story.extend(self._build_glossary_page(cr))

        # Cost breakdown — skip if zero (consulting mode uses no API)
        if result.total_cost_usd > 0:
            story.extend(self._build_cost_section(result))

        # Purge certificate
        if purge_cert is not None:
            story.append(PageBreak())
            story.extend(self._build_purge_certificate(purge_cert))

        # Build PDF with footer (dark cover on first page)
        doc.build(story, onFirstPage=self._add_cover_bg, onLaterPages=self._add_footer)

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
        """Build the cover page — dark theme with Atlas Associates branding."""
        s = self._styles
        t = self._t
        elements: list = []

        # White/light styles for dark background
        cover_title = ParagraphStyle(
            "CoverTitle",
            fontName="HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold",
            fontSize=28,
            leading=36,
            textColor=colors.white,
            alignment=1,
            spaceAfter=6 * mm,
        )
        cover_subtitle = ParagraphStyle(
            "CoverSubtitle",
            fontName="HeiseiMin-W3" if self._lang == "ja" else "Helvetica",
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#9ca3af"),
            alignment=1,
            spaceAfter=4 * mm,
        )
        cover_center = ParagraphStyle(
            "CoverCenter",
            fontName="HeiseiMin-W3" if self._lang == "ja" else "Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#d1d5db"),
            alignment=1,
            spaceAfter=2 * mm,
        )
        cover_small = ParagraphStyle(
            "CoverSmall",
            fontName="HeiseiMin-W3" if self._lang == "ja" else "Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6b7280"),
            alignment=0,
            spaceAfter=1 * mm,
        )

        # Spacer (below logo area drawn by canvas)
        elements.append(Spacer(1, 5 * cm))

        # Title prefix
        elements.append(
            Paragraph(
                f'<font color="#5271FF" size="12">{t["title_prefix"]}</font>',
                cover_center,
            )
        )
        elements.append(Spacer(1, 6 * mm))

        # Title
        elements.append(Paragraph(t["report_title"], cover_title))
        elements.append(Spacer(1, 2 * mm))

        # Project name — with horizontal rule accent
        elements.append(Paragraph(result.project_name, cover_subtitle))
        elements.append(Spacer(1, 3 * mm))

        # Thin accent line below project name
        elements.append(
            HRFlowable(
                width="30%", thickness=0.5,
                color=colors.HexColor("#5271FF"),
                spaceAfter=8 * mm,
                hAlign="CENTER",
            )
        )
        elements.append(Spacer(1, 6 * mm))

        # Score display (consulting report)
        cr = result.consulting_report
        if cr and cr.overall_score > 0:
            grade = cr.grade or "?"
            grade_color = GRADE_COLORS.get(grade, colors.HexColor("#9ca3af"))

            # Grade line first (above score)
            grade_label = f'{t["grade_prefix"]}: {grade}'
            rec = _PDF_GRADE_REC.get(self._lang, _PDF_GRADE_REC["en"])
            recommendation = rec.get(grade, "")
            elements.append(
                Paragraph(
                    f'<font color="#5271FF" size="14"><b>{grade_label}</b></font>'
                    f'  <font color="#9ca3af" size="10">{recommendation}</font>',
                    cover_center,
                )
            )
            elements.append(Spacer(1, 4 * mm))

            # Large score number — use matching fontSize and leading to prevent overlap
            score_style = ParagraphStyle(
                "CoverScore", fontName="Helvetica-Bold", fontSize=56,
                leading=64, alignment=1, textColor=colors.white,
            )
            score_text = (
                f'<font color="{colors.white.hexval()}">{cr.overall_score:.0f}</font>'
                f'<font color="#6b7280" size="20"> / 100</font>'
            )
            elements.append(Paragraph(score_text, score_style))
            elements.append(Spacer(1, 8 * mm))
        elif result.score is not None:
            # Fallback to heuristic score
            score = result.score
            grade_color = GRADE_COLORS.get(score.grade, COLOR_TEXT_DIM)

            grade_text = f'{t["grade_prefix"]}: {score.grade}'
            elements.append(
                Paragraph(
                    f'<font color="#5271FF" size="14"><b>{grade_text}</b></font>',
                    cover_center,
                )
            )
            elements.append(Spacer(1, 4 * mm))

            score_style = ParagraphStyle(
                "CoverScore", fontName="Helvetica-Bold", fontSize=56,
                leading=64, alignment=1, textColor=colors.white,
            )
            score_text = (
                f'<font color="{colors.white.hexval()}">{score.overall_score:.0f}</font>'
                f'<font color="#6b7280" size="20"> / 100</font>'
            )
            elements.append(Paragraph(score_text, score_style))
            elements.append(Spacer(1, 8 * mm))

        # AI model attribution
        if cr and cr.ai_model_used:
            elements.append(
                Paragraph(
                    f'<font color="#5271FF" size="11">'
                    f'<b>{t["ai_model"]}: {cr.ai_model_used}</b></font>',
                    cover_center,
                )
            )
            elements.append(Spacer(1, 6 * mm))

        # Metadata
        elements.append(
            Paragraph(
                f"{t['analysis_id']}: {result.analysis_id}",
                cover_small,
            )
        )
        elements.append(
            Paragraph(
                f"{t['date']}: {result.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
                cover_small,
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

    def _build_ai_provider_section(self, result: AnalysisResult) -> list:
        """マルチAIプロバイダーの分析結果セクションを生成。"""
        s = self._styles
        t = self._t
        elements: list = []

        ai_title = "AI Provider Analysis" if self._lang == "en" else "AIプロバイダー分析"
        elements.append(Paragraph(ai_title, s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        # プロバイダーカラー
        provider_colors = {
            "claude": COLOR_ORANGE,
            "gemini": COLOR_ACCENT,
            "chatgpt": COLOR_GREEN,
        }

        # 各プロバイダーのサマリー
        for name, ai_result in result.ai_results.items():
            if ai_result.error:
                elements.append(Paragraph(
                    f"<b>{name.capitalize()}</b>: Error - {ai_result.error}",
                    s["body_small"],
                ))
                continue

            color = provider_colors.get(name, COLOR_TEXT)
            elements.append(Paragraph(
                f'<font color="{color.hexval()}"><b>{name.capitalize()}</b></font>'
                f' ({ai_result.model_id}) — '
                f'Verdict: <b>{ai_result.verdict}</b> | '
                f'Confidence: {ai_result.confidence:.0f}%',
                s["body"],
            ))
            if ai_result.executive_summary:
                elements.append(Paragraph(ai_result.executive_summary, s["body_small"]))
            elements.append(Spacer(1, 3 * mm))

        # プロバイダー比較テーブル
        valid_providers = [
            (name, r) for name, r in result.ai_results.items()
            if r.error is None and r.dimension_scores
        ]

        if valid_providers:
            elements.append(Spacer(1, 4 * mm))
            comparison_title = "Provider Score Comparison" if self._lang == "en" else "プロバイダースコア比較"
            elements.append(Paragraph(comparison_title, s["heading2"]))

            # v0.3: 5 dimensions (security_posture merged into architecture_quality)
            dim_keys = [
                "technical_originality", "technology_advancement",
                "implementation_depth", "architecture_quality",
                "claim_consistency",
            ]
            dim_labels_en = {
                "technical_originality": "Originality",
                "technology_advancement": "Advancement",
                "implementation_depth": "Implementation",
                "architecture_quality": "Arch. + Security",
                "claim_consistency": "Consistency",
            }
            dim_labels_ja = {
                "technical_originality": "独自性",
                "technology_advancement": "先進性",
                "implementation_depth": "実装深度",
                "architecture_quality": "設計+セキュリティ",
                "claim_consistency": "整合性",
            }
            dim_labels = dim_labels_ja if self._lang == "ja" else dim_labels_en

            # ヘッダー行
            header = [t.get("dimension", "Dimension")]
            for name, _ in valid_providers:
                header.append(name.capitalize())
            avg_label = "Avg" if self._lang == "en" else "平均"
            header.append(avg_label)

            table_data = [header]
            for key in dim_keys:
                row = [dim_labels.get(key, key)]
                scores = []
                for _, r in valid_providers:
                    score_val = r.dimension_scores.get(key, 0)
                    row.append(f"{score_val:.0f}")
                    scores.append(score_val)
                avg = sum(scores) / len(scores) if scores else 0
                row.append(f"{avg:.0f}")
                table_data.append(row)

            # コスト行
            cost_label = "Cost (USD)" if self._lang == "en" else "コスト (USD)"
            cost_row = [cost_label]
            total_cost = 0.0
            for _, r in valid_providers:
                cost_row.append(f"${r.cost_usd:.4f}")
                total_cost += r.cost_usd
            cost_row.append(f"${total_cost:.4f}")
            table_data.append(cost_row)

            n_cols = len(header)
            col_width = 15 * cm / n_cols
            col_widths = [col_width] * n_cols

            font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"

            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), font_header),
                ("FONTNAME", (0, 1), (-1, -1), font_body),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)

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

    # Atlas Associates Inc. credit — hardcoded, not configurable.
    # This attribution is required by the license and must not be removed.
    _CREDIT = "Powered by Due Diligence Engine \u2014 Takayuki Miyano / Atlas Associates"

    def _add_cover_bg(self, canvas, doc) -> None:
        """Draw dark background + logo on cover page, then add standard footer."""
        canvas.saveState()
        page_width, page_height = A4

        # Full-page dark background
        canvas.setFillColor(COLOR_BG_DARK)
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # Atlas Associates logo text (top-left)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(2 * cm, page_height - 2 * cm, "ATLAS ASSOCIATES")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#9ca3af"))
        canvas.drawString(2 * cm, page_height - 2.5 * cm, "Technology Due Diligence")

        # Decorative accent line
        canvas.setStrokeColor(COLOR_ACCENT)
        canvas.setLineWidth(2)
        canvas.line(2 * cm, page_height - 2.8 * cm, 6 * cm, page_height - 2.8 * cm)

        # Bottom credit
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawCentredString(
            page_width / 2,
            1.2 * cm,
            self._CREDIT,
        )

        # Page number
        page_label = self._t.get("page", "Page")
        canvas.drawRightString(
            page_width - 2 * cm,
            1.2 * cm,
            f"{page_label} {doc.page}",
        )

        canvas.restoreState()

    def _add_footer(self, canvas, doc) -> None:
        """Add NDA compliance footer + Atlas Associates credit to every page."""
        canvas.saveState()
        page_width, page_height = A4

        # Atlas Associates credit (left side, every page)
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(COLOR_TEXT_DIM)
        canvas.drawString(
            2 * cm,
            0.8 * cm,
            self._CREDIT,
        )

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

    # ===================================================================
    # Consulting Report build methods
    # ===================================================================

    def _build_score_dashboard(self, cr) -> list:
        """Score dashboard with overall score + 6-dimension horizontal bar chart."""
        t = self._t
        s = self._styles
        elements: list = []

        # Title
        elements.append(Paragraph(t["score_dashboard"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )
        elements.append(
            Paragraph(t["score_dashboard_subtitle"], s["body_dim"])
        )
        elements.append(Spacer(1, 6 * mm))

        # --- Overall score large display ---
        grade = cr.grade or "?"
        grade_color = GRADE_COLORS.get(grade, COLOR_TEXT_DIM)

        # Grade label first (above score to prevent overlap)
        grade_label = f'{t["grade_prefix"]}: {grade}'
        rec = _PDF_GRADE_REC.get(self._lang, _PDF_GRADE_REC["en"])
        recommendation = rec.get(grade, "")
        grade_line = (
            f'<font color="{grade_color.hexval()}" size="14"><b>{grade_label}</b></font>'
            f'  <font color="{COLOR_TEXT_DIM.hexval()}" size="10">{recommendation}</font>'
        )
        elements.append(Paragraph(grade_line, s["center"]))
        elements.append(Spacer(1, 2 * mm))

        # Large score — use explicit leading to match font size
        score_large_style = ParagraphStyle(
            "DashboardScoreLarge", fontName="Helvetica-Bold", fontSize=48,
            leading=56, alignment=1, textColor=grade_color,
        )
        overall_text = (
            f'{cr.overall_score:.0f}'
            f'<font color="{COLOR_TEXT_DIM.hexval()}" size="18"> / 100</font>'
        )
        elements.append(Paragraph(overall_text, score_large_style))
        elements.append(Spacer(1, 8 * mm))

        # --- 5-Dimension bar chart (v0.3: Security Posture merged into Architecture Quality) ---
        dim_name_map = {
            "technical_originality": "Technical Originality",
            "technology_advancement": "Technology Advancement",
            "implementation_depth": "Implementation Depth",
            "architecture_quality": "Architecture Quality (incl. Security)",
            "claim_consistency": "Claim Consistency",
        }
        _dim_desc_en = {
            "technical_originality": "Novelty of algorithms, patents, and proprietary tech",
            "technology_advancement": "Modernity of stack, frameworks, and tooling",
            "implementation_depth": "Test coverage, error handling, production readiness",
            "architecture_quality": "Code structure + security maturity (encryption, auth, vulns)",
            "claim_consistency": "Alignment between marketing claims and actual code",
        }
        _dim_desc_ja = {
            "technical_originality": "アルゴリズム・特許・独自技術の新規性",
            "technology_advancement": "技術スタック・フレームワークの先進性",
            "implementation_depth": "テストカバレッジ・エラー処理・本番運用品質",
            "architecture_quality": "コード構造 + セキュリティ成熟度（暗号化・認証・脆弱性）",
            "claim_consistency": "マーケティング主張と実装コードの整合性",
        }
        weights = {
            "technical_originality": 0.20,
            "technology_advancement": 0.20,
            "implementation_depth": 0.20,
            "architecture_quality": 0.20,
            "claim_consistency": 0.20,
        }

        # Collect dimension data
        dims = []
        for key, en_name in dim_name_map.items():
            dim = cr.dimension_scores.get(key)
            if not dim:
                continue
            name = _DIM_NAME_JA.get(en_name, en_name) if self._lang == "ja" else en_name
            desc = _dim_desc_ja.get(key, "") if self._lang == "ja" else _dim_desc_en.get(key, "")
            w = weights.get(key, 0)
            dims.append((name, dim.score, dim.level, w, desc))

        if not dims:
            return elements

        # Drawing dimensions
        bar_max_w = 280  # max bar width in points
        row_h = 44       # height per row (increased for description line)
        label_w = 140    # label area width
        chart_w = label_w + bar_max_w + 80  # total width
        chart_h = len(dims) * row_h + 10

        d = Drawing(chart_w, chart_h)

        for i, (name, score, level, weight, desc) in enumerate(dims):
            y = chart_h - (i + 1) * row_h + 14

            # Dimension label (left, bold)
            font_name = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            d.add(String(0, y + 4, name, fontName=font_name, fontSize=9,
                         fillColor=COLOR_TEXT))

            # Dimension description (below label, small gray text)
            desc_font = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
            d.add(String(0, y - 8, desc, fontName=desc_font, fontSize=6.5,
                         fillColor=COLOR_TEXT_DIM))

            # Background bar (gray track)
            d.add(Rect(label_w, y, bar_max_w, 16,
                        fillColor=colors.HexColor("#e2e8f0"),
                        strokeColor=None, strokeWidth=0))

            # Score bar (Arc brand: black + sky blue dominant)
            bar_w = max(2, (score / 100) * bar_max_w)
            if score >= 75:
                bar_color = COLOR_ACCENT                  # Arc sky #5271FF
            elif score >= 50:
                bar_color = COLOR_ACCENT_DARK             # Arc sky darker
            elif score >= 30:
                bar_color = colors.HexColor("#000000")    # pure black
            else:
                bar_color = colors.HexColor("#6b2a2a")    # muted red (warning)
            d.add(Rect(label_w, y, bar_w, 16,
                        fillColor=bar_color,
                        strokeColor=None, strokeWidth=0))

            # Score text (right of bar)
            score_str = f"{score:.0f}  Lv.{level}  ({weight:.0%})"
            d.add(String(label_w + bar_max_w + 6, y + 3, score_str,
                         fontName="Helvetica", fontSize=8,
                         fillColor=COLOR_TEXT_DIM))

        elements.append(d)
        elements.append(Spacer(1, 8 * mm))

        # Weighted total line
        weighted_total = sum(sc * w for _, sc, _, w, _ in dims)
        if self._lang == "ja":
            total_text = f"加重合計スコア: <b>{weighted_total:.1f}</b> / 100"
        else:
            total_text = f"Weighted Total Score: <b>{weighted_total:.1f}</b> / 100"
        elements.append(Paragraph(total_text, s["body"]))

        # Score barometer
        elements.append(Spacer(1, 6 * mm))
        barometer = Drawing(chart_w, 40)
        # Track
        barometer.add(Rect(label_w, 15, bar_max_w, 10,
                           fillColor=colors.HexColor("#e2e8f0"),
                           strokeColor=None, strokeWidth=0))
        # Colored segments (Arc brand: black→sky blue gradient, red for fail)
        segments = [
            (0, 40, colors.HexColor("#6b2a2a")),       # muted red (F)
            (40, 60, colors.HexColor("#000000")),      # black (D)
            (60, 75, colors.HexColor("#1a1a2e")),      # near-black (C)
            (75, 90, COLOR_ACCENT_DARK),               # Arc sky darker (B)
            (90, 100, COLOR_ACCENT),                   # Arc sky (A)
        ]
        for lo, hi, clr in segments:
            x = label_w + (lo / 100) * bar_max_w
            w = ((hi - lo) / 100) * bar_max_w
            barometer.add(Rect(x, 15, w, 10, fillColor=clr,
                               strokeColor=None, strokeWidth=0))

        # Position marker
        marker_x = label_w + (cr.overall_score / 100) * bar_max_w
        barometer.add(Rect(marker_x - 1.5, 12, 3, 16,
                           fillColor=COLOR_TEXT, strokeColor=None, strokeWidth=0))

        # Grade labels
        grade_labels = [("F", 20), ("D", 50), ("C", 67.5), ("B", 82.5), ("A", 95)]
        for g_label, pos in grade_labels:
            x = label_w + (pos / 100) * bar_max_w
            barometer.add(String(x - 3, 2, g_label, fontName="Helvetica-Bold",
                                 fontSize=8, fillColor=COLOR_TEXT_DIM))

        elements.append(barometer)

        return elements

    def _build_business_summary(self, cr) -> list:
        """Executive business summary page."""
        from src.models import ConsultingReport

        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["business_summary"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        # AI model attribution
        if cr.ai_model_used:
            elements.append(
                Paragraph(f"{t['ai_model']}: {cr.ai_model_used}", s["body_dim"])
            )
            elements.append(Spacer(1, 4 * mm))

        # Grade badge
        grade = cr.grade or "N/A"
        grade_color = GRADE_COLORS.get(grade, COLOR_TEXT_DIM)
        score_text = f"{cr.overall_score:.0f}/100 — {t['grade_prefix']}: {grade}"
        elements.append(
            Paragraph(
                f'<font color="{grade_color.hexval()}">{score_text}</font>',
                s["heading2"],
            )
        )
        elements.append(Spacer(1, 6 * mm))

        # Business summary text
        if cr.executive_summary_business:
            for para in cr.executive_summary_business.split("\n\n"):
                para = para.strip()
                if para:
                    elements.append(Paragraph(para, s["body"]))
                    elements.append(Spacer(1, 3 * mm))

        # Technical summary
        if cr.executive_summary:
            elements.append(Spacer(1, 4 * mm))
            elements.append(
                Paragraph(t.get("exec_summary", "Executive Summary"), s["heading2"])
            )
            elements.append(Spacer(1, 3 * mm))
            for para in cr.executive_summary.split("\n\n"):
                para = para.strip()
                if para:
                    elements.append(Paragraph(para, s["body"]))
                    elements.append(Spacer(1, 3 * mm))

        return elements

    def _build_swot_page(self, cr) -> list:
        """SWOT analysis as visual 2×2 grid with overflow protection (v0.3.1 fix).

        Uses ReportLab Table + KeepInFrame to ENFORCE cell boundaries:
        - Colored header bar (Strengths=green, Weaknesses=gray, Opportunities=Arc sky, Threats=red)
        - Cell body content is CLIPPED if it exceeds the fixed row height (no bleeding
          into adjacent cells like in v0.3.0)
        - Max 3 items per cell + 180-char truncation per item
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle, KeepInFrame

        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["swot_analysis"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        swot = cr.swot
        # 4 quadrants: (label, items, header color)
        quadrants = [
            (t["strengths"], swot.strengths, colors.HexColor("#2d5a3d")),       # green
            (t["weaknesses"], swot.weaknesses, colors.HexColor("#4a4a4a")),     # dark gray
            (t["opportunities"], swot.opportunities, COLOR_ACCENT),             # Arc sky
            (t["threats"], swot.threats, colors.HexColor("#6b2a2a")),           # muted red
        ]

        # Style for cell content
        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
        # Colored header — rendered as a separate "tag" row above body
        cell_header_style = ParagraphStyle(
            "SWOTHeader", fontName=font_header, fontSize=11,
            textColor=COLOR_WHITE, leading=14, alignment=TA_LEFT,
            leftIndent=0, rightIndent=0,
            spaceBefore=0, spaceAfter=0,
        )
        # Body items — smaller font than before (8pt) + tighter leading (11)
        cell_item_style = ParagraphStyle(
            "SWOTItem", fontName=font_body, fontSize=8,
            textColor=COLOR_TEXT, leading=11,
            spaceAfter=3, leftIndent=2, rightIndent=2,
        )
        cell_extra_style = ParagraphStyle(
            "SWOTExtra", fontName=font_body, fontSize=7.5,
            textColor=COLOR_TEXT_DIM, leading=10,
            spaceAfter=3, leftIndent=8, rightIndent=2,
        )

        def _truncate(s: str, n: int = 180) -> str:
            """Truncate long strings with ellipsis to prevent cell overflow."""
            if not s:
                return ""
            s = s.strip()
            return s if len(s) <= n else s[: n - 1] + "…"

        def _build_cell(title: str, items: list, color_hex) -> "KeepInFrame":
            """Build one SWOT quadrant cell wrapped in KeepInFrame (mode=shrink)."""
            cell_flow: list = []
            # Colored header strip (background via a small Table, not <para>)
            header_row = RLTable(
                [[Paragraph(f"<b>{title}</b>", cell_header_style)]],
                colWidths=[82 * mm - 4],
            )
            header_row.setStyle(RLTableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), color_hex),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            cell_flow.append(header_row)
            cell_flow.append(Spacer(1, 2))

            if not items:
                cell_flow.append(Paragraph("—", cell_item_style))
            else:
                # Max 3 items per cell to fit within fixed row height
                for item in items[:3]:
                    point = _truncate(item.point, 80)
                    explanation = _truncate(item.explanation, 180)
                    bullet = f"<b>{point}</b>: {explanation}"
                    cell_flow.append(Paragraph(f"• {bullet}", cell_item_style))

                    extra = (
                        item.business_analogy
                        or item.business_impact
                        or item.potential_value
                        or item.mitigation
                    )
                    if extra:
                        cell_flow.append(
                            Paragraph(f"<i>{_truncate(extra, 140)}</i>", cell_extra_style)
                        )

            # KeepInFrame clips content to fit cell (mode="shrink" → auto-scale down if overflow)
            return KeepInFrame(
                maxWidth=82 * mm - 4,
                maxHeight=110 * mm - 4,
                content=cell_flow,
                mode="shrink",  # shrink to fit, never overflow
                hAlign="LEFT",
                vAlign="TOP",
            )

        # Build 2×2 table data
        cells = [_build_cell(title, items, color) for title, items, color in quadrants]
        table_data = [
            [cells[0], cells[1]],   # Strengths | Weaknesses
            [cells[2], cells[3]],   # Opportunities | Threats
        ]

        col_w = 82 * mm
        row_h = 110 * mm
        tbl = RLTable(
            table_data,
            colWidths=[col_w, col_w],
            rowHeights=[row_h, row_h],
        )
        tbl.setStyle(RLTableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ]))
        elements.append(tbl)

        return elements

    def _build_consulting_scores(self, cr) -> list:
        """Dimension scores from consulting report with business explanations."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["score_breakdown"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        # v0.3: 5 dimensions, Security Posture merged into Architecture Quality
        dim_name_map = {
            "technical_originality": "Technical Originality",
            "technology_advancement": "Technology Advancement",
            "implementation_depth": "Implementation Depth",
            "architecture_quality": "Architecture Quality (incl. Security)",
            "claim_consistency": "Claim Consistency",
        }

        weights = {
            "technical_originality": 0.20,
            "technology_advancement": 0.20,
            "implementation_depth": 0.20,
            "architecture_quality": 0.20,
            "claim_consistency": 0.20,
        }

        # Score table (use Paragraph cells for proper CID font rendering)
        cell_style_h = ParagraphStyle(
            "ScoreH", fontName=s["heading1"].fontName, fontSize=9,
            textColor=COLOR_WHITE, leading=12, alignment=1,
        )
        cell_style_name = ParagraphStyle(
            "ScoreName", fontName=s["heading1"].fontName, fontSize=9,
            textColor=COLOR_TEXT, leading=12,
        )
        cell_style_val = ParagraphStyle(
            "ScoreVal", fontName="Helvetica", fontSize=9,
            textColor=COLOR_TEXT, leading=12, alignment=1,
        )

        header = [
            Paragraph(t["dimension"], ParagraphStyle("DimH", parent=cell_style_h, alignment=0)),
            Paragraph(t["score"], cell_style_h),
            Paragraph("Lv.", cell_style_h),
            Paragraph(t["weight"], cell_style_h),
            Paragraph(t["weighted_score"], cell_style_h),
        ]
        rows = [header]

        for key in dim_name_map:
            dim = cr.dimension_scores.get(key)
            if not dim:
                continue
            name = dim_name_map[key]
            if self._lang == "ja":
                name = _DIM_NAME_JA.get(name, name)
            w = weights.get(key, 0)
            rows.append([
                Paragraph(name, cell_style_name),
                Paragraph(f"{dim.score:.0f}", cell_style_val),
                Paragraph(f"Lv.{dim.level}", cell_style_val),
                Paragraph(f"{w:.0%}", cell_style_val),
                Paragraph(f"{dim.score * w:.1f}", cell_style_val),
            ])

        if len(rows) > 1:
            table = Table(rows, colWidths=[140, 50, 40, 50, 70])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_SURFACE),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_LIGHT_BG, COLOR_WHITE]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 6 * mm))

        # Detailed rationale per dimension — wrapped in KeepTogether to prevent
        # orphans (e.g., heading at bottom of page with body on next page).
        for key in dim_name_map:
            dim = cr.dimension_scores.get(key)
            if not dim or not dim.rationale:
                continue
            name = dim_name_map[key]
            if self._lang == "ja":
                name = _DIM_NAME_JA.get(name, name)

            block: list = [
                Paragraph(f"<b>{name}</b> — Lv.{dim.level} {dim.label}", s["body"]),
                Paragraph(dim.rationale, s["body"]),
            ]
            if dim.business_explanation:
                block.append(Paragraph(f"<i>{dim.business_explanation}</i>", s["body_dim"]))
            if dim.enables:
                block.append(Paragraph(f"{t['enables']}: {dim.enables}", s["body_dim"]))
            block.append(Spacer(1, 4 * mm))
            elements.append(KeepTogether(block))

        return elements

    def _build_tech_level_page(self, cr) -> list:
        """Tech level summary with visual gauge."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(t["tech_level"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )

        tls = cr.tech_level_summary
        if not tls:
            return elements

        level = int(tls.get("overall_level", 0))
        label = tls.get("overall_label", "")
        explanation = tls.get("plain_explanation", "")

        # ── Per-dimension tech levels (v0.3: 5 dimensions) ──
        # Shows a compact horizontal bar per dimension for visual richness.
        dim_name_map = {
            "technical_originality": "Technical Originality",
            "technology_advancement": "Technology Advancement",
            "implementation_depth": "Implementation Depth",
            "architecture_quality": "Architecture Quality (incl. Security)",
            "claim_consistency": "Claim Consistency",
        }
        dim_levels: list[tuple[str, int, str]] = []
        for key, en_name in dim_name_map.items():
            dim = cr.dimension_scores.get(key)
            if not dim:
                continue
            display_name = _DIM_NAME_JA.get(en_name, en_name) if self._lang == "ja" else en_name
            dim_levels.append((display_name, int(dim.level or 0), dim.label or ""))

        if dim_levels:
            label_font = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            val_font = "Helvetica-Bold"
            label_w = 150
            seg_w = 24
            gap = 2
            row_h = 26
            chart_w = label_w + 10 * (seg_w + gap) + 80
            chart_h = len(dim_levels) * row_h + 6

            dgrid = Drawing(chart_w, chart_h)
            for i, (name, lv, lbl) in enumerate(dim_levels):
                y = chart_h - (i + 1) * row_h + 6
                # Dimension name (left)
                dgrid.add(String(0, y + 4, name, fontName=label_font, fontSize=8.5,
                                 fillColor=COLOR_TEXT))
                # 10-segment gauge
                for j in range(10):
                    x = label_w + j * (seg_w + gap)
                    if j < lv:
                        fill = COLOR_ACCENT if lv >= 7 else (
                            COLOR_ACCENT_DARK if lv >= 5 else colors.HexColor("#000000")
                        )
                    else:
                        fill = colors.HexColor("#e2e8f0")
                    dgrid.add(Rect(x, y, seg_w, 14,
                                   fillColor=fill, strokeColor=None, strokeWidth=0))
                # Lv.X/10 text right
                text_x = label_w + 10 * (seg_w + gap) + 6
                dgrid.add(String(text_x, y + 3, f"Lv.{lv}/10",
                                 fontName=val_font, fontSize=8.5,
                                 fillColor=COLOR_TEXT_DIM))
            elements.append(dgrid)
            elements.append(Spacer(1, 6 * mm))

        # ── Overall tech level gauge (larger, summary) ──
        overall_label = t.get("overall_label", "Overall Tech Level") if self._lang == "en" else "総合テックレベル"
        elements.append(Paragraph(f"<b>{overall_label}</b>", s["heading2"]))

        gauge_w = 380
        gauge_h = 30
        seg_w = 32
        seg_h = 20
        gap = 3

        d = Drawing(gauge_w, gauge_h)
        for i in range(10):
            x = i * (seg_w + gap)
            if i < level:
                fill = COLOR_ACCENT
            else:
                fill = colors.HexColor("#e2e8f0")
            d.add(Rect(x, 4, seg_w, seg_h,
                        fillColor=fill, strokeColor=None, strokeWidth=0))

        text_x = 10 * (seg_w + gap) + 8
        level_str = f"Lv.{level}/10"
        d.add(String(text_x, 10, level_str,
                     fontName="Helvetica-Bold", fontSize=12,
                     fillColor=COLOR_TEXT))
        elements.append(d)
        elements.append(Spacer(1, 4 * mm))

        if label:
            elements.append(Paragraph(f"<b>{label}</b>", s["body"]))

        if explanation:
            elements.append(Paragraph(explanation, s["body"]))

        return elements

    def _build_future_outlook_page(self, cr) -> list:
        """Future outlook with timeline projections."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["future_outlook"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        fo = cr.future_outlook

        if fo.product_vision:
            elements.append(Paragraph(f"<b>{t['product_vision']}</b>", s["body"]))
            elements.append(Paragraph(fo.product_vision, s["body"]))
            elements.append(Spacer(1, 4 * mm))

        if fo.viability_assessment:
            elements.append(Paragraph(f"<b>{t['viability']}</b>", s["body"]))
            elements.append(Paragraph(fo.viability_assessment, s["body"]))
            elements.append(Spacer(1, 6 * mm))

        # Projections
        confidence_colors = {
            "high": COLOR_GREEN,
            "medium": COLOR_YELLOW,
            "low": COLOR_RED,
        }

        for label_key, proj in [
            ("year_1", fo.year_1),
            ("year_3", fo.year_3),
            ("year_5", fo.year_5),
        ]:
            if proj is None:
                continue
            conf_color = confidence_colors.get(proj.confidence, COLOR_TEXT_DIM)
            elements.append(
                Paragraph(
                    f"<b>{t[label_key]}</b> "
                    f'({t["confidence"]}: <font color="{conf_color.hexval()}">'
                    f"{proj.confidence}</font>)",
                    s["heading2"],
                )
            )
            elements.append(Paragraph(proj.projection, s["body"]))
            if proj.key_milestones:
                elements.append(
                    Paragraph(f"<b>{t['milestones']}:</b>", s["body"])
                )
                for ms in proj.key_milestones:
                    elements.append(Paragraph(f"• {ms}", s["body"]))
            elements.append(Spacer(1, 4 * mm))

        return elements

    def _build_strategic_advice_page(self, cr) -> list:
        """Strategic advice with prioritized actions."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["strategic_advice"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        sa = cr.strategic_advice

        for section_key, actions in [
            ("immediate_actions", sa.immediate_actions),
            ("medium_term", sa.medium_term),
        ]:
            if not actions:
                continue
            elements.append(Paragraph(t[section_key], s["heading2"]))
            elements.append(Spacer(1, 3 * mm))

            cell_style = ParagraphStyle(
                "CellStyle", fontName=s["body"].fontName, fontSize=8,
                textColor=COLOR_TEXT, leading=11,
            )
            cell_style_h = ParagraphStyle(
                "CellStyleH", fontName=s["heading1"].fontName, fontSize=8,
                textColor=COLOR_WHITE, leading=11,
            )
            header = [
                Paragraph(t["action"], cell_style_h),
                Paragraph(t["rationale"], cell_style_h),
                Paragraph(t["impact"], cell_style_h),
            ]
            rows = [header]
            for act in actions:
                rows.append([
                    Paragraph(act.action, cell_style),
                    Paragraph(act.rationale, cell_style),
                    Paragraph(act.expected_impact, cell_style),
                ])

            col_w = 150
            table = Table(rows, colWidths=[col_w, col_w, col_w])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_SURFACE),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_LIGHT_BG, COLOR_WHITE]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 6 * mm))

        if sa.long_term_vision:
            elements.append(Paragraph(t["long_term_vision"], s["heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(sa.long_term_vision, s["body"]))

        return elements

    def _build_investment_thesis_page(self, cr) -> list:
        """Investment thesis with recommendation badge."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["investment_thesis"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        thesis = cr.investment_thesis

        # Recommendation badge
        rec_labels = {
            "strong_invest": (t.get("invest_strong", "Strong Invest"), COLOR_GREEN),
            "invest_with_conditions": (t.get("invest_conditions", "Invest with Conditions"), colors.HexColor("#84cc16")),
            "cautious": (t.get("invest_cautious", "Cautious"), COLOR_YELLOW),
            "pass": (t.get("invest_pass", "Pass"), COLOR_ORANGE),
            "strong_pass": (t.get("invest_strong_pass", "Strong Pass"), COLOR_RED),
        }
        rec_label, rec_color = rec_labels.get(
            thesis.recommendation,
            (thesis.recommendation, COLOR_TEXT_DIM),
        )
        elements.append(
            Paragraph(
                f'{t["recommendation"]}: '
                f'<font color="{rec_color.hexval()}" size="14"><b>{rec_label}</b></font>',
                s["body"],
            )
        )
        elements.append(Spacer(1, 4 * mm))

        # Rationale
        if thesis.rationale:
            elements.append(Paragraph(thesis.rationale, s["body"]))
            elements.append(Spacer(1, 6 * mm))

        # Two-column: Risks vs Upside
        risk_items = "".join(f"• {r}<br/>" for r in thesis.key_risks) if thesis.key_risks else "—"
        upside_items = "".join(f"• {u}<br/>" for u in thesis.key_upside) if thesis.key_upside else "—"

        risk_upside = Table(
            [
                [
                    Paragraph(f"<b>{t['key_risks']}</b><br/>{risk_items}", s["body"]),
                    Paragraph(f"<b>{t['key_upside']}</b><br/>{upside_items}", s["body"]),
                ]
            ],
            colWidths=[225, 225],
        )
        risk_upside.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(risk_upside)
        elements.append(Spacer(1, 4 * mm))

        # Comparable companies
        if thesis.comparable_companies:
            elements.append(
                Paragraph(
                    f"<b>{t['comparable_companies']}:</b> "
                    + ", ".join(thesis.comparable_companies),
                    s["body"],
                )
            )
            elements.append(Spacer(1, 3 * mm))

        # Valuation factors
        if thesis.suggested_valuation_factors:
            elements.append(
                Paragraph(
                    f"<b>{t['valuation_factors']}:</b> "
                    + thesis.suggested_valuation_factors,
                    s["body"],
                )
            )

        return elements

    def _build_consulting_red_flags(self, cr) -> list:
        """Red flags from consulting report."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["red_flags"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        severity_colors = {
            "critical": COLOR_RED,
            "high": COLOR_ORANGE,
            "medium": COLOR_YELLOW,
            "low": COLOR_GREEN,
        }

        for flag in cr.red_flags:
            if not isinstance(flag, dict):
                continue
            sev = str(flag.get("severity", "info")).lower()
            sev_color = severity_colors.get(sev, COLOR_ACCENT)
            title = flag.get("title", "")
            desc = flag.get("description", "")
            impact = flag.get("business_impact", "")

            elements.append(
                Paragraph(
                    f'<font color="{sev_color.hexval()}"><b>[{sev.upper()}]</b></font> '
                    f"<b>{title}</b>",
                    s["body"],
                )
            )
            if desc:
                elements.append(Paragraph(desc, s["body"]))
            if impact:
                elements.append(
                    Paragraph(f"<i>{impact}</i>", s["body_dim"])
                )
            elements.append(Spacer(1, 3 * mm))

        return elements

    def _build_glossary_page(self, cr) -> list:
        """Glossary page combining base glossary and AI additions."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["glossary"], s["heading1"]))
        elements.append(Spacer(1, 6 * mm))

        # AI-generated glossary additions
        glossary = cr.glossary_additions or []
        if not glossary:
            elements.append(Paragraph("—", s["body_dim"]))
            return elements

        cell_style = ParagraphStyle(
            "GlossCell", fontName=s["body"].fontName, fontSize=8,
            textColor=COLOR_TEXT, leading=11,
        )
        cell_style_h = ParagraphStyle(
            "GlossCellH", fontName=s["heading1"].fontName, fontSize=8,
            textColor=COLOR_WHITE, leading=11,
        )
        cell_style_bold = ParagraphStyle(
            "GlossCellB", fontName=s["heading1"].fontName, fontSize=8,
            textColor=COLOR_TEXT, leading=11,
        )
        header = [Paragraph(t["term"], cell_style_h), Paragraph(t["definition"], cell_style_h)]
        rows = [header]
        for entry in glossary:
            if isinstance(entry, dict):
                rows.append([
                    Paragraph(entry.get("term", ""), cell_style_bold),
                    Paragraph(entry.get("definition", ""), cell_style),
                ])

        if len(rows) > 1:
            table = Table(rows, colWidths=[120, 330])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_SURFACE),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_LIGHT_BG, COLOR_WHITE]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(table)

        return elements

    # ------------------------------------------------------------------
    # Site Verification page
    # ------------------------------------------------------------------

    def _build_site_verification_page(self, cr) -> list:
        """Site verification page with horizontal bar chart for 10 items."""
        t = self._t
        s = self._styles
        elements: list = []

        sv = cr.site_verification
        if not sv or not sv.items:
            return elements

        # Title + subtitle
        elements.append(Paragraph(t["site_verification"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )
        elements.append(Paragraph(t["site_verification_subtitle"], s["body_dim"]))
        elements.append(Spacer(1, 4 * mm))

        # URLs analyzed
        if sv.urls_analyzed:
            elements.append(
                Paragraph(f"<b>{t['sv_urls_analyzed']}:</b>", s["body"])
            )
            for url in sv.urls_analyzed:
                elements.append(Paragraph(f"  {url}", s["body_small"]))
            elements.append(Spacer(1, 4 * mm))

        # Overall credibility score — Arc brand coloring
        cred_score = sv.overall_credibility
        if cred_score >= 75:
            cred_color = COLOR_ACCENT                # Arc sky
        elif cred_score >= 50:
            cred_color = COLOR_ACCENT_DARK           # Arc sky darker
        elif cred_score >= 30:
            cred_color = colors.HexColor("#000000")  # black
        else:
            cred_color = colors.HexColor("#6b2a2a")  # muted red

        cred_text = (
            f'<font color="{cred_color.hexval()}" size="36">{cred_score:.0f}</font>'
            f'<font color="{COLOR_TEXT_DIM.hexval()}" size="14"> / 100</font>'
        )
        elements.append(Paragraph(cred_text, s["score_large"]))
        elements.append(
            Paragraph(t["overall_credibility"], s["center"])
        )
        elements.append(Spacer(1, 8 * mm))

        # --- Horizontal bar chart for verification items ---
        confidence_badge = {
            "high": t.get("confidence_high", "H"),
            "medium": t.get("confidence_medium", "M"),
            "low": t.get("confidence_low", "L"),
        }

        bar_max_w = 240
        row_h = 44
        label_w = 160
        chart_w = label_w + bar_max_w + 80
        chart_h = len(sv.items) * row_h + 10

        d = Drawing(chart_w, chart_h)

        for i, item in enumerate(sv.items):
            y = chart_h - (i + 1) * row_h + 14

            # Item name (bold)
            item_name = item.item_name_ja if self._lang == "ja" and item.item_name_ja else item.item_name
            font_bold = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            d.add(String(0, y + 4, item_name, fontName=font_bold, fontSize=8.5,
                         fillColor=COLOR_TEXT))

            # Confidence label (small gray below name)
            conf_label = confidence_badge.get(item.confidence, "M")
            conf_font = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
            conf_text = f"Confidence: {conf_label}"
            d.add(String(0, y - 8, conf_text, fontName=conf_font, fontSize=6.5,
                         fillColor=COLOR_TEXT_DIM))

            # Gray track bar
            d.add(Rect(label_w, y, bar_max_w, 16,
                        fillColor=colors.HexColor("#e2e8f0"),
                        strokeColor=None, strokeWidth=0))

            # Score bar (Arc brand: black + sky blue)
            score = item.score
            bar_w = max(2, (score / 100) * bar_max_w)
            if score >= 75:
                bar_color = COLOR_ACCENT                  # Arc sky
            elif score >= 50:
                bar_color = COLOR_ACCENT_DARK             # Arc sky darker
            elif score >= 30:
                bar_color = colors.HexColor("#000000")    # black
            else:
                bar_color = colors.HexColor("#6b2a2a")    # muted red
            d.add(Rect(label_w, y, bar_w, 16,
                        fillColor=bar_color,
                        strokeColor=None, strokeWidth=0))

            # Score number (right of bar)
            score_str = f"{score:.0f}"
            d.add(String(label_w + bar_max_w + 6, y + 3, score_str,
                         fontName="Helvetica", fontSize=9,
                         fillColor=COLOR_TEXT_DIM))

        elements.append(d)
        elements.append(Spacer(1, 8 * mm))

        # Summary text
        if sv.summary:
            elements.append(Paragraph(f"<b>{t['sv_summary']}</b>", s["body"]))
            elements.append(Paragraph(sv.summary, s["body"]))

        return elements

    # ------------------------------------------------------------------
    # Competitive Analysis — Forrester Wave-style 2×3 grid
    # ------------------------------------------------------------------

    _MARKET_ORDER_JA = {
        "Global": "グローバル", "US": "米国", "EMEA": "EMEA",
        "LATAM": "中南米", "Japan": "日本", "SEA": "東南アジア",
    }

    # Cell size for mini charts (fits 2 per row within A4 margins)
    _CELL_W = 235
    _CELL_H = 180

    def _mini_chart(self, chart, ctype: str, quadrant_labels: list[str] | None = None) -> Drawing:
        """Render a single Forrester-style mini chart as a standalone Drawing."""
        w, h = self._CELL_W, self._CELL_H
        d = Drawing(w, h)

        # Paddings: left for Y-axis label, bottom for X-axis label, top/right margins
        pl, pb, pr, pt = 32, 22, 8, 8
        pw = w - pl - pr  # plot width
        ph = h - pb - pt  # plot height

        # --- Background & border ---
        d.add(Rect(0, 0, w, h,
                   fillColor=colors.HexColor("#f8f9fa"),
                   strokeColor=COLOR_BORDER, strokeWidth=0.4))

        # --- Grid lines (Forrester style: light horizontal/vertical bands) ---
        for frac in (0.25, 0.5, 0.75):
            gx = pl + pw * frac
            gy = pb + ph * frac
            d.add(Line(gx, pb, gx, pb + ph,
                       strokeColor=colors.HexColor("#e5e7eb"), strokeWidth=0.3))
            d.add(Line(pl, gy, pl + pw, gy,
                       strokeColor=colors.HexColor("#e5e7eb"), strokeWidth=0.3))

        # --- Axes (solid) ---
        d.add(Line(pl, pb, pl + pw, pb,
                   strokeColor=COLOR_TEXT_DIM, strokeWidth=0.6))
        d.add(Line(pl, pb, pl, pb + ph,
                   strokeColor=COLOR_TEXT_DIM, strokeWidth=0.6))

        # --- Axis scale ticks: 0, 25, 50, 75, 100 ---
        af = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
        for val in (0, 50, 100):
            # X ticks
            tx = pl + pw * (val / 100)
            d.add(Line(tx, pb, tx, pb - 3,
                       strokeColor=COLOR_TEXT_DIM, strokeWidth=0.3))
            d.add(String(tx - 4, pb - 11, str(val),
                         fontName=af, fontSize=5, fillColor=COLOR_TEXT_DIM))
            # Y ticks
            ty = pb + ph * (val / 100)
            d.add(Line(pl, ty, pl - 3, ty,
                       strokeColor=COLOR_TEXT_DIM, strokeWidth=0.3))
            d.add(String(pl - 14, ty - 2, str(val),
                         fontName=af, fontSize=5, fillColor=COLOR_TEXT_DIM))

        # --- Quadrant labels (for quadrant-type charts) ---
        if quadrant_labels and len(quadrant_labels) == 4:
            lf = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            lc = colors.HexColor("#c0c4cc")
            ls = 5.5
            mx = pl + pw / 2
            my = pb + ph / 2
            # [top-left, top-right, bottom-left, bottom-right]
            d.add(String(pl + 3, pb + ph - 10, quadrant_labels[0],
                         fontName=lf, fontSize=ls, fillColor=lc))
            d.add(String(mx + 3, pb + ph - 10, quadrant_labels[1],
                         fontName=lf, fontSize=ls, fillColor=lc))
            d.add(String(pl + 3, pb + 3, quadrant_labels[2],
                         fontName=lf, fontSize=ls, fillColor=lc))
            d.add(String(mx + 3, pb + 3, quadrant_labels[3],
                         fontName=lf, fontSize=ls, fillColor=lc))
            # Center cross (dashed)
            d.add(Line(mx, pb, mx, pb + ph,
                       strokeColor=colors.HexColor("#d1d5db"), strokeWidth=0.4,
                       strokeDashArray=[3, 3]))
            d.add(Line(pl, my, pl + pw, my,
                       strokeColor=colors.HexColor("#d1d5db"), strokeWidth=0.4,
                       strokeDashArray=[3, 3]))

        # --- Risk-return special: sweet spot zone + efficient frontier ---
        if ctype == "gs_risk_return":
            # Sweet spot = low risk, high return (left-top)
            sx, sy = pl + pw * 0.02, pb + ph * 0.58
            sw, sh = pw * 0.38, ph * 0.38
            d.add(Rect(sx, sy, sw, sh,
                       fillColor=colors.HexColor("#e8f4f8"),
                       strokeColor=colors.HexColor("#b8d8e8"), strokeWidth=0.3))
            lf = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            d.add(String(sx + 2, sy + sh - 9,
                         self._t.get("sweet_spot", "Sweet Spot"),
                         fontName=lf, fontSize=5, fillColor=COLOR_ACCENT))
            # Efficient frontier diagonal
            d.add(Line(pl + pw * 0.05, pb + ph * 0.1,
                       pl + pw * 0.95, pb + ph * 0.9,
                       strokeColor=COLOR_ACCENT, strokeWidth=0.7,
                       strokeDashArray=[4, 2]))

        # --- Axis labels ---
        x_lab = chart.x_axis_label_ja if self._lang == "ja" and chart.x_axis_label_ja else chart.x_axis_label
        y_lab = chart.y_axis_label_ja if self._lang == "ja" and chart.y_axis_label_ja else chart.y_axis_label
        # Truncate
        x_lab = (x_lab[:22] + "…") if len(x_lab) > 24 else x_lab
        y_lab = (y_lab[:14] + "…") if len(y_lab) > 16 else y_lab
        d.add(String(pl + pw / 2 - len(x_lab) * 1.5, 2, x_lab,
                     fontName=af, fontSize=5.5, fillColor=COLOR_TEXT_DIM))
        # Y-axis label (rotated text not supported in ReportLab String,
        # so place vertically at left edge)
        d.add(String(1, pb + ph / 2 - len(y_lab) * 1.2, y_lab,
                     fontName=af, fontSize=5, fillColor=COLOR_TEXT_DIM))

        # --- Data points ---
        is_bubble = (ctype == "bubble_3d")
        nf = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
        # Sort: non-target first, target on top
        sorted_pts = sorted(chart.data_points, key=lambda dp: dp.is_target)
        label_positions: list[tuple[float, float]] = []

        for dp in sorted_pts:
            cx = pl + (dp.x / 100) * pw
            cy = pb + (dp.y / 100) * ph

            if is_bubble:
                r = max(4, min(18, dp.z * 0.18))
                fill = COLOR_ACCENT if dp.is_target else colors.HexColor("#d1d5db")
                alpha = 0.85
            else:
                r = 5.5 if dp.is_target else 4
                fill = COLOR_ACCENT if dp.is_target else colors.HexColor("#9ca3af")
                alpha = 1.0

            stroke_c = colors.white if dp.is_target else colors.HexColor("#ffffff")
            stroke_w = 1.0 if dp.is_target else 0.3
            d.add(Circle(cx, cy, r, fillColor=fill,
                         strokeColor=stroke_c, strokeWidth=stroke_w))

            # Smart label placement to avoid overlaps
            name = dp.name[:12]
            lx = cx + r + 2
            ly = cy - 2
            # If off right edge, place left
            if lx + len(name) * 3 > w - 2:
                lx = cx - r - len(name) * 3 - 1
            # If off top, shift down
            if ly + 6 > h - 2:
                ly = cy - 8
            # Check overlap with previous labels (simple)
            for plx, ply in label_positions:
                if abs(lx - plx) < 25 and abs(ly - ply) < 7:
                    ly -= 7
                    break
            label_positions.append((lx, ly))

            fs = 5.5 if dp.is_target else 5
            fc = COLOR_TEXT if dp.is_target else COLOR_TEXT_DIM
            d.add(String(lx, ly, name,
                         fontName=nf, fontSize=fs, fillColor=fc))

        return d

    # ────────────────────────────────────────────────────────
    # Task C: Atlas Optimization Assessment (4-axis parallel evaluation)
    # ────────────────────────────────────────────────────────

    def _build_atlas_four_axis_page(self, cr) -> list:
        """Atlas 4-axis dashboard — same visual language as 6-dim score dashboard.

        Inviolable rules respected:
        - Horizontal progress bars (filled vs empty contrast)
        - Left label → bar → right monospaced score value
        - Arc sky (#5271FF) + black brand colors
        - F→A barometer at the bottom
        """
        t = self._t
        s = self._styles
        elements: list = []

        afa = cr.atlas_four_axis
        if afa is None or not afa.axes:
            return elements

        # Title
        elements.append(Paragraph(t["atlas_four_axis"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )
        elements.append(Paragraph(t["atlas_subtitle"], s["body_dim"]))
        elements.append(Spacer(1, 6 * mm))

        # Industry context badge
        if afa.industry_context:
            ind_text = (
                f'<font color="{COLOR_TEXT_DIM.hexval()}" size="9">'
                f'{t["atlas_industry_context"]}: <b>{afa.industry_context}</b></font>'
            )
            elements.append(Paragraph(ind_text, s["center"]))
            elements.append(Spacer(1, 3 * mm))

        # Atlas composite score (large display, accent color)
        atlas_label = f'{t["atlas_overall"]}'
        elements.append(
            Paragraph(
                f'<font color="{COLOR_ACCENT.hexval()}" size="13"><b>{atlas_label}</b></font>',
                s["center"],
            )
        )
        elements.append(Spacer(1, 2 * mm))

        score_large_style = ParagraphStyle(
            "AtlasScoreLarge", fontName="Helvetica-Bold", fontSize=48,
            leading=56, alignment=1, textColor=COLOR_ACCENT,
        )
        overall_text = (
            f'{afa.overall_score:.0f}'
            f'<font color="{COLOR_TEXT_DIM.hexval()}" size="18"> / 100</font>'
        )
        elements.append(Paragraph(overall_text, score_large_style))
        elements.append(Spacer(1, 8 * mm))

        # 4-axis horizontal bar chart (same pattern as score dashboard)
        # Order: performance(25), stability(20), lightweight(5), security(50)
        axes_ordered = sorted(
            afa.axes,
            key=lambda a: {"performance": 0, "stability": 1, "lightweight": 2, "security": 3}.get(a.axis_key, 99),
        )

        bar_max_w = 280
        row_h = 44
        label_w = 140
        chart_w = label_w + bar_max_w + 80
        chart_h = len(axes_ordered) * row_h + 10

        d = Drawing(chart_w, chart_h)

        for i, axis in enumerate(axes_ordered):
            y = chart_h - (i + 1) * row_h + 14
            name = axis.name_ja if self._lang == "ja" and axis.name_ja else axis.name_en

            # Axis label (left, bold)
            font_name = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            d.add(String(0, y + 4, name, fontName=font_name, fontSize=9, fillColor=COLOR_TEXT))

            # Rationale (below label, small dim text)
            desc_font = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
            rationale_short = (axis.rationale or "")[:64]
            if len(axis.rationale or "") > 64:
                rationale_short += "…"
            d.add(String(0, y - 8, rationale_short, fontName=desc_font, fontSize=6.5,
                         fillColor=COLOR_TEXT_DIM))

            # Background bar (gray track)
            d.add(Rect(label_w, y, bar_max_w, 16,
                       fillColor=colors.HexColor("#e2e8f0"),
                       strokeColor=None, strokeWidth=0))

            # Score bar (Arc brand colors)
            bar_w = max(2, (axis.score / 100) * bar_max_w)
            if axis.score >= 75:
                bar_color = COLOR_ACCENT
            elif axis.score >= 50:
                bar_color = COLOR_ACCENT_DARK
            elif axis.score >= 30:
                bar_color = colors.HexColor("#000000")
            else:
                bar_color = colors.HexColor("#6b2a2a")
            d.add(Rect(label_w, y, bar_w, 16,
                       fillColor=bar_color, strokeColor=None, strokeWidth=0))

            # Score text (right of bar) — monospaced format
            score_str = f"{axis.score:.0f}  Lv.{axis.level}  ({axis.weight_pct:.0f}%)"
            d.add(String(label_w + bar_max_w + 6, y + 3, score_str,
                         fontName="Helvetica", fontSize=8, fillColor=COLOR_TEXT_DIM))

        elements.append(d)
        elements.append(Spacer(1, 8 * mm))

        # Summary text
        summary = afa.summary_ja if self._lang == "ja" and afa.summary_ja else afa.summary
        if summary:
            elements.append(Paragraph(summary, s["body"]))

        return elements

    def _build_atlas_security_breakdown_page(self, cr, security_axis) -> list:
        """Security Strength sub-breakdown — emphasizes encryption (30%) as core."""
        t = self._t
        s = self._styles
        elements: list = []

        elements.append(Paragraph(t["security_breakdown"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm)
        )
        elements.append(Paragraph(t["security_breakdown_subtitle"], s["body_dim"]))
        elements.append(Spacer(1, 6 * mm))

        # Sub-items in fixed order: encryption (largest) → privacy → comms → layers → posture (smallest)
        order = {"encryption": 0, "privacy": 1, "comms": 2, "layers": 3, "posture": 4}
        sub_items = sorted(security_axis.sub_items, key=lambda si: order.get(si.key, 99))

        bar_max_w = 280
        row_h = 44
        label_w = 160
        chart_w = label_w + bar_max_w + 80
        chart_h = len(sub_items) * row_h + 10

        d = Drawing(chart_w, chart_h)

        # Map sub-item keys to short i18n labels (fallback to provided name)
        subitem_labels = {
            "encryption": t.get("subitem_encryption", "Encryption"),
            "privacy": t.get("subitem_privacy", "Privacy"),
            "posture": t.get("subitem_posture", "Posture"),
            "comms": t.get("subitem_comms", "Comms"),
            "layers": t.get("subitem_layers", "Layers"),
        }

        for i, si in enumerate(sub_items):
            y = chart_h - (i + 1) * row_h + 14
            name = subitem_labels.get(si.key, si.name_ja if self._lang == "ja" else si.name_en)

            # Label
            font_name = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
            d.add(String(0, y + 4, name, fontName=font_name, fontSize=9, fillColor=COLOR_TEXT))

            # Rationale
            desc_font = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
            rationale_short = (si.rationale or "")[:60]
            if len(si.rationale or "") > 60:
                rationale_short += "…"
            d.add(String(0, y - 8, rationale_short, fontName=desc_font, fontSize=6.5,
                         fillColor=COLOR_TEXT_DIM))

            # Background bar
            d.add(Rect(label_w, y, bar_max_w, 16,
                       fillColor=colors.HexColor("#e2e8f0"),
                       strokeColor=None, strokeWidth=0))

            # Score bar
            bar_w = max(2, (si.score / 100) * bar_max_w)
            if si.score >= 75:
                bar_color = COLOR_ACCENT
            elif si.score >= 50:
                bar_color = COLOR_ACCENT_DARK
            elif si.score >= 30:
                bar_color = colors.HexColor("#000000")
            else:
                bar_color = colors.HexColor("#6b2a2a")
            d.add(Rect(label_w, y, bar_w, 16,
                       fillColor=bar_color, strokeColor=None, strokeWidth=0))

            # Score text — show weight prominently for emphasis
            score_str = f"{si.score:.0f}  Lv.{si.level}  ({si.weight_pct:.0f}%)"
            d.add(String(label_w + bar_max_w + 6, y + 3, score_str,
                         fontName="Helvetica", fontSize=8, fillColor=COLOR_TEXT_DIM))

        elements.append(d)
        elements.append(Spacer(1, 8 * mm))

        # Weight philosophy callout
        if self._lang == "ja":
            philosophy = (
                "<b>重み哲学:</b> 暗号化技術の高度さ（30%）が核心。"
                "MFA・SOC2 等の「誰でもできる」項目は最小重み（2%）に抑制。"
            )
        else:
            philosophy = (
                "<b>Weight Philosophy:</b> Cryptographic sophistication (30%) is the core. "
                "Checkbox compliance (MFA/SOC2 — \"anyone can do\") is minimum-weighted (2%)."
            )
        elements.append(Paragraph(philosophy, s["body"]))
        elements.append(Spacer(1, 4 * mm))

        # Plain-language glossary for non-engineers reading the report
        elements.append(
            Paragraph(
                "<b>" + ("用語ミニ解説（非エンジニア向け）" if self._lang == "ja"
                         else "Glossary for non-engineer readers") + "</b>",
                s["heading3"],
            )
        )
        if self._lang == "ja":
            gloss_items = [
                ("暗号化技術", "通信や保存データを、本人以外には読めない状態に変換する技術。"
                              "Signal Protocol / PQXDH などが最先端。"),
                ("E2E暗号化", "送信者と受信者だけが読める暗号化。サービス運営者でも中身は見られない。"),
                ("MFA (多要素認証)", "パスワードに加え、SMS コードや認証アプリで本人確認する仕組み。"
                                      "今や標準。導入していないと論外。"),
                ("SOC2", "米国 AICPA が定めたセキュリティ監査基準。取得企業は多数あり、"
                         "差別化要因ではなく衛生項目。"),
                ("libsignal", "Signal Foundation が公開している、Signal Protocol の公式実装ライブラリ。"
                              "使うと暗号の自前実装ミスを避けられる。"),
                ("PQXDH / ML-KEM", "量子コンピュータでも破れない次世代暗号（ポスト量子暗号）。"
                                    "Apple の iMessage (PQ3) や Signal が採用済み。"),
            ]
        else:
            gloss_items = [
                ("Cryptography", "The art of making data unreadable to anyone but the intended recipient. "
                                 "Signal Protocol / PQXDH are state-of-the-art."),
                ("E2E Encryption", "End-to-end: only sender & recipient can decrypt. Even the service provider cannot read it."),
                ("MFA (Multi-Factor Auth)", "Password + second factor (SMS code / authenticator app). "
                                             "Standard hygiene — missing it is a red flag, having it is not a differentiator."),
                ("SOC2", "US AICPA security audit standard. Widely held; a hygiene item, not a differentiator."),
                ("libsignal", "Official Signal Protocol implementation by Signal Foundation. "
                              "Using it avoids self-rolled crypto mistakes."),
                ("PQXDH / ML-KEM", "Post-quantum cryptography — safe even against future quantum computers. "
                                    "Adopted by Apple iMessage (PQ3) and Signal."),
            ]
        for term, definition in gloss_items:
            elements.append(
                Paragraph(
                    f'<b>{term}</b> — <font color="{COLOR_TEXT_DIM.hexval()}">{definition}</font>',
                    s["body_small"],
                )
            )

        return elements

    # ────────────────────────────────────────────────────────
    # v0.3.1: Competitor Selection Rationales
    # For each competitor, 3-5 line explanation of why they were chosen.
    # Placed AFTER competitive analysis charts, BEFORE the matrix —
    # so readers understand who is being compared and why.
    # ────────────────────────────────────────────────────────

    def _build_competitor_rationales_page(self, cr) -> list:
        """Competitor selection rationales (3-5 lines per competitor) + estimated score."""
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        t = self._t
        s = self._styles
        elements: list = []

        rationales = cr.competitor_rationales or []
        if not rationales:
            return elements

        elements.append(Paragraph(t["competitor_rationales"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=3 * mm)
        )
        elements.append(Paragraph(t["competitor_rationales_subtitle"], s["body_dim"]))
        elements.append(Spacer(1, 3 * mm))

        # Important disclaimer about estimated scores
        if self._lang == "ja":
            disclaimer = (
                "<b>⚠ 推定スコアについて</b><br/>"
                "各社の推定スコア（0-100 点）は <b>公開情報のみに基づく AI の推定値</b> です。"
                "公開情報（マーケページ・ホワイトペーパー・プレスリリース等）は概して好意的に"
                "書かれているため、<b>ソースコードレベルで DD した場合の実スコアはこれ以下になる"
                "可能性が高い</b>ことに留意してください。参考値としてご活用ください。"
            )
        else:
            disclaimer = (
                "<b>⚠ About Estimated Scores</b><br/>"
                "Each competitor's estimated score (0-100) is an <b>AI estimate based ONLY "
                "on publicly available information</b>. Public materials (marketing pages, "
                "whitepapers, press releases) skew positive — so the <b>actual score under "
                "source-code-level DD is likely LOWER</b> than shown. Use as a reference only."
            )
        # Rendered in a light blue callout box
        callout = RLTable(
            [[Paragraph(disclaimer, s["body_small"])]],
            colWidths=[160 * mm],
        )
        callout.setStyle(RLTableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_ACCENT_LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEABOVE", (0, 0), (-1, 0), 2, COLOR_ACCENT),
        ]))
        elements.append(callout)
        elements.append(Spacer(1, 5 * mm))

        for r in rationales:
            # Wrap each competitor block in KeepTogether to prevent orphans —
            # a header on one page with its body bleeding to the next looks broken.
            block: list = []

            # Header row: company name + category + estimated score
            header_bits: list[str] = [f'<b>{r.name}</b>']
            if r.category:
                header_bits.append(
                    f'<font color="{COLOR_ACCENT.hexval()}" size="9">[{r.category}]</font>'
                )
            # Estimated score — always shown (even if 0), clearly labeled as estimate
            score_label = "推定" if self._lang == "ja" else "est."
            header_bits.append(
                f'<font color="{COLOR_TEXT_DIM.hexval()}" size="10">'
                f'{score_label}: <b>{r.estimated_score:.0f}</b>/100</font>'
            )
            block.append(Paragraph("  ".join(header_bits), s["heading3"]))

            # Meta line: HQ + market position
            meta_parts: list[str] = []
            if r.hq_country:
                meta_parts.append(f'{t["rationale_hq"]}: {r.hq_country}')
            if r.market_position:
                meta_parts.append(f'{t["rationale_position"]}: {r.market_position}')
            if meta_parts:
                block.append(Paragraph(" · ".join(meta_parts), s["body_dim"]))

            # Rationale (3-5 line prose, language-appropriate)
            rationale_text = (r.rationale_ja if self._lang == "ja" and r.rationale_ja
                              else r.rationale_en)
            if rationale_text:
                block.append(Paragraph(rationale_text, s["body"]))

            block.append(Spacer(1, 4 * mm))
            elements.append(KeepTogether(block))

        return elements

    # ────────────────────────────────────────────────────────
    # Task D: Implementation Capability Matrix (8th competitive chart)
    # ────────────────────────────────────────────────────────

    def _build_implementation_matrix_page(self, cr) -> list:
        """Implementation matrix — A4 portrait Table, ~30 items × 5-10 competitors.

        Uses ASCII status symbols (✓ △ ✗ ?) per inviolable rule (no emoji icons).
        Target company column highlighted with Arc sky (#5271FF) background.
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        t = self._t
        s = self._styles
        elements: list = []

        im = cr.implementation_matrix
        if im is None or not im.items:
            return elements

        elements.append(PageBreak())
        elements.append(Paragraph(t["impl_matrix"], s["heading1"]))
        elements.append(
            HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=2 * mm)
        )
        elements.append(Paragraph(t["impl_matrix_subtitle"], s["body_dim"]))
        elements.append(Spacer(1, 2 * mm))

        # Legend — use ○△× (Japanese tech rating standard, universally rendered by CID fonts).
        # ✓✗ are NOT in HeiseiKakuGo-W5, so we use ○△× (U+25EF/U+25B3/U+00D7) instead.
        legend_text_font = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
        legend_symbol_font = "HeiseiKakuGo-W5"  # has ○△× in both languages
        legend_text = (
            f'<font name="{legend_symbol_font}" size="10" color="{COLOR_ACCENT.hexval()}">○</font> '
            f'<font name="{legend_text_font}" size="8">{t["impl_legend_verified"]}</font>'
            f'   '
            f'<font name="{legend_symbol_font}" size="10" color="{COLOR_TEXT.hexval()}">△</font> '
            f'<font name="{legend_text_font}" size="8">{t["impl_legend_claimed"]}</font>'
            f'   '
            f'<font name="{legend_symbol_font}" size="10" color="#6b2a2a">×</font> '
            f'<font name="{legend_text_font}" size="8">{t["impl_legend_not_impl"]}</font>'
            f'   '
            f'<font name="{legend_symbol_font}" size="10" color="{COLOR_TEXT_DIM.hexval()}">?</font> '
            f'<font name="{legend_text_font}" size="8">{t["impl_legend_unknown"]}</font>'
        )
        elements.append(Paragraph(legend_text, s["center"]))
        elements.append(Spacer(1, 3 * mm))

        # Build column structure: [Item, Target, Comp1, Comp2, ...]
        # Limit to 10 competitors (= 11 columns total) to fit A4 portrait
        all_companies = [im.target_company] + im.competitors[:10]

        # Header row
        font_header = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
        header_para_style = ParagraphStyle(
            "MatHeader", fontName=font_header, fontSize=7,
            textColor=COLOR_WHITE, alignment=1, leading=9,
        )
        target_header_style = ParagraphStyle(
            "MatTargetHeader", fontName=font_header, fontSize=7,
            textColor=COLOR_WHITE, alignment=1, leading=9,
        )

        header_row = [Paragraph("", header_para_style)]
        for c in all_companies:
            # Truncate long names
            short_name = c[:14] + "…" if len(c) > 14 else c
            header_row.append(Paragraph(short_name, header_para_style))

        # Group items by category
        category_order = [
            "performance", "stability", "lightweight", "encryption",
            "privacy", "posture", "comms", "layers",
        ]
        cat_label_map = {
            "performance": t.get("matcat_performance", "Performance"),
            "stability": t.get("matcat_stability", "Stability"),
            "lightweight": t.get("matcat_lightweight", "Lightweight"),
            "encryption": t.get("matcat_encryption", "Encryption"),
            "privacy": t.get("matcat_privacy", "Privacy"),
            "posture": t.get("matcat_posture", "Posture"),
            "comms": t.get("matcat_comms", "Comms"),
            "layers": t.get("matcat_layers", "Layers"),
        }

        items_by_cat: dict[str, list] = {}
        for item in im.items:
            items_by_cat.setdefault(item.category, []).append(item)

        # Build table rows: header + (category-row + items)*N
        font_body = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
        item_para_style = ParagraphStyle(
            "MatItem", fontName=font_body, fontSize=7,
            textColor=COLOR_TEXT, alignment=0, leading=9,
        )
        cat_para_style = ParagraphStyle(
            "MatCat", fontName=font_header, fontSize=8,
            textColor=COLOR_ACCENT, alignment=0, leading=10,
        )
        # Cell symbols (✓ △ ✗ ?) need a font that has all 4.
        # CID HeiseiKakuGo-W5 supports all of them; Helvetica-Bold doesn't have △.
        cell_symbol_font = "HeiseiKakuGo-W5" if self._lang == "ja" else "HeiseiKakuGo-W5"
        cell_style = ParagraphStyle(
            "MatCell", fontName=cell_symbol_font, fontSize=10,
            textColor=COLOR_TEXT, alignment=1, leading=11,
        )

        table_data = [header_row]
        # Track which row indices are category rows (for styling)
        cat_row_indices = []
        # Build a map: company_name → position (column 1+)
        company_col = {name: idx + 1 for idx, name in enumerate(all_companies)}

        # Status → symbol + color (Japanese tech rating: ○△× — universally rendered)
        status_glyph = {
            "verified": ("○", COLOR_ACCENT),                           # 実装確認済
            "claimed": ("△", COLOR_TEXT),                              # 主張あり
            "not_implemented": ("×", colors.HexColor("#6b2a2a")),      # 未実装
            "unknown": ("?", COLOR_TEXT_DIM),                          # 不明
        }

        for cat in category_order:
            cat_items = items_by_cat.get(cat, [])
            if not cat_items:
                continue

            # Category header row (full-width via merged-style: just put label in col 0)
            cat_label = cat_label_map.get(cat, cat)
            cat_row_index = len(table_data)
            cat_row = [Paragraph(f"<b>{cat_label}</b>", cat_para_style)] + [""] * len(all_companies)
            table_data.append(cat_row)
            cat_row_indices.append(cat_row_index)

            # Item rows
            for item in cat_items:
                item_label = item.item_ja if self._lang == "ja" and item.item_ja else item.item_en
                row = [Paragraph(item_label, item_para_style)]
                # Build status lookup for this item
                status_by_company: dict[str, str] = {}
                for st in item.statuses:
                    status_by_company[st.company_name] = st.status.value if hasattr(st.status, "value") else str(st.status)

                for company in all_companies:
                    raw_status = status_by_company.get(company, "unknown")
                    glyph, glyph_color = status_glyph.get(raw_status, ("?", COLOR_TEXT_DIM))
                    cell_para = Paragraph(
                        f'<font color="{glyph_color.hexval()}"><b>{glyph}</b></font>',
                        cell_style,
                    )
                    row.append(cell_para)
                table_data.append(row)

        # Column widths: item column wider, company columns narrow
        n_cols = 1 + len(all_companies)
        item_col_w = 145
        # Available width: A4 portrait usable = ~510pt
        comp_col_w = max(28, min(45, (510 - item_col_w) / max(1, len(all_companies))))
        col_widths = [item_col_w] + [comp_col_w] * len(all_companies)

        tbl = RLTable(table_data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
            # Highlight target column (column index 1)
            ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#E8EDFF")),
        ]
        # Style category rows: span the row visually (background only, no merge to keep glyphs)
        for idx in cat_row_indices:
            style_cmds.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#f3f4f6")))
            style_cmds.append(("SPAN", (0, idx), (-1, idx)))

        tbl.setStyle(RLTableStyle(style_cmds))
        elements.append(tbl)

        return elements

    def _build_competitive_analysis_pages(self, cr) -> list:
        """Competitive analysis: 5 chart types × 2×3 Table grid (6 markets).

        Uses ReportLab Table layout (not Drawing.shift) for reliable positioning.
        Each page: heading + 3-row × 2-col Table of mini-chart Drawings.
        Row 1: Global | US
        Row 2: EMEA  | LATAM
        Row 3: Japan  | SEA
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle

        t = self._t
        s = self._styles
        elements: list = []

        ca = cr.competitive_analysis
        if not ca or not ca.markets:
            return elements

        # Lookup: market_name → {chart_type → MarketChart}
        market_charts: dict[str, dict[str, object]] = {}
        for market in ca.markets:
            market_charts[market.market_name] = {
                c.chart_type: c for c in market.charts
            }

        chart_types = [
            "magic_quadrant", "bcg_matrix", "mckinsey_moat",
            "security_posture", "data_governance",
            "gs_risk_return", "bubble_3d",
        ]
        chart_title_map = {
            "magic_quadrant": "chart_magic_quadrant",
            "bcg_matrix": "chart_bcg_matrix",
            "mckinsey_moat": "chart_mckinsey_moat",
            "security_posture": "chart_security_posture",
            "data_governance": "chart_data_governance",
            "gs_risk_return": "chart_gs_risk_return",
            "bubble_3d": "chart_bubble_3d",
        }
        quadrant_map = {
            "magic_quadrant": ["challengers", "leaders", "niche_players", "visionaries"],
            "bcg_matrix": ["question_marks", "stars", "dogs", "cash_cows"],
            "mckinsey_moat": ["innovator", "fortress", "fast_follower", "commodity"],
            "security_posture": ["compliance_risk", "privacy_leader", "exposed", "security_fortress"],
            "data_governance": ["transparent_vuln", "trust_leader", "high_risk", "opaque_fortress"],
        }

        # Grid: 3 rows × 2 cols
        grid_rows = [
            ("Global", "US"),
            ("EMEA", "LATAM"),
            ("Japan", "SEA"),
        ]

        cw = self._CELL_W
        ch = self._CELL_H
        label_h = 14  # height for market name label row

        for ctype in chart_types:
            has_data = any(
                ctype in market_charts.get(mn, {})
                for row in grid_rows for mn in row
            )
            if not has_data:
                continue

            elements.append(PageBreak())

            # Page heading
            title_key = chart_title_map.get(ctype, ctype)
            page_title = t.get(title_key, ctype)
            elements.append(
                Paragraph(f"{t['competitive_analysis']} — {page_title}", s["heading1"])
            )
            elements.append(
                HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=2 * mm)
            )

            # Extract axis rationale from first available chart of this type
            sample_chart = None
            for market in ca.markets:
                for ch_obj in market.charts:
                    if ch_obj.chart_type == ctype:
                        sample_chart = ch_obj
                        break
                if sample_chart:
                    break

            # Axis rationale captions
            if sample_chart:
                x_rat = (sample_chart.x_axis_rationale_ja if self._lang == "ja" and sample_chart.x_axis_rationale_ja
                         else sample_chart.x_axis_rationale)
                y_rat = (sample_chart.y_axis_rationale_ja if self._lang == "ja" and sample_chart.y_axis_rationale_ja
                         else sample_chart.y_axis_rationale)
                x_label = (sample_chart.x_axis_label_ja if self._lang == "ja" and sample_chart.x_axis_label_ja
                           else sample_chart.x_axis_label)
                y_label = (sample_chart.y_axis_label_ja if self._lang == "ja" and sample_chart.y_axis_label_ja
                           else sample_chart.y_axis_label)
                cap_font = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
                cap_bold = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"
                if x_rat or y_rat:
                    cap_parts = []
                    if x_label and x_rat:
                        cap_parts.append(
                            f'<font name="{cap_bold}" size="7" color="#5271FF">X: {x_label}</font>'
                            f'<font name="{cap_font}" size="7" color="#6b7280"> — {x_rat}</font>'
                        )
                    if y_label and y_rat:
                        cap_parts.append(
                            f'<font name="{cap_bold}" size="7" color="#5271FF">Y: {y_label}</font>'
                            f'<font name="{cap_font}" size="7" color="#6b7280"> — {y_rat}</font>'
                        )
                    for cap in cap_parts:
                        elements.append(Paragraph(cap, s["body"]))
                else:
                    elements.append(Paragraph(t["competitive_subtitle"], s["body_dim"]))
            else:
                elements.append(Paragraph(t["competitive_subtitle"], s["body_dim"]))
            elements.append(Spacer(1, 1.5 * mm))

            # Build Table data: alternating label-row + chart-row
            table_data = []
            body_font = "HeiseiKakuGo-W5" if self._lang == "ja" else "Helvetica-Bold"

            for m_left, m_right in grid_rows:
                # Label row
                left_label = self._MARKET_ORDER_JA.get(m_left, m_left) if self._lang == "ja" else m_left
                right_label = self._MARKET_ORDER_JA.get(m_right, m_right) if self._lang == "ja" else m_right
                table_data.append([
                    Paragraph(f'<font name="{body_font}" size="8" color="#5271FF">{left_label}</font>', s["body"]),
                    Paragraph(f'<font name="{body_font}" size="8" color="#5271FF">{right_label}</font>', s["body"]),
                ])

                # Chart row
                row_charts = []
                for mname in (m_left, m_right):
                    chart = market_charts.get(mname, {}).get(ctype)
                    if chart is None:
                        # Empty placeholder drawing
                        placeholder = Drawing(cw, ch)
                        placeholder.add(Rect(0, 0, cw, ch,
                                             fillColor=colors.HexColor("#f5f5f5"),
                                             strokeColor=COLOR_BORDER, strokeWidth=0.3))
                        nf = "HeiseiMin-W3" if self._lang == "ja" else "Helvetica"
                        placeholder.add(String(cw / 2 - 12, ch / 2, "No data",
                                               fontName=nf, fontSize=7, fillColor=COLOR_TEXT_DIM))
                        row_charts.append(placeholder)
                    else:
                        qlabels = None
                        if ctype in quadrant_map:
                            qlabels = [t.get(k, k) for k in quadrant_map[ctype]]
                        row_charts.append(self._mini_chart(chart, ctype, qlabels))
                table_data.append(row_charts)

            # Create Table with 6 rows (3 label + 3 chart), 2 cols
            row_heights = []
            for _ in grid_rows:
                row_heights.append(label_h)
                row_heights.append(ch)

            tbl = RLTable(table_data, colWidths=[cw, cw], rowHeights=row_heights)
            tbl.setStyle(RLTableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
            elements.append(tbl)

        return elements
