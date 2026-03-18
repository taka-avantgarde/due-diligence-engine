"""Technology-focused scoring engine with 10-level ratings.

Evaluates TECHNOLOGY ONLY (no team assessment).
Each dimension is rated on a 10-level scale with clear criteria,
then converted to a 100-point weighted score.

Dimensions (weights sum to 1.0):
1. Technical Originality  (0.25) - Is this real IP or an API wrapper?
2. Technology Advancement  (0.20) - How cutting-edge is the technology?
3. Implementation Depth    (0.20) - Is the implementation production-grade?
4. Architecture Quality    (0.15) - Is the architecture scalable and well-designed?
5. Claim Consistency       (0.10) - Do docs match code?
6. Security Posture        (0.10) - Security practices
"""

from __future__ import annotations

from src.models import (
    AnalysisResult,
    RedFlag,
    Score,
    ScoreDimension,
    Severity,
    TechLevel,
    TechLevelRating,
)


# 10-level technology rating criteria
TECH_LEVEL_CRITERIA: dict[str, list[TechLevel]] = {
    "technical_originality": [
        TechLevel(level=1, label="Lv.1 — Copy", description="Existing OSS/API をそのまま利用。独自コードなし"),
        TechLevel(level=2, label="Lv.2 — Wrapper", description="API薄いラッパー。設定変更程度のカスタマイズ"),
        TechLevel(level=3, label="Lv.3 — Glue", description="複数APIの組み合わせ。独自ロジックはルーティングのみ"),
        TechLevel(level=4, label="Lv.4 — Customized", description="既存技術のカスタマイズ。一部独自処理あり"),
        TechLevel(level=5, label="Lv.5 — Extended", description="既存フレームワークの大幅拡張。独自アルゴリズム一部あり"),
        TechLevel(level=6, label="Lv.6 — Hybrid", description="既存+独自技術のハイブリッド。明確なIP領域あり"),
        TechLevel(level=7, label="Lv.7 — Original", description="コア技術が独自実装。特許申請可能レベル"),
        TechLevel(level=8, label="Lv.8 — Advanced", description="業界先端の独自実装。学会発表レベル"),
        TechLevel(level=9, label="Lv.9 — Breakthrough", description="新しい技術パラダイムの提案。論文引用されるレベル"),
        TechLevel(level=10, label="Lv.10 — Frontier", description="世界最先端。既存技術を根本的に置き換える可能性"),
    ],
    "technology_advancement": [
        TechLevel(level=1, label="Lv.1 — Legacy", description="10年以上前の技術。メンテナンスモード"),
        TechLevel(level=2, label="Lv.2 — Outdated", description="5-10年前の技術。後継技術が存在"),
        TechLevel(level=3, label="Lv.3 — Established", description="広く普及した安定技術。新規性なし"),
        TechLevel(level=4, label="Lv.4 — Current", description="現在の業界標準レベル"),
        TechLevel(level=5, label="Lv.5 — Modern", description="最新のベストプラクティスを採用"),
        TechLevel(level=6, label="Lv.6 — Progressive", description="次世代技術の早期採用者"),
        TechLevel(level=7, label="Lv.7 — Innovative", description="業界内で先進的。競合が追随中"),
        TechLevel(level=8, label="Lv.8 — Leading", description="業界をリードする技術選択"),
        TechLevel(level=9, label="Lv.9 — Pioneering", description="新カテゴリを定義する技術"),
        TechLevel(level=10, label="Lv.10 — Visionary", description="5年先の技術を今実装。市場が追いつく段階"),
    ],
    "implementation_depth": [
        TechLevel(level=1, label="Lv.1 — Mockup", description="UIモックのみ。バックエンド未実装"),
        TechLevel(level=2, label="Lv.2 — PoC", description="概念実証レベル。ハードコード多数"),
        TechLevel(level=3, label="Lv.3 — Prototype", description="動くプロトタイプ。エラー処理なし"),
        TechLevel(level=4, label="Lv.4 — Alpha", description="基本機能動作。テストなし"),
        TechLevel(level=5, label="Lv.5 — Beta", description="主要機能実装済み。基本テストあり"),
        TechLevel(level=6, label="Lv.6 — RC", description="本番想定の実装。CI/CDあり"),
        TechLevel(level=7, label="Lv.7 — Production", description="本番運用中。監視・ログあり"),
        TechLevel(level=8, label="Lv.8 — Mature", description="長期運用実績。パフォーマンス最適化済み"),
        TechLevel(level=9, label="Lv.9 — Enterprise", description="大規模運用対応。SLA保証レベル"),
        TechLevel(level=10, label="Lv.10 — Mission-Critical", description="ミッションクリティカル対応。冗長性・DR完備"),
    ],
    "architecture_quality": [
        TechLevel(level=1, label="Lv.1 — Spaghetti", description="構造なし。単一ファイルに全コード"),
        TechLevel(level=2, label="Lv.2 — Monolith", description="最小限の分離。全結合"),
        TechLevel(level=3, label="Lv.3 — Layered", description="基本的なレイヤー分離あり"),
        TechLevel(level=4, label="Lv.4 — Modular", description="モジュール分割。一部密結合"),
        TechLevel(level=5, label="Lv.5 — Clean", description="関心の分離が明確。テスト容易"),
        TechLevel(level=6, label="Lv.6 — Scalable", description="水平スケーリング対応設計"),
        TechLevel(level=7, label="Lv.7 — Microservice", description="適切なサービス分割。API契約明確"),
        TechLevel(level=8, label="Lv.8 — Event-Driven", description="イベント駆動。非同期処理最適化"),
        TechLevel(level=9, label="Lv.9 — Cloud-Native", description="クラウドネイティブ設計。自動スケール"),
        TechLevel(level=10, label="Lv.10 — Distributed", description="分散システム。CAP定理を意識した設計"),
    ],
    "claim_consistency": [
        TechLevel(level=1, label="Lv.1 — Fabricated", description="主張と実装が完全に乖離。意図的虚偽の疑い"),
        TechLevel(level=2, label="Lv.2 — Misleading", description="重要な点で誤解を招く主張"),
        TechLevel(level=3, label="Lv.3 — Exaggerated", description="大幅な誇張。実装は主張の30%以下"),
        TechLevel(level=4, label="Lv.4 — Overstated", description="一部誇張あり。コア機能は存在"),
        TechLevel(level=5, label="Lv.5 — Partial", description="主張の半分程度が検証可能"),
        TechLevel(level=6, label="Lv.6 — Mostly True", description="大部分が事実。軽微な不一致あり"),
        TechLevel(level=7, label="Lv.7 — Accurate", description="主張が実装と一致。ベンチマーク一部あり"),
        TechLevel(level=8, label="Lv.8 — Verified", description="主張がコードで完全に検証可能"),
        TechLevel(level=9, label="Lv.9 — Conservative", description="実装が主張以上。控えめな表現"),
        TechLevel(level=10, label="Lv.10 — Transparent", description="全主張に証拠付き。第三者検証済み"),
    ],
    "security_posture": [
        TechLevel(level=1, label="Lv.1 — Negligent", description="ハードコードされた秘密鍵。SQLi脆弱性"),
        TechLevel(level=2, label="Lv.2 — Minimal", description="基本的な問題あり。入力検証なし"),
        TechLevel(level=3, label="Lv.3 — Basic", description="最低限の対策。OWASP Top10未対応"),
        TechLevel(level=4, label="Lv.4 — Standard", description="基本的なセキュリティ対策済み"),
        TechLevel(level=5, label="Lv.5 — Compliant", description="業界標準準拠。定期的な依存関係更新"),
        TechLevel(level=6, label="Lv.6 — Hardened", description="セキュリティスキャン自動化。脆弱性管理あり"),
        TechLevel(level=7, label="Lv.7 — Defense-in-Depth", description="多層防御。ペネトレーションテスト実施"),
        TechLevel(level=8, label="Lv.8 — Zero-Trust", description="ゼロトラスト設計。暗号化完備"),
        TechLevel(level=9, label="Lv.9 — Certified", description="SOC2/ISO27001等の認証取得レベル"),
        TechLevel(level=10, label="Lv.10 — Military-Grade", description="国防レベル。形式検証・監査完備"),
    ],
}


# Dimension definitions with weights
DIMENSIONS = {
    "technical_originality": {
        "name": "Technical Originality",
        "name_ja": "技術独自性",
        "weight": 0.25,
    },
    "technology_advancement": {
        "name": "Technology Advancement",
        "name_ja": "技術先進性",
        "weight": 0.20,
    },
    "implementation_depth": {
        "name": "Implementation Depth",
        "name_ja": "実装深度",
        "weight": 0.20,
    },
    "architecture_quality": {
        "name": "Architecture Quality",
        "name_ja": "アーキテクチャ品質",
        "weight": 0.15,
    },
    "claim_consistency": {
        "name": "Claim Consistency",
        "name_ja": "主張整合性",
        "weight": 0.10,
    },
    "security_posture": {
        "name": "Security Posture",
        "name_ja": "セキュリティ態勢",
        "weight": 0.10,
    },
}


class Scorer:
    """Computes a technology-focused due diligence score.

    Evaluates technology ONLY (no team/process assessment).
    Each dimension is rated on a 10-level scale and converted to 100-point score.
    """

    def score(self, result: AnalysisResult) -> Score:
        """ヒューリスティックスコアとAI結果を統合して最終スコアを算出。

        AI結果がある場合: (heuristic * 0.3 + ai_avg * 0.7)
        AI結果がない場合: ヒューリスティック100%
        """
        dimensions = [
            self._score_technical_originality(result),
            self._score_technology_advancement(result),
            self._score_implementation_depth(result),
            self._score_architecture_quality(result),
            self._score_claim_consistency(result),
            self._score_security_posture(result),
        ]

        # マルチAI結果がある場合、各次元のスコアをAI平均と加重統合
        if result.ai_results:
            dimensions = self._integrate_ai_scores(dimensions, result)

        # Collect all red flags
        all_flags: list[RedFlag] = []
        all_flags.extend(result.code_analysis.red_flags)
        all_flags.extend(result.doc_analysis.red_flags)
        all_flags.extend(result.git_forensics.red_flags)
        all_flags.extend(result.consistency.red_flags)

        # Compute tech level ratings
        tech_ratings = self._compute_tech_ratings(result)

        score = Score(
            dimensions=dimensions,
            red_flags=all_flags,
            tech_ratings=tech_ratings,
        )
        score.compute()
        return score

    def _integrate_ai_scores(
        self,
        heuristic_dims: list[ScoreDimension],
        result: AnalysisResult,
    ) -> list[ScoreDimension]:
        """ヒューリスティックスコアとマルチAI平均スコアを加重統合。

        各次元: 統合スコア = heuristic * 0.3 + ai_avg * 0.7
        """
        dim_key_map = {
            "Technical Originality": "technical_originality",
            "Technology Advancement": "technology_advancement",
            "Implementation Depth": "implementation_depth",
            "Architecture Quality": "architecture_quality",
            "Claim Consistency": "claim_consistency",
            "Security Posture": "security_posture",
        }

        valid_ai = [
            r for r in result.ai_results.values()
            if r.error is None and r.dimension_scores
        ]

        if not valid_ai:
            return heuristic_dims

        integrated: list[ScoreDimension] = []
        for dim in heuristic_dims:
            ai_key = dim_key_map.get(dim.name)
            if not ai_key:
                integrated.append(dim)
                continue

            ai_scores = [
                r.dimension_scores.get(ai_key, 0)
                for r in valid_ai
                if ai_key in r.dimension_scores
            ]

            if ai_scores:
                ai_avg = sum(ai_scores) / len(ai_scores)
                blended = dim.score * 0.3 + ai_avg * 0.7

                provider_details = ", ".join(
                    f"{r.provider.capitalize()}: {r.dimension_scores.get(ai_key, 0):.0f}"
                    for r in valid_ai
                    if ai_key in r.dimension_scores
                )
                rationale = (
                    f"{dim.rationale} "
                    f"[AI avg: {ai_avg:.0f} ({provider_details}) | "
                    f"Heuristic: {dim.score:.0f} | Blended: {blended:.0f}]"
                )

                integrated.append(ScoreDimension(
                    name=dim.name,
                    score=round(blended, 1),
                    weight=dim.weight,
                    rationale=rationale,
                    sub_scores=dim.sub_scores,
                    flags=dim.flags,
                ))
            else:
                integrated.append(dim)

        return integrated

    def get_level_criteria(self, dimension_key: str) -> list[TechLevel]:
        """Get the 10-level criteria for a given dimension."""
        return TECH_LEVEL_CRITERIA.get(dimension_key, [])

    def _compute_tech_ratings(self, result: AnalysisResult) -> list[TechLevelRating]:
        """Compute 10-level ratings for all dimensions."""
        ratings: list[TechLevelRating] = []

        # Technical Originality
        orig_level = self._determine_originality_level(result)
        criteria = TECH_LEVEL_CRITERIA["technical_originality"]
        ratings.append(TechLevelRating(
            dimension="Technical Originality",
            dimension_ja="技術独自性",
            level=orig_level,
            label=criteria[orig_level - 1].label,
            description=criteria[orig_level - 1].description,
            criteria=criteria,
        ))

        # Technology Advancement
        adv_level = self._determine_advancement_level(result)
        criteria = TECH_LEVEL_CRITERIA["technology_advancement"]
        ratings.append(TechLevelRating(
            dimension="Technology Advancement",
            dimension_ja="技術先進性",
            level=adv_level,
            label=criteria[adv_level - 1].label,
            description=criteria[adv_level - 1].description,
            criteria=criteria,
        ))

        # Implementation Depth
        impl_level = self._determine_implementation_level(result)
        criteria = TECH_LEVEL_CRITERIA["implementation_depth"]
        ratings.append(TechLevelRating(
            dimension="Implementation Depth",
            dimension_ja="実装深度",
            level=impl_level,
            label=criteria[impl_level - 1].label,
            description=criteria[impl_level - 1].description,
            criteria=criteria,
        ))

        # Architecture Quality
        arch_level = self._determine_architecture_level(result)
        criteria = TECH_LEVEL_CRITERIA["architecture_quality"]
        ratings.append(TechLevelRating(
            dimension="Architecture Quality",
            dimension_ja="アーキテクチャ品質",
            level=arch_level,
            label=criteria[arch_level - 1].label,
            description=criteria[arch_level - 1].description,
            criteria=criteria,
        ))

        # Claim Consistency
        claim_level = self._determine_claim_level(result)
        criteria = TECH_LEVEL_CRITERIA["claim_consistency"]
        ratings.append(TechLevelRating(
            dimension="Claim Consistency",
            dimension_ja="主張整合性",
            level=claim_level,
            label=criteria[claim_level - 1].label,
            description=criteria[claim_level - 1].description,
            criteria=criteria,
        ))

        # Security Posture
        sec_level = self._determine_security_level(result)
        criteria = TECH_LEVEL_CRITERIA["security_posture"]
        ratings.append(TechLevelRating(
            dimension="Security Posture",
            dimension_ja="セキュリティ態勢",
            level=sec_level,
            label=criteria[sec_level - 1].label,
            description=criteria[sec_level - 1].description,
            criteria=criteria,
        ))

        return ratings

    # --- Level determination methods (heuristic-based) ---

    def _determine_originality_level(self, result: AnalysisResult) -> int:
        code = result.code_analysis
        ratio = code.api_wrapper_ratio
        lines = code.total_lines

        if ratio > 0.8:
            return 1 if lines < 500 else 2
        if ratio > 0.6:
            return 3
        if ratio > 0.4:
            return 4
        if ratio > 0.2:
            base = 5
        else:
            base = 6

        # Boost for large, diverse codebases
        if lines > 20000 and len(code.languages) >= 3:
            base = min(base + 2, 10)
        elif lines > 10000:
            base = min(base + 1, 10)

        return base

    def _determine_advancement_level(self, result: AnalysisResult) -> int:
        code = result.code_analysis
        base = 4  # Start at "Current"

        # Language modernity heuristics
        modern_langs = {"TypeScript", "Rust", "Go", "Kotlin", "Swift", "Dart"}
        legacy_langs = {"Perl", "COBOL", "Fortran", "VB"}

        project_langs = set(code.languages.keys())
        # Normalize extensions to language names
        ext_to_lang = {
            ".ts": "TypeScript", ".tsx": "TypeScript",
            ".rs": "Rust", ".go": "Go",
            ".kt": "Kotlin", ".swift": "Swift", ".dart": "Dart",
            ".py": "Python", ".js": "JavaScript",
        }
        actual_langs = {ext_to_lang.get(ext, ext) for ext in project_langs}

        if actual_langs & modern_langs:
            base += 1
        if actual_langs & legacy_langs:
            base -= 2

        # Dependency freshness proxy: more deps = potentially more modern ecosystem
        if code.dependency_count > 30:
            base += 1
        if code.has_ci_cd:
            base += 1

        return max(1, min(base, 10))

    def _determine_implementation_level(self, result: AnalysisResult) -> int:
        code = result.code_analysis
        base = 3  # Start at "Prototype"

        if code.total_lines > 500:
            base = 4
        if code.total_lines > 2000:
            base = 5
        if code.has_tests:
            base += 1
        if code.has_ci_cd:
            base += 1
        if code.total_lines > 10000 and code.has_tests and code.has_ci_cd:
            base += 1
        if code.total_files > 100 and code.has_documentation:
            base += 1

        return max(1, min(base, 10))

    def _determine_architecture_level(self, result: AnalysisResult) -> int:
        code = result.code_analysis
        base = 3  # Start at "Layered"

        if code.total_files > 20:
            base = 4
        if code.total_files > 50 and len(code.languages) >= 2:
            base = 5
        if code.total_files > 100:
            base += 1
        if code.has_ci_cd and code.has_tests:
            base += 1
        if code.has_documentation:
            base += 1

        # Penalty for excessive dependencies (can indicate poor architecture)
        if code.dependency_count > 100:
            base -= 1

        return max(1, min(base, 10))

    def _determine_claim_level(self, result: AnalysisResult) -> int:
        consistency = result.consistency
        score = consistency.consistency_score
        contradictions = len(consistency.contradictions)

        if contradictions > 5:
            return max(1, min(3, int(score / 20)))
        if contradictions > 2:
            return max(3, min(5, int(score / 15)))

        # Map consistency_score (0-100) to level (1-10)
        level = max(1, min(10, int(score / 10)))
        return level

    def _determine_security_level(self, result: AnalysisResult) -> int:
        code = result.code_analysis
        base = 4  # Start at "Standard"

        security_flags = [f for f in code.red_flags if "security" in f.category.lower()]

        if any(f.severity == Severity.CRITICAL for f in security_flags):
            return 1
        if any(f.severity == Severity.HIGH for f in security_flags):
            base -= 2

        base -= len(security_flags)

        if code.has_ci_cd:
            base += 1
        if code.has_tests:
            base += 1
        if code.dependency_count < 50:
            base += 1

        return max(1, min(base, 10))

    # --- Score computation methods (convert level to 100-point) ---

    def _score_technical_originality(self, result: AnalysisResult) -> ScoreDimension:
        level = self._determine_originality_level(result)
        score = level * 10.0
        code = result.code_analysis

        return ScoreDimension(
            name=DIMENSIONS["technical_originality"]["name"],
            score=score,
            weight=DIMENSIONS["technical_originality"]["weight"],
            rationale=(
                f"Tech Level {level}/10. "
                f"API wrapper ratio: {code.api_wrapper_ratio:.0%}, "
                f"{code.total_lines} lines across {len(code.languages)} languages."
            ),
            sub_scores={
                "api_wrapper_ratio": max(0, 100 - code.api_wrapper_ratio * 100),
                "codebase_size": min(100, code.total_lines / 100),
            },
            flags=[f for f in code.red_flags if f.category == "code_originality"],
        )

    def _score_technology_advancement(self, result: AnalysisResult) -> ScoreDimension:
        level = self._determine_advancement_level(result)
        score = level * 10.0

        return ScoreDimension(
            name=DIMENSIONS["technology_advancement"]["name"],
            score=score,
            weight=DIMENSIONS["technology_advancement"]["weight"],
            rationale=f"Tech Level {level}/10. Technology stack modernity assessment.",
            sub_scores={
                "language_modernity": score,
                "ecosystem_freshness": score,
            },
        )

    def _score_implementation_depth(self, result: AnalysisResult) -> ScoreDimension:
        level = self._determine_implementation_level(result)
        score = level * 10.0
        code = result.code_analysis

        rationale_parts = [f"Tech Level {level}/10."]
        if code.has_tests:
            rationale_parts.append("Tests present.")
        else:
            rationale_parts.append("No tests.")
        if code.has_ci_cd:
            rationale_parts.append("CI/CD configured.")
        else:
            rationale_parts.append("No CI/CD.")

        return ScoreDimension(
            name=DIMENSIONS["implementation_depth"]["name"],
            score=score,
            weight=DIMENSIONS["implementation_depth"]["weight"],
            rationale=" ".join(rationale_parts),
            sub_scores={
                "tests": 100 if code.has_tests else 0,
                "ci_cd": 100 if code.has_ci_cd else 0,
                "documentation": 100 if code.has_documentation else 0,
            },
            flags=[f for f in code.red_flags if f.category in ("code_quality", "engineering_maturity")],
        )

    def _score_architecture_quality(self, result: AnalysisResult) -> ScoreDimension:
        level = self._determine_architecture_level(result)
        score = level * 10.0
        code = result.code_analysis

        return ScoreDimension(
            name=DIMENSIONS["architecture_quality"]["name"],
            score=score,
            weight=DIMENSIONS["architecture_quality"]["weight"],
            rationale=(
                f"Tech Level {level}/10. "
                f"{code.total_files} files, {code.dependency_count} dependencies."
            ),
            sub_scores={
                "file_structure": min(100, code.total_files * 2),
                "dependency_health": max(0, 100 - max(0, code.dependency_count - 50)),
            },
        )

    def _score_claim_consistency(self, result: AnalysisResult) -> ScoreDimension:
        level = self._determine_claim_level(result)
        score = level * 10.0
        consistency = result.consistency

        return ScoreDimension(
            name=DIMENSIONS["claim_consistency"]["name"],
            score=score,
            weight=DIMENSIONS["claim_consistency"]["weight"],
            rationale=(
                f"Tech Level {level}/10. "
                f"{len(consistency.verified_claims)} verified, "
                f"{len(consistency.unverified_claims)} unverified, "
                f"{len(consistency.contradictions)} contradictions."
            ),
            sub_scores={
                "verified_ratio": consistency.consistency_score,
                "contradiction_count": max(0, 100 - len(consistency.contradictions) * 20),
            },
            flags=consistency.red_flags,
        )

    def _score_security_posture(self, result: AnalysisResult) -> ScoreDimension:
        level = self._determine_security_level(result)
        score = level * 10.0
        code = result.code_analysis

        security_flags = [f for f in code.red_flags if "security" in f.category.lower()]

        return ScoreDimension(
            name=DIMENSIONS["security_posture"]["name"],
            score=score,
            weight=DIMENSIONS["security_posture"]["weight"],
            rationale=(
                f"Tech Level {level}/10. "
                f"{code.dependency_count} dependencies, "
                f"{len(security_flags)} security findings."
            ),
            sub_scores={
                "dependency_risk": max(0, 100 - code.dependency_count),
                "security_flags": max(0, 100 - len(security_flags) * 25),
            },
        )
