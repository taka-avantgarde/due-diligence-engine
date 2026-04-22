"""Parse AI-generated consulting report JSON into ConsultingReport model.

Used by ``dde report --consulting result.json`` to load and validate
the structured JSON output produced by IDE AI (Claude Code, Cursor, etc.).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.models import (
    AtlasAxisScore,
    AtlasAxisSubItem,
    AtlasFourAxisEvaluation,
    CompanyImplementationStatus,
    CompetitiveAnalysis,
    CompetitorDataPoint,
    CompetitorRationale,
    ConsultingReport,
    EnhancedDimensionScore,
    FutureOutlook,
    ImplementationMatrix,
    ImplementationStatus,
    InvestmentThesis,
    MarketChart,
    MarketPosition,
    MatrixItem,
    SiteVerificationItem,
    SiteVerificationReport,
    StrategicAction,
    StrategicAdvice,
    SWOTAnalysis,
    SWOTItem,
    YearProjection,
)

logger = logging.getLogger(__name__)


def parse_consulting_json(file_path: str | Path) -> ConsultingReport:
    """Load a consulting report JSON file and return a validated model.

    Args:
        file_path: Path to the JSON file produced by the IDE AI.

    Returns:
        A validated ``ConsultingReport`` instance with missing fields
        filled with safe defaults and scores clamped to valid ranges.
    """
    path = Path(file_path)
    raw_text = path.read_text(encoding="utf-8")
    data = _extract_json(raw_text)
    return _build_report(data)


def parse_consulting_dict(data: dict[str, Any]) -> ConsultingReport:
    """Build a ConsultingReport from an already-parsed dict."""
    return _build_report(data)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from raw text, handling markdown code blocks."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding the outermost { ... }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Could not parse consulting report JSON. "
        "Ensure the AI output is valid JSON."
    )


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _build_report(data: dict[str, Any]) -> ConsultingReport:
    """Build and validate a ConsultingReport from a raw dict."""

    # --- dimension scores ---
    raw_dims = data.get("dimension_scores", {})
    dimension_scores: dict[str, EnhancedDimensionScore] = {}
    for key, val in raw_dims.items():
        if isinstance(val, dict):
            dimension_scores[key] = EnhancedDimensionScore(
                score=_clamp(float(val.get("score", 0)), 0, 100),
                level=int(_clamp(float(val.get("level", 1)), 1, 10)),
                label=str(val.get("label", "")),
                rationale=str(val.get("rationale", "")),
                business_explanation=str(val.get("business_explanation", "")),
                enables=str(val.get("enables", "")),
            )

    # --- SWOT ---
    raw_swot = data.get("swot", {})
    swot = SWOTAnalysis(
        strengths=[SWOTItem(**s) for s in raw_swot.get("strengths", []) if isinstance(s, dict)],
        weaknesses=[SWOTItem(**s) for s in raw_swot.get("weaknesses", []) if isinstance(s, dict)],
        opportunities=[SWOTItem(**s) for s in raw_swot.get("opportunities", []) if isinstance(s, dict)],
        threats=[SWOTItem(**s) for s in raw_swot.get("threats", []) if isinstance(s, dict)],
    )

    # --- Future outlook ---
    raw_outlook = data.get("future_outlook", {})
    future_outlook = FutureOutlook(
        product_vision=str(raw_outlook.get("product_vision", "")),
        viability_assessment=str(raw_outlook.get("viability_assessment", "")),
        year_1=_parse_projection(raw_outlook.get("year_1")),
        year_3=_parse_projection(raw_outlook.get("year_3")),
        year_5=_parse_projection(raw_outlook.get("year_5")),
    )

    # --- Strategic advice ---
    raw_advice = data.get("strategic_advice", {})
    strategic_advice = StrategicAdvice(
        immediate_actions=[
            StrategicAction(**a)
            for a in raw_advice.get("immediate_actions", [])
            if isinstance(a, dict)
        ],
        medium_term=[
            StrategicAction(**a)
            for a in raw_advice.get("medium_term", [])
            if isinstance(a, dict)
        ],
        long_term_vision=str(raw_advice.get("long_term_vision", "")),
    )

    # --- Investment thesis ---
    raw_thesis = data.get("investment_thesis", {})
    investment_thesis = InvestmentThesis(
        recommendation=str(raw_thesis.get("recommendation", "")),
        rationale=str(raw_thesis.get("rationale", "")),
        key_risks=_ensure_str_list(raw_thesis.get("key_risks", [])),
        key_upside=_ensure_str_list(raw_thesis.get("key_upside", [])),
        comparable_companies=_ensure_str_list(raw_thesis.get("comparable_companies", [])),
        suggested_valuation_factors=str(raw_thesis.get("suggested_valuation_factors", "")),
    )

    # --- Site verification ---
    site_verification: SiteVerificationReport | None = None
    raw_sv = data.get("site_verification")
    if isinstance(raw_sv, dict):
        sv_items: list[SiteVerificationItem] = []
        for item in raw_sv.get("items", []):
            if isinstance(item, dict):
                sv_items.append(SiteVerificationItem(
                    item_key=str(item.get("item_key", "")),
                    item_name=str(item.get("item_name", "")),
                    item_name_ja=str(item.get("item_name_ja", "")),
                    score=_clamp(float(item.get("score", 0)), 0, 100),
                    confidence=str(item.get("confidence", "medium")),
                    rationale=str(item.get("rationale", "")),
                    evidence=_ensure_str_list(item.get("evidence", [])),
                ))
        site_verification = SiteVerificationReport(
            urls_analyzed=_ensure_str_list(raw_sv.get("urls_analyzed", [])),
            items=sv_items,
            overall_credibility=_clamp(float(raw_sv.get("overall_credibility", 0)), 0, 100),
            summary=str(raw_sv.get("summary", "")),
        )

    # --- Competitive analysis ---
    competitive_analysis: CompetitiveAnalysis | None = None
    raw_ca = data.get("competitive_analysis")
    if isinstance(raw_ca, dict):
        markets: list[MarketPosition] = []
        for mkt in raw_ca.get("markets", []):
            if not isinstance(mkt, dict):
                continue
            charts: list[MarketChart] = []
            for ch in mkt.get("charts", []):
                if not isinstance(ch, dict):
                    continue
                data_points: list[CompetitorDataPoint] = []
                for dp in ch.get("data_points", []):
                    if not isinstance(dp, dict):
                        continue
                    data_points.append(CompetitorDataPoint(
                        name=str(dp.get("name", "")),
                        x=_clamp(float(dp.get("x", 0)), 0, 100),
                        y=_clamp(float(dp.get("y", 0)), 0, 100),
                        z=_clamp(float(dp.get("z", 0)), 0, 100),
                        is_target=bool(dp.get("is_target", False)),
                    ))
                charts.append(MarketChart(
                    chart_type=str(ch.get("chart_type", "")),
                    title=str(ch.get("title", "")),
                    title_ja=str(ch.get("title_ja", "")),
                    x_axis_label=str(ch.get("x_axis_label", "")),
                    x_axis_label_ja=str(ch.get("x_axis_label_ja", "")),
                    y_axis_label=str(ch.get("y_axis_label", "")),
                    y_axis_label_ja=str(ch.get("y_axis_label_ja", "")),
                    data_points=data_points,
                ))
            markets.append(MarketPosition(
                market_name=str(mkt.get("market_name", "")),
                market_name_ja=str(mkt.get("market_name_ja", "")),
                charts=charts,
            ))
        competitive_analysis = CompetitiveAnalysis(
            target_company=str(raw_ca.get("target_company", "")),
            home_country=str(raw_ca.get("home_country", "")),
            markets=markets,
        )

    atlas_four_axis = _parse_atlas_four_axis(data.get("atlas_four_axis"))
    implementation_matrix = _parse_implementation_matrix(data.get("implementation_matrix"))
    competitor_rationales = _parse_competitor_rationales(data.get("competitor_rationales"))

    return ConsultingReport(
        executive_summary=str(data.get("executive_summary", "")),
        executive_summary_business=str(data.get("executive_summary_business", "")),
        dimension_scores=dimension_scores,
        overall_score=_clamp(float(data.get("overall_score", 0)), 0, 100),
        grade=str(data.get("grade", "")),
        swot=swot,
        future_outlook=future_outlook,
        strategic_advice=strategic_advice,
        investment_thesis=investment_thesis,
        red_flags=data.get("red_flags", []),
        tech_level_summary=data.get("tech_level_summary", {}),
        glossary_additions=data.get("glossary_additions", []),
        ai_model_used=str(data.get("ai_model_used", "")),
        analysis_id=str(data.get("analysis_id", "")),
        project_name=str(data.get("project_name", "")),
        site_verification=site_verification,
        competitive_analysis=competitive_analysis,
        atlas_four_axis=atlas_four_axis,
        implementation_matrix=implementation_matrix,
        competitor_rationales=competitor_rationales,
    )


def _parse_competitor_rationales(data: Any) -> list[CompetitorRationale]:
    """Parse competitor selection rationales (3-5 lines each) — v0.3.1."""
    if not isinstance(data, list):
        return []
    out: list[CompetitorRationale] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append(
            CompetitorRationale(
                name=str(item.get("name", "")),
                category=str(item.get("category", "")),
                rationale_en=str(item.get("rationale_en", "")),
                rationale_ja=str(item.get("rationale_ja", "")),
                hq_country=str(item.get("hq_country", "")),
                market_position=str(item.get("market_position", "")),
                estimated_score=_clamp(float(item.get("estimated_score", 0)), 0, 100),
            )
        )
    return out


def _parse_atlas_four_axis(data: Any) -> AtlasFourAxisEvaluation | None:
    """Parse Atlas 4-axis evaluation block (Task C)."""
    if not isinstance(data, dict):
        return None

    axes: list[AtlasAxisScore] = []
    for axis_data in data.get("axes", []) or []:
        if not isinstance(axis_data, dict):
            continue
        sub_items: list[AtlasAxisSubItem] = []
        for si in axis_data.get("sub_items", []) or []:
            if not isinstance(si, dict):
                continue
            sub_items.append(
                AtlasAxisSubItem(
                    key=str(si.get("key", "")),
                    name_en=str(si.get("name_en", "")),
                    name_ja=str(si.get("name_ja", "")),
                    score=_clamp(float(si.get("score", 0)), 0, 100),
                    level=int(_clamp(float(si.get("level", 1)), 1, 10)),
                    weight_pct=float(si.get("weight_pct", 0)),
                    rationale=str(si.get("rationale", "")),
                )
            )
        axes.append(
            AtlasAxisScore(
                axis_key=str(axis_data.get("axis_key", "")),
                name_en=str(axis_data.get("name_en", "")),
                name_ja=str(axis_data.get("name_ja", "")),
                weight_pct=float(axis_data.get("weight_pct", 0)),
                score=_clamp(float(axis_data.get("score", 0)), 0, 100),
                level=int(_clamp(float(axis_data.get("level", 1)), 1, 10)),
                rationale=str(axis_data.get("rationale", "")),
                sub_items=sub_items,
            )
        )

    return AtlasFourAxisEvaluation(
        axes=axes,
        overall_score=_clamp(float(data.get("overall_score", 0)), 0, 100),
        industry_context=str(data.get("industry_context", "")),
        summary=str(data.get("summary", "")),
        summary_ja=str(data.get("summary_ja", "")),
    )


def _parse_implementation_matrix(data: Any) -> ImplementationMatrix | None:
    """Parse Implementation Capability Matrix (Task D)."""
    if not isinstance(data, dict):
        return None

    items: list[MatrixItem] = []
    for item_data in data.get("items", []) or []:
        if not isinstance(item_data, dict):
            continue
        statuses: list[CompanyImplementationStatus] = []
        for s in item_data.get("statuses", []) or []:
            if not isinstance(s, dict):
                continue
            # Parse status enum with safe fallback to UNKNOWN
            raw_status = str(s.get("status", "unknown")).lower()
            try:
                status_enum = ImplementationStatus(raw_status)
            except ValueError:
                status_enum = ImplementationStatus.UNKNOWN
            statuses.append(
                CompanyImplementationStatus(
                    company_name=str(s.get("company_name", "")),
                    status=status_enum,
                    evidence=str(s.get("evidence", "")),
                )
            )
        items.append(
            MatrixItem(
                category=str(item_data.get("category", "")),
                item_key=str(item_data.get("item_key", "")),
                item_en=str(item_data.get("item_en", "")),
                item_ja=str(item_data.get("item_ja", "")),
                statuses=statuses,
            )
        )

    return ImplementationMatrix(
        target_company=str(data.get("target_company", "")),
        competitors=[str(c) for c in (data.get("competitors", []) or [])],
        items=items,
    )


def _parse_projection(raw: Any) -> YearProjection | None:
    if not isinstance(raw, dict):
        return None
    return YearProjection(
        projection=str(raw.get("projection", "")),
        confidence=str(raw.get("confidence", "medium")),
        key_milestones=_ensure_str_list(raw.get("key_milestones", [])),
    )


def _ensure_str_list(val: Any) -> list[str]:
    if not isinstance(val, list):
        return []
    return [str(item) for item in val]
