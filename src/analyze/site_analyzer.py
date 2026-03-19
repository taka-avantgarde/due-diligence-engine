"""サイト分析エンジン — プロダクト/サービスのWebサイトを分析し信頼性を評価。

主な機能:
1. Webサイトのスクレイピング・テキスト抽出
2. サイト上の主張（技術力、実績、チーム等）を構造化して抽出
3. GitHubソースコードと照合して「主張 vs 実態」のギャップを検出
4. AIによる総合信頼性評価
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from src.models import RedFlag, Severity

logger = logging.getLogger(__name__)

# スクレイピング対象外のURL拡張子
_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".woff", ".woff2",
    ".css", ".js",
}

# 最大クロール数
_MAX_PAGES = 10
_TIMEOUT_SEC = 15


class SiteClaim(BaseModel):
    """サイトから抽出した主張（クレーム）。"""
    category: str  # "technology", "performance", "team", "traction", "security", "funding"
    claim: str  # 主張の内容
    source_url: str  # 主張が記載されていたページURL
    confidence: float = 0.5  # 抽出信頼度 (0-1)


class SiteAnalysisResult(BaseModel):
    """サイト分析の結果。"""
    site_url: str
    pages_analyzed: int = 0
    total_text_length: int = 0
    claims: list[SiteClaim] = Field(default_factory=list)
    technologies_mentioned: list[str] = Field(default_factory=list)
    team_info: dict[str, Any] = Field(default_factory=dict)
    traction_claims: list[str] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    raw_texts: dict[str, str] = Field(default_factory=dict)  # URL→テキスト


class CrossValidationResult(BaseModel):
    """GitHubソースコード vs サイト主張のクロス検証結果。"""
    verified_claims: list[dict[str, str]] = Field(default_factory=list)
    unverified_claims: list[dict[str, str]] = Field(default_factory=list)
    contradictions: list[dict[str, str]] = Field(default_factory=list)
    exaggerations: list[dict[str, str]] = Field(default_factory=list)
    credibility_score: float = 50.0  # 0-100
    red_flags: list[RedFlag] = Field(default_factory=list)
    summary: str = ""


def _extract_meta_content(html: str) -> str:
    """HTMLのmeta/title/OGP/JSON-LDからテキストを抽出。

    SPA（Next.js等）ではbodyにコンテンツがないため、
    meta description, og:*, title, JSON-LD等からテキストを収集する。
    """
    parts = []

    # <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if title_match:
        parts.append(title_match.group(1).strip())

    # meta name="description" / og:description / twitter:description
    for attr in ("description", "og:description", "twitter:description",
                 "og:title", "twitter:title"):
        pattern = rf'<meta\s+(?:name|property)=["\'](?:{re.escape(attr)})["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)
        if not match:
            # content が先に来るパターン
            pattern2 = rf'<meta\s+content=["\']([^"\']+)["\']\s+(?:name|property)=["\'](?:{re.escape(attr)})["\']'
            match = re.search(pattern2, html, re.IGNORECASE)
        if match:
            parts.append(match.group(1).strip())

    # JSON-LD (application/ld+json)
    for ld_match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    ):
        try:
            import json
            ld_data = json.loads(ld_match.group(1))
            if isinstance(ld_data, dict):
                for key in ("name", "description", "headline", "about"):
                    val = ld_data.get(key, "")
                    if isinstance(val, str) and val:
                        parts.append(val)
        except Exception:
            pass

    # Next.js RSC payloadから文字列を抽出（self.__next_f.push 内のテキスト）
    for rsc_match in re.finditer(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL,
    ):
        rsc_text = rsc_match.group(1)
        # エスケープされたUnicode文字を復元
        try:
            rsc_text = rsc_text.encode().decode("unicode_escape")
        except Exception:
            pass
        # HTML/JSONの中からcontent文字列を抽出
        for content_match in re.finditer(r'"content":"([^"]+)"', rsc_text):
            val = content_match.group(1)
            if len(val) > 10 and not val.startswith("http"):
                parts.append(val)
        # "children":"テキスト" パターン
        for child_match in re.finditer(r'"children":"([^"]{10,})"', rsc_text):
            parts.append(child_match.group(1))

    return " ".join(dict.fromkeys(parts))  # 重複排除しつつ順序維持


def _extract_text_from_html(html: str) -> str:
    """HTMLからテキストを抽出（簡易パーサー、beautifulsoup不要）。

    SPA対応: bodyが空の場合はmeta/OGP/JSON-LD/RSCペイロードからも抽出。
    """
    # script, style タグの中身を除去
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # HTMLコメント除去
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    # HTMLタグ除去
    text = re.sub(r"<[^>]+>", " ", text)
    # HTMLエンティティをデコード
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    # 余分な空白を圧縮
    text = re.sub(r"\s+", " ", text).strip()

    # SPA対策: bodyテキストが短い場合、meta/OGP/RSCからも抽出
    if len(text) < 100:
        meta_text = _extract_meta_content(html)
        if meta_text:
            text = f"{text} {meta_text}".strip()

    return text


def _extract_links(html: str, base_url: str) -> list[str]:
    """HTMLからリンクを抽出。"""
    links = []
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = match.group(1)
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full_url = urljoin(base_url, href)
        # 同一ドメインのみ
        if urlparse(full_url).netloc == urlparse(base_url).netloc:
            # スキップ拡張子チェック
            path = urlparse(full_url).path.lower()
            if not any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
                links.append(full_url.split("#")[0].split("?")[0])  # フラグメント・クエリ除去
    return list(set(links))


class SiteAnalyzer:
    """Webサイトをクロール・分析して主張を抽出するアナライザー。"""

    def __init__(self) -> None:
        self._visited: set[str] = set()
        self._texts: dict[str, str] = {}

    def analyze(self, site_url: str) -> SiteAnalysisResult:
        """サイトを分析して主張を抽出。

        Args:
            site_url: 分析対象のWebサイトURL

        Returns:
            サイト分析結果
        """
        result = SiteAnalysisResult(site_url=site_url)

        # URLの正規化
        if not site_url.startswith("http"):
            site_url = "https://" + site_url

        # クロール
        self._crawl(site_url, max_depth=2)

        result.pages_analyzed = len(self._texts)
        result.raw_texts = dict(self._texts)
        result.total_text_length = sum(len(t) for t in self._texts.values())

        if not self._texts:
            result.red_flags.append(RedFlag(
                category="site_analysis",
                title="サイトにアクセスできません",
                description=f"URL {site_url} からコンテンツを取得できませんでした。",
                severity=Severity.HIGH,
            ))
            return result

        # 全テキストを結合して分析
        all_text = "\n\n".join(self._texts.values())

        # 技術スタック抽出
        result.technologies_mentioned = self._extract_technologies(all_text)

        # 主張抽出
        result.claims = self._extract_claims(all_text, site_url)

        # チーム情報抽出
        result.team_info = self._extract_team_info(all_text)

        # トラクション（実績）抽出
        result.traction_claims = self._extract_traction(all_text)

        # ローカルレッドフラグ検出
        result.red_flags.extend(self._detect_red_flags(all_text, result))

        # Findings生成
        result.findings.append(f"Analyzed {result.pages_analyzed} pages ({result.total_text_length:,} chars)")
        result.findings.append(f"Found {len(result.claims)} claims, {len(result.technologies_mentioned)} technologies")
        if result.traction_claims:
            result.findings.append(f"Traction claims: {len(result.traction_claims)}")

        return result

    def _crawl(self, url: str, max_depth: int = 2, depth: int = 0) -> None:
        """再帰的にページをクロール。"""
        if depth > max_depth or len(self._visited) >= _MAX_PAGES:
            return
        if url in self._visited:
            return

        self._visited.add(url)

        try:
            with httpx.Client(timeout=_TIMEOUT_SEC, follow_redirects=True) as client:
                resp = client.get(url, headers={
                    "User-Agent": "DDE-SiteAnalyzer/1.0 (Due Diligence Engine)",
                    "Accept": "text/html,application/xhtml+xml",
                })
                if resp.status_code != 200:
                    logger.warning(f"HTTP {resp.status_code} for {url}")
                    return
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    return

                html = resp.text
                text = _extract_text_from_html(html)
                if text and len(text) > 20:
                    self._texts[url] = text

                # リンクを再帰的にクロール
                if depth < max_depth:
                    links = _extract_links(html, url)
                    # 優先ページ: about, team, pricing, features, technology, security
                    priority_keywords = ["about", "team", "pricing", "feature", "tech", "security", "product"]
                    priority_links = [l for l in links if any(kw in l.lower() for kw in priority_keywords)]
                    other_links = [l for l in links if l not in priority_links]

                    for link in (priority_links + other_links)[:_MAX_PAGES]:
                        self._crawl(link, max_depth, depth + 1)

        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")

    def _extract_technologies(self, text: str) -> list[str]:
        """テキストから言及されている技術を抽出。"""
        tech_patterns = [
            # 言語・フレームワーク
            r"\b(Python|JavaScript|TypeScript|Rust|Go|Java|Kotlin|Swift|C\+\+|Ruby|Scala)\b",
            r"\b(React|Vue|Angular|Next\.js|Nuxt|Django|Flask|FastAPI|Spring|Rails)\b",
            r"\b(Flutter|React Native|SwiftUI|Jetpack Compose)\b",
            # インフラ
            r"\b(AWS|GCP|Azure|Kubernetes|Docker|Terraform)\b",
            r"\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|DynamoDB)\b",
            r"\b(Firebase|Supabase|Vercel|Cloudflare|Heroku)\b",
            # AI/ML
            r"\b(GPT-4|Claude|Gemini|LLM|machine learning|deep learning|neural network)\b",
            r"\b(TensorFlow|PyTorch|Hugging Face|OpenAI|Anthropic)\b",
            # セキュリティ
            r"\b(E2EE|end-to-end encryption|zero-knowledge|Signal Protocol|TLS|OAuth)\b",
            r"\b(SOC\s*2|HIPAA|GDPR|ISO\s*27001|PCI\s*DSS)\b",
        ]
        found = set()
        for pattern in tech_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found.add(match.group(0))
        return sorted(found)

    def _extract_claims(self, text: str, site_url: str) -> list[SiteClaim]:
        """テキストから主張を抽出。"""
        claims = []

        # パフォーマンス系: 数値+倍、%、ms、秒
        perf_patterns = [
            (r"(\d+[xX×]?\s*(?:faster|速い|高速|倍速|improvement|向上))", "performance"),
            (r"(\d+(?:\.\d+)?%\s*(?:less|more|reduction|increase|削減|向上|改善))", "performance"),
            (r"((?:under|within|以内|未満)\s*\d+\s*(?:ms|milliseconds|ミリ秒|seconds|秒))", "performance"),
            (r"(99\.?\d*%\s*(?:uptime|availability|可用性|稼働率))", "performance"),
        ]
        for pattern, category in perf_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(SiteClaim(
                    category=category,
                    claim=match.group(0).strip(),
                    source_url=site_url,
                    confidence=0.7,
                ))

        # ユーザー・トラクション系
        traction_patterns = [
            (r"(\d[\d,]*\+?\s*(?:users|customers|企業|ユーザー|clients|partners|downloads))", "traction"),
            (r"(\$[\d,.]+[MBK]?\s*(?:ARR|MRR|revenue|funding|raised|調達))", "funding"),
            (r"(Series\s*[A-D]|シリーズ[A-D]|seed\s*round|プレシリーズ)", "funding"),
        ]
        for pattern, category in traction_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(SiteClaim(
                    category=category,
                    claim=match.group(0).strip(),
                    source_url=site_url,
                    confidence=0.6,
                ))

        # セキュリティ系
        security_patterns = [
            (r"(SOC\s*2\s*(?:Type\s*(?:I{1,2}|1|2))?(?:\s*certified|\s*compliant)?)", "security"),
            (r"(ISO\s*27001(?:\s*certified)?)", "security"),
            (r"(HIPAA\s*compliant)", "security"),
            (r"(GDPR\s*compliant)", "security"),
            (r"(PCI\s*DSS(?:\s*Level\s*\d)?)", "security"),
            (r"(end-to-end\s*encrypt(?:ion|ed)|E2EE)", "security"),
            (r"(zero[\s-]*knowledge(?:\s*proof)?)", "security"),
        ]
        for pattern, category in security_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(SiteClaim(
                    category=category,
                    claim=match.group(0).strip(),
                    source_url=site_url,
                    confidence=0.8,
                ))

        return claims

    def _extract_team_info(self, text: str) -> dict[str, Any]:
        """チーム情報を抽出。"""
        info: dict[str, Any] = {}

        # チーム規模
        team_match = re.search(r"(\d+)\+?\s*(?:team\s*members|engineers|developers|employees|名|人)", text, re.IGNORECASE)
        if team_match:
            info["team_size"] = team_match.group(0)

        # 著名人・出身企業
        big_tech = re.findall(r"(?:ex-|former\s+)?(Google|Meta|Apple|Amazon|Microsoft|Netflix|Stripe|McKinsey|Goldman)", text, re.IGNORECASE)
        if big_tech:
            info["notable_backgrounds"] = list(set(big_tech))

        return info

    def _extract_traction(self, text: str) -> list[str]:
        """トラクション（実績）の主張を抽出。"""
        traction = []
        patterns = [
            r"\d[\d,]*\+?\s*(?:users|customers|企業|clients|downloads|installs)",
            r"\$[\d,.]+[MBK]?\s*(?:in\s+)?(?:revenue|ARR|MRR|GMV|processed)",
            r"\d+[xX×]\s*(?:growth|成長|increase)",
            r"(?:featured\s+in|selected\s+by|backed\s+by|partnered\s+with)\s+\w+",
            r"(?:Y\s*Combinator|Techstars|500\s*Startups|a16z|Sequoia)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                traction.append(match.group(0).strip())
        return list(set(traction))

    def _detect_red_flags(self, text: str, result: SiteAnalysisResult) -> list[RedFlag]:
        """サイトコンテンツからレッドフラグを検出。"""
        flags = []

        # 過大な数値主張
        huge_numbers = re.findall(r"\d{6,}\+?\s*(?:users|customers|downloads)", text, re.IGNORECASE)
        if huge_numbers and not result.traction_claims:
            flags.append(RedFlag(
                category="site_credibility",
                title="検証不能な大規模ユーザー数の主張",
                description=f"サイトで非常に大きなユーザー数が主張されていますが、裏付けが見つかりません: {', '.join(huge_numbers[:3])}",
                severity=Severity.MEDIUM,
            ))

        # バズワード密度が高い
        buzzwords = re.findall(
            r"\b(revolutionary|game[-\s]?changing|disruptive|world[-\s]?first|industry[-\s]?leading|cutting[-\s]?edge|breakthrough|unprecedented)\b",
            text, re.IGNORECASE,
        )
        if len(buzzwords) > 8:
            flags.append(RedFlag(
                category="site_credibility",
                title="バズワードの過剰使用",
                description=f"{len(buzzwords)}個のマーケティングバズワードが検出されました。実態よりも誇張されている可能性があります。",
                severity=Severity.LOW,
            ))

        # 技術的な詳細が欠如
        tech_depth_indicators = re.findall(
            r"\b(API|SDK|documentation|docs|open[-\s]?source|GitHub|architecture|whitepaper|RFC)\b",
            text, re.IGNORECASE,
        )
        if len(result.technologies_mentioned) > 5 and len(tech_depth_indicators) < 3:
            flags.append(RedFlag(
                category="site_credibility",
                title="技術的詳細の欠如",
                description="多数の技術を謳っていますが、具体的な技術文書やAPIドキュメントへの言及が少ないです。",
                severity=Severity.MEDIUM,
            ))

        return flags


def cross_validate_site_vs_code(
    site_result: SiteAnalysisResult,
    code_languages: dict[str, int],
    code_findings: list[str],
    has_tests: bool,
    has_ci_cd: bool,
    dependency_count: int,
    doc_claims: list[str],
) -> CrossValidationResult:
    """サイトの主張とGitHubソースコードをクロス検証。

    Args:
        site_result: サイト分析結果
        code_languages: コード内の言語別行数
        code_findings: コード分析の所見
        has_tests: テストがあるか
        has_ci_cd: CI/CDがあるか
        dependency_count: 依存パッケージ数
        doc_claims: ドキュメントからの主張

    Returns:
        クロス検証結果
    """
    result = CrossValidationResult()

    # 1. 技術スタックの検証: サイトで謳っている技術がコードに存在するか
    code_langs_lower = {k.lower() for k in code_languages.keys()}
    code_findings_text = " ".join(code_findings).lower()

    for tech in site_result.technologies_mentioned:
        tech_lower = tech.lower()
        # コード内に存在するか確認
        found_in_code = (
            tech_lower in code_langs_lower
            or tech_lower in code_findings_text
        )
        if found_in_code:
            result.verified_claims.append({
                "claim": f"Technology: {tech}",
                "status": "verified",
                "evidence": "Found in codebase",
            })
        else:
            result.unverified_claims.append({
                "claim": f"Technology: {tech}",
                "status": "unverified",
                "note": "Mentioned on site but not found in codebase",
            })

    # 2. セキュリティ主張の検証
    security_claims = [c for c in site_result.claims if c.category == "security"]
    for claim in security_claims:
        claim_lower = claim.claim.lower()
        if "e2ee" in claim_lower or "end-to-end" in claim_lower:
            # E2EEの実装証拠をコードから探す
            has_crypto = any(
                kw in code_findings_text
                for kw in ["encrypt", "crypto", "signal", "e2ee", "ratchet", "diffie"]
            )
            if has_crypto:
                result.verified_claims.append({
                    "claim": claim.claim,
                    "status": "verified",
                    "evidence": "Encryption-related code found",
                })
            else:
                result.contradictions.append({
                    "claim": claim.claim,
                    "status": "contradiction",
                    "note": "E2EE claimed but no encryption code found",
                })
        elif "soc 2" in claim_lower or "iso 27001" in claim_lower:
            # コンプライアンス系は外部証明なのでコードからは検証困難
            result.unverified_claims.append({
                "claim": claim.claim,
                "status": "unverifiable_from_code",
                "note": "Compliance certifications cannot be verified from code alone",
            })

    # 3. テスト・品質主張の検証
    quality_keywords = ["tested", "test coverage", "ci/cd", "automated", "quality"]
    has_quality_claim = any(
        any(kw in c.claim.lower() for kw in quality_keywords)
        for c in site_result.claims
    )
    if has_quality_claim:
        if has_tests and has_ci_cd:
            result.verified_claims.append({
                "claim": "Quality/Testing practices",
                "status": "verified",
                "evidence": f"Tests and CI/CD found in codebase",
            })
        elif not has_tests:
            result.contradictions.append({
                "claim": "Quality/Testing practices",
                "status": "contradiction",
                "note": "Quality claims made but no tests found in codebase",
            })

    # 4. 誇張度の計算
    perf_claims = [c for c in site_result.claims if c.category == "performance"]
    for claim in perf_claims:
        # 数値が非常に大きい場合は誇張の可能性
        numbers = re.findall(r"(\d+)", claim.claim)
        for num_str in numbers:
            num = int(num_str)
            if num > 100:  # 100x以上の改善は疑わしい
                result.exaggerations.append({
                    "claim": claim.claim,
                    "note": f"Extremely large improvement claim ({num})",
                })

    # 5. 信頼性スコア計算
    total_claims = len(result.verified_claims) + len(result.unverified_claims) + len(result.contradictions)
    if total_claims > 0:
        verified_ratio = len(result.verified_claims) / total_claims
        contradiction_ratio = len(result.contradictions) / total_claims
        # 基本スコア: 検証済み割合 × 100 - 矛盾ペナルティ
        result.credibility_score = round(
            max(0, min(100, verified_ratio * 80 + 20 - contradiction_ratio * 40 - len(result.exaggerations) * 5)),
            1,
        )
    else:
        result.credibility_score = 50.0  # データ不足

    # レッドフラグ生成
    if result.credibility_score < 30:
        result.red_flags.append(RedFlag(
            category="cross_validation",
            title="サイト主張とコードの間に重大な乖離",
            description=f"信頼性スコア: {result.credibility_score}/100。サイトの主張の多くがコードで裏付けられていません。",
            severity=Severity.CRITICAL,
        ))
    elif result.credibility_score < 50:
        result.red_flags.append(RedFlag(
            category="cross_validation",
            title="サイト主張の信頼性が低い",
            description=f"信頼性スコア: {result.credibility_score}/100。一部の主張がコードと矛盾しています。",
            severity=Severity.HIGH,
        ))

    if len(result.contradictions) > 0:
        result.red_flags.append(RedFlag(
            category="cross_validation",
            title=f"{len(result.contradictions)}件の矛盾を検出",
            description="サイトの主張がソースコードの実態と矛盾しています。",
            severity=Severity.HIGH,
            evidence=[c["claim"] for c in result.contradictions],
        ))

    if len(result.exaggerations) > 0:
        result.red_flags.append(RedFlag(
            category="cross_validation",
            title=f"{len(result.exaggerations)}件の誇張の可能性",
            description="非現実的なパフォーマンス数値の主張が検出されました。",
            severity=Severity.MEDIUM,
            evidence=[e["claim"] for e in result.exaggerations],
        ))

    # サマリー生成
    result.summary = (
        f"Credibility Score: {result.credibility_score}/100 | "
        f"Verified: {len(result.verified_claims)} | "
        f"Unverified: {len(result.unverified_claims)} | "
        f"Contradictions: {len(result.contradictions)} | "
        f"Exaggerations: {len(result.exaggerations)}"
    )

    return result
