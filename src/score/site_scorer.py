"""サイト単体スコアリングエンジン — GitHubリポなしで100点満点技術レポートを生成。

7軸評価:
1. Tech Stack Depth     (0.20) — 言及技術の数・先進度・組み合わせの妥当性
2. Product Maturity     (0.15) — デモ・API Docs・料金ページ・変更履歴の有無
3. Security Posture     (0.10) — 認証・コンプライアンス・暗号化の主張
4. Transparency         (0.10) — 技術文書・ホワイトペーパー・OSS公開
5. Market Traction      (0.15) — ユーザー数・売上・パートナー・受賞歴
6. Innovation Score     (0.20) — 独自技術の主張 vs バズワード密度
7. Credibility Signals  (0.10) — 内部整合性・誇張度・具体性

AI搭載モード: ANTHROPIC_API_KEY が設定されている場合、Claude APIによるセマンティック分析を使用。
フォールバック: APIキーがない場合はregexベースのヒューリスティック分析を使用。
"""

from __future__ import annotations

import json
import logging
import os
import re

from src.analyze.site_analyzer import SiteAnalysisResult
from src.models import RedFlag, Score, ScoreDimension, Severity

logger = logging.getLogger(__name__)


# 8軸の定義
SITE_DIMENSIONS = {
    "tech_stack_depth": {
        "name": "Tech Stack Depth",
        "name_ja": "技術スタック深度",
        "weight": 0.20,
    },
    "product_maturity": {
        "name": "Product Maturity",
        "name_ja": "プロダクト成熟度",
        "weight": 0.15,
    },
    "security_posture": {
        "name": "Security Posture",
        "name_ja": "セキュリティ態勢",
        "weight": 0.10,
    },
    "transparency": {
        "name": "Transparency",
        "name_ja": "透明性・文書化",
        "weight": 0.10,
    },
    "market_traction": {
        "name": "Market Traction",
        "name_ja": "市場トラクション",
        "weight": 0.15,
    },
    "innovation_score": {
        "name": "Innovation Score",
        "name_ja": "イノベーション度",
        "weight": 0.20,
    },
    "credibility_signals": {
        "name": "Credibility Signals",
        "name_ja": "信頼性シグナル",
        "weight": 0.10,
    },
}

# 先進的な技術キーワード（重み付け）
_ADVANCED_TECH = {
    "rust": 3, "go": 2, "typescript": 2, "kotlin": 2, "swift": 2,
    "kubernetes": 3, "terraform": 2, "docker": 1,
    "e2ee": 3, "end-to-end encryption": 3, "zero-knowledge": 3,
    "signal protocol": 3, "ml-kem": 4, "pqc": 4,
    "gpt-4": 2, "claude": 2, "gemini": 2, "llm": 2,
    "machine learning": 2, "deep learning": 2, "neural network": 2,
    "pytorch": 2, "tensorflow": 2,
    "graphql": 2, "grpc": 2, "webassembly": 3, "wasm": 3,
    "next.js": 1, "react": 1, "vue": 1, "flutter": 2,
    "aws": 1, "gcp": 1, "azure": 1,
    "postgresql": 1, "redis": 1, "elasticsearch": 2,
    "firebase": 1, "supabase": 1,
}

# コンプライアンス・認証の重み
_COMPLIANCE_KEYWORDS = {
    "soc 2": 4, "soc2": 4, "iso 27001": 4, "iso27001": 4,
    "hipaa": 3, "gdpr": 3, "pci dss": 3, "pci-dss": 3,
    "fedramp": 4, "ccpa": 2, "soc 1": 3,
}

# Claude AI分析プロンプト
_AI_SCORING_PROMPT = """You are an expert due diligence analyst evaluating a website/product for investors and business professionals.

Analyze the following website content and score it on 7 dimensions. This site could be any type: tech startup, service company, B2B SaaS, consulting firm, e-commerce, traditional business, Japanese company, etc. Evaluate it fairly regardless of industry.

WEBSITE URL: {site_url}
PAGES ANALYZED: {pages_count}

WEBSITE CONTENT (truncated):
{content}

Score each dimension from 0 to 100 based on what the content reveals. Be fair and contextual — a consulting firm shouldn't be penalized for not open-sourcing code, and a Japanese company shouldn't be penalized for not having English docs.

Scoring Guidelines:
- 80-100: Strong evidence, specific details, verifiable claims
- 60-79: Good signals but some gaps
- 40-59: Mixed or minimal evidence
- 20-39: Weak or vague
- 0-19: Missing or very poor

Dimensions to score:
1. tech_stack_depth: How technically sophisticated is this product/service? Consider: specific technologies mentioned, depth of technical explanation, infrastructure, integrations. For non-tech companies, evaluate their operational/process sophistication instead.
2. product_maturity: How mature/ready is the product or service? Consider: features, documentation, pricing, case studies, testimonials, launch status, customer support availability.
3. security_posture: How seriously do they take security and data protection? Consider: privacy policy, data handling, certifications (SOC2, GDPR, ISO27001), encryption mentions, security page.
4. transparency: How transparent are they about their operations? Consider: team info, company background, contact details, blog/news, public roadmap, open communication.
5. market_traction: What evidence of real-world adoption exists? Consider: customer count, case studies, testimonials, media coverage, awards, partnerships, revenue mentions.
6. innovation_score: How innovative or differentiated is their approach? Consider: unique value proposition, proprietary methods, creative solutions, differentiation from competitors. Penalize empty buzzwords without substance.
7. credibility_signals: How credible and trustworthy do they appear? Consider: specific data, company registration, contact info, privacy policy, legal pages, professional presentation, consistency of claims.

Return ONLY a JSON object (no markdown, no explanation) in this exact format:
{{
  "dimensions": {{
    "tech_stack_depth": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences explaining the score in English>"
    }},
    "product_maturity": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences>"
    }},
    "security_posture": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences>"
    }},
    "transparency": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences>"
    }},
    "market_traction": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences>"
    }},
    "innovation_score": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences>"
    }},
    "credibility_signals": {{
      "score": <0-100>,
      "rationale": "<1-2 sentences>"
    }}
  }},
  "red_flags": [
    {{
      "title": "<short title>",
      "description": "<1-2 sentences>",
      "severity": "low|medium|high|critical"
    }}
  ],
  "overall_summary": "<2-3 sentences overall assessment of this site/company>"
}}"""


class SiteScorer:
    """サイト単体の100点満点スコアリングエンジン。

    ANTHROPIC_API_KEY が設定されている場合:
        Claude APIによるセマンティック分析（業種・言語を問わず正確に評価）
    APIキーがない場合:
        regexベースのヒューリスティック分析（フォールバック）
    """

    def score(self, site_result: SiteAnalysisResult) -> Score:
        """サイト分析結果から7軸スコアを算出。

        Args:
            site_result: SiteAnalyzerが返すサイト分析結果

        Returns:
            7軸スコア・総合点・グレード付きのScoreオブジェクト
        """
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            try:
                return self._score_with_ai(site_result, anthropic_key)
            except Exception as e:
                logger.warning(f"AI scoring failed, falling back to heuristic: {e}")

        return self._score_heuristic(site_result)

    def _score_with_ai(self, site_result: SiteAnalysisResult, api_key: str) -> Score:
        """Claude APIによるセマンティックスコアリング。"""
        import anthropic

        # テキストを最大15,000文字に圧縮（トークン節約）
        all_text = "\n\n".join(
            f"[{url}]\n{text[:2000]}"
            for url, text in list(site_result.raw_texts.items())[:8]
        )
        all_text = all_text[:15000]

        prompt = _AI_SCORING_PROMPT.format(
            site_url=site_result.site_url,
            pages_count=site_result.pages_analyzed,
            content=all_text,
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5",  # 高速・低コスト
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_response = message.content[0].text.strip()

        # JSON抽出（```json...``` ブロックがある場合も対応）
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON in AI response: {raw_response[:200]}")

        data = json.loads(json_match.group(0))
        return self._build_score_from_ai_response(data, site_result)

    def _build_score_from_ai_response(
        self, data: dict, site_result: SiteAnalysisResult
    ) -> Score:
        """AI応答からScoreオブジェクトを構築。"""
        dimensions = []
        ai_dims = data.get("dimensions", {})

        for key, dim_def in SITE_DIMENSIONS.items():
            ai_dim = ai_dims.get(key, {})
            score_val = float(ai_dim.get("score", 50))
            rationale = ai_dim.get("rationale", "")

            dimensions.append(ScoreDimension(
                name=dim_def["name"],
                score=round(score_val, 1),
                weight=dim_def["weight"],
                rationale=rationale,
                sub_scores={},
            ))

        # AI検出のレッドフラグ
        all_flags = list(site_result.red_flags)
        for flag_data in data.get("red_flags", []):
            severity_map = {
                "low": Severity.LOW,
                "medium": Severity.MEDIUM,
                "high": Severity.HIGH,
                "critical": Severity.CRITICAL,
            }
            all_flags.append(RedFlag(
                category="ai_detected",
                title=flag_data.get("title", "Issue"),
                description=flag_data.get("description", ""),
                severity=severity_map.get(
                    flag_data.get("severity", "medium"), Severity.MEDIUM
                ),
            ))

        # overall_summary を findings に追加
        summary = data.get("overall_summary", "")
        if summary:
            site_result.findings.insert(0, f"AI Analysis: {summary}")

        score_obj = Score(
            dimensions=dimensions,
            red_flags=all_flags,
        )
        score_obj.compute()
        return score_obj

    # --- フォールバック: regexベースのスコアリング ---

    def _score_heuristic(self, site_result: SiteAnalysisResult) -> Score:
        """APIキーがない場合のregexベーススコアリング。"""
        all_text = "\n".join(site_result.raw_texts.values()).lower()

        dimensions = [
            self._score_tech_stack_depth(site_result, all_text),
            self._score_product_maturity(site_result, all_text),
            self._score_security_posture(site_result, all_text),
            self._score_transparency(site_result, all_text),
            self._score_market_traction(site_result, all_text),
            self._score_innovation(site_result, all_text),
            self._score_credibility_signals(site_result, all_text),
        ]

        all_flags = list(site_result.red_flags)

        score_obj = Score(
            dimensions=dimensions,
            red_flags=all_flags,
        )
        score_obj.compute()
        return score_obj

    def _score_tech_stack_depth(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["tech_stack_depth"]
        tech_count = len(sr.technologies_mentioned)

        advanced_points = 0
        for tech in sr.technologies_mentioned:
            tech_lower = tech.lower()
            for keyword, weight in _ADVANCED_TECH.items():
                if keyword in tech_lower:
                    advanced_points += weight
                    break

        raw = min(100, tech_count * 5 + advanced_points * 3)
        if tech_count == 0:
            raw = 10

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=(
                f"{tech_count} technologies mentioned. "
                f"Advanced tech score: {advanced_points}."
            ),
            sub_scores={
                "tech_count": min(100, tech_count * 10),
                "advanced_score": min(100, advanced_points * 5),
            },
        )

    def _score_product_maturity(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["product_maturity"]
        signals = 0
        details = []

        if re.search(r"\b(pricing|plans?|price|料金|プラン|subscription)\b", text):
            signals += 2
            details.append("pricing")
        if re.search(r"\b(api\s*doc|api\s*reference|developer\s*doc|sdk|swagger|openapi)\b", text):
            signals += 2
            details.append("API docs")
        if re.search(r"\b(demo|free\s*trial|try\s*(?:it|now|free)|無料体験|デモ)\b", text):
            signals += 2
            details.append("demo/trial")
        if re.search(r"\b(changelog|release\s*notes?|what'?s\s*new|更新履歴|リリースノート)\b", text):
            signals += 2
            details.append("changelog")
        if re.search(r"\b(status\s*page|uptime|incident|稼働状況)\b", text):
            signals += 1
            details.append("status page")
        if sr.pages_analyzed >= 5:
            signals += 1
            details.append(f"{sr.pages_analyzed} pages")
        if sr.total_text_length > 10000:
            signals += 1
            details.append("rich content")

        raw = min(100, signals * 9)

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=f"Maturity signals: {', '.join(details) if details else 'none'}.",
            sub_scores={"signal_count": signals},
        )

    def _score_security_posture(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["security_posture"]
        points = 0
        details = []

        for keyword, weight in _COMPLIANCE_KEYWORDS.items():
            if keyword in text:
                points += weight
                details.append(keyword.upper())

        security_claims = [c for c in sr.claims if c.category == "security"]
        points += len(security_claims) * 2
        if security_claims:
            details.append(f"{len(security_claims)} security claims")

        security_pages = [
            url for url in sr.raw_texts
            if any(kw in url.lower() for kw in ["security", "privacy", "trust"])
        ]
        if security_pages:
            points += 3
            details.append("dedicated security page")

        raw = min(100, points * 5 + 20)
        if not security_claims and not details:
            raw = 20

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=f"Security: {', '.join(details) if details else 'No security claims found'}.",
            sub_scores={"compliance_points": points},
        )

    def _score_transparency(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["transparency"]
        signals = 0
        details = []

        if re.search(r"\b(open[\s-]*source|github\.com|gitlab\.com|oss)\b", text):
            signals += 3
            details.append("open source")
        if re.search(r"\b(whitepaper|white\s*paper|technical\s*paper|ホワイトペーパー|技術文書)\b", text):
            signals += 3
            details.append("whitepaper")
        if re.search(r"\b(blog|engineering\s*blog|tech\s*blog|技術ブログ)\b", text):
            signals += 2
            details.append("tech blog")
        if re.search(r"\b(documentation|docs|developer\s*guide|api\s*reference)\b", text):
            signals += 2
            details.append("documentation")
        if re.search(r"\b(rfc|architecture|system\s*design|アーキテクチャ)\b", text):
            signals += 2
            details.append("architecture docs")

        raw = min(100, signals * 8 + 10)

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=f"Transparency: {', '.join(details) if details else 'minimal disclosure'}.",
            sub_scores={"signal_count": signals},
        )

    def _score_market_traction(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["market_traction"]
        points = 0
        details = []

        traction_count = len(sr.traction_claims)
        points += traction_count * 3
        if traction_count > 0:
            details.append(f"{traction_count} traction claims")

        funding_claims = [c for c in sr.claims if c.category == "funding"]
        if funding_claims:
            points += len(funding_claims) * 4
            details.append("funding mentioned")

        if re.search(r"\b(partner|award|認定|受賞|パートナー|featured\s*in|as\s*seen\s*in)\b", text):
            points += 2
            details.append("partnerships/awards")

        if re.search(r"\b(y\s*combinator|techstars|500\s*startups|a16z|sequoia|accel)\b", text):
            points += 4
            details.append("notable backers")

        raw = min(100, points * 5 + 15)
        if traction_count == 0 and not funding_claims:
            raw = 15

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=f"Traction: {', '.join(details) if details else 'no traction data'}.",
            sub_scores={"traction_count": traction_count, "points": points},
        )

    def _score_innovation(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["innovation_score"]

        innovation_keywords = re.findall(
            r"\b(patent|proprietary|novel|unique\s*(?:approach|algorithm|technology)|"
            r"first[\s-]*(?:of|in)|our\s*own|自社開発|独自|特許)\b",
            text, re.IGNORECASE,
        )
        innovation_count = len(innovation_keywords)

        buzzwords = re.findall(
            r"\b(revolutionary|game[\s-]*changing|disruptive|world[\s-]*first|"
            r"industry[\s-]*leading|cutting[\s-]*edge|breakthrough|unprecedented|"
            r"next[\s-]*generation|paradigm[\s-]*shift|synergy|leverage|"
            r"best[\s-]*in[\s-]*class|state[\s-]*of[\s-]*the[\s-]*art)\b",
            text, re.IGNORECASE,
        )
        buzzword_count = len(buzzwords)

        if innovation_count > 0 and buzzword_count <= innovation_count:
            raw = min(100, 50 + innovation_count * 8)
        elif innovation_count > 0:
            raw = min(90, 40 + innovation_count * 5 - buzzword_count * 2)
        else:
            raw = max(15, 35 - buzzword_count * 3)

        raw = max(10, min(100, raw))

        flags = []
        if buzzword_count > 10:
            flags.append(RedFlag(
                category="site_innovation",
                title="バズワード過多",
                description=f"{buzzword_count}個のバズワードが検出。実態との乖離の可能性。",
                severity=Severity.LOW,
            ))

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=(
                f"Innovation claims: {innovation_count}, "
                f"buzzwords: {buzzword_count}."
            ),
            sub_scores={
                "innovation_claims": innovation_count,
                "buzzword_density": buzzword_count,
            },
            flags=flags,
        )

    def _score_credibility_signals(
        self, sr: SiteAnalysisResult, text: str
    ) -> ScoreDimension:
        dim = SITE_DIMENSIONS["credibility_signals"]
        points = 10

        specific_numbers = re.findall(
            r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|users|ms|seconds|customers|countries)\b",
            text, re.IGNORECASE,
        )
        points += min(20, len(specific_numbers) * 2)

        if re.search(r"\b(contact|お問い合わせ|support@|info@)\b", text):
            points += 5
        if re.search(r"\b(inc\.|corp\.|ltd\.|llc|株式会社|合同会社)\b", text, re.IGNORECASE):
            points += 5

        if re.search(r"\b(privacy\s*policy|terms\s*of\s*service|利用規約|プライバシー)\b", text):
            points += 5

        red_flag_penalty = len(sr.red_flags) * 5
        points -= red_flag_penalty

        exaggeration_claims = [
            c for c in sr.claims
            if c.category == "performance" and c.confidence < 0.5
        ]
        points -= len(exaggeration_claims) * 3

        raw = max(10, min(100, points * 2))

        return ScoreDimension(
            name=dim["name"],
            score=round(raw, 1),
            weight=dim["weight"],
            rationale=(
                f"Specifics: {len(specific_numbers)} data points. "
                f"Red flags: {len(sr.red_flags)}."
            ),
            sub_scores={
                "specificity": min(100, len(specific_numbers) * 10),
                "red_flag_penalty": red_flag_penalty,
            },
        )
