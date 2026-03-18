"""メイン分析オーケストレーター（マルチAIプロバイダー対応）。

戦略:
1. ローカル分析（API不要）: コード構造、ドキュメント、Git履歴、整合性チェック
2. AI分析（オプション）: 環境変数 or BYOKキーで設定されたプロバイダーを並列実行
   - 従来方式: Haiku→Sonnet→Opus 3段階パイプライン（環境変数のANTHROPIC_API_KEY使用時）
   - 新方式: マルチプロバイダー並列分析（BYOKキー使用時、最大3社同時）
3. スコアリング: ヒューリスティック + AI結果の加重平均
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import anthropic

from src.ai.providers import (
    AIProvider,
    create_provider,
    estimate_provider_cost,
)
from src.analyze.code import CodeAnalyzer
from src.analyze.consistency import ConsistencyAnalyzer
from src.analyze.docs import DocAnalyzer
from src.analyze.git_forensics import GitForensicsAnalyzer
from src.config import MODELS, Config, estimate_cost
from src.ingest.secure_loader import SecureLoader
from src.models import AIProviderResult, AnalysisResult, RedFlag, Severity
from src.score.scorer import Scorer

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """分析パイプライン全体を統括するオーケストレーター。

    従来の3段階AI分析に加え、BYOKマルチプロバイダー並列分析に対応。
    設定されたプロバイダー（1〜3社）を同時実行し、各社独立の評価結果を取得。
    """

    def __init__(
        self,
        config: Config,
        loader: SecureLoader,
        api_keys: dict[str, str] | None = None,
    ) -> None:
        """
        Args:
            config: アプリケーション設定。
            loader: セキュアローダー。
            api_keys: BYOKのAPIキー dict {"claude": "sk-...", "gemini": "...", "chatgpt": "sk-..."} 。
                      省略時は config の環境変数キーを使用。
        """
        self._config = config
        self._loader = loader
        self._api_keys = api_keys or {}
        self._client: anthropic.Anthropic | None = None
        self._usage: dict[str, dict[str, int]] = {
            "haiku": {"input_tokens": 0, "output_tokens": 0},
            "sonnet": {"input_tokens": 0, "output_tokens": 0},
            "opus": {"input_tokens": 0, "output_tokens": 0},
        }

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._config.anthropic_api_key)
        return self._client

    def _get_effective_api_keys(self) -> dict[str, str]:
        """BYOK キーと環境変数キーをマージして有効なキーセットを返す。

        BYOKキーが優先。環境変数キーはBYOKにないプロバイダーのみ補完。
        """
        keys = dict(self._api_keys)
        env_keys = self._config.get_ai_api_keys()
        for provider, key in env_keys.items():
            if provider not in keys:
                keys[provider] = key
        return keys

    def run(
        self,
        project_name: str,
        repo_path: Path | None = None,
        skip_git: bool = False,
    ) -> AnalysisResult:
        """分析パイプラインを実行。

        Args:
            project_name: 分析対象プロジェクト名。
            repo_path: gitリポジトリのパス（省略時はgit分析をスキップ）。
            skip_git: Trueの場合、gitフォレンジックをスキップ。

        Returns:
            スコアと所見を含む AnalysisResult。
        """
        result = AnalysisResult(project_name=project_name)

        # Phase 1: ローカル分析（API呼び出しなし）
        logger.info("Phase 1: Running local analysis...")
        code_analyzer = CodeAnalyzer(self._loader)
        result.code_analysis = code_analyzer.analyze()

        doc_analyzer = DocAnalyzer(self._loader)
        result.doc_analysis = doc_analyzer.analyze()

        if not skip_git and repo_path and (repo_path / ".git").exists():
            git_analyzer = GitForensicsAnalyzer(repo_path)
            result.git_forensics = git_analyzer.analyze()

        consistency_analyzer = ConsistencyAnalyzer()
        result.consistency = consistency_analyzer.analyze(
            result.code_analysis, result.doc_analysis
        )

        # Phase 2: AI分析（マルチプロバイダー対応）
        effective_keys = self._get_effective_api_keys()

        if effective_keys:
            logger.info(f"Phase 2: Running AI analysis with {len(effective_keys)} provider(s): {list(effective_keys.keys())}")
            self._run_multi_provider_analysis(result, effective_keys)
        elif self._config.anthropic_api_key:
            # 後方互換: 環境変数のAnthropicキーのみの場合は従来の3段階パイプライン
            logger.info("Phase 2: Running legacy AI-enhanced analysis (Haiku→Sonnet→Opus)...")
            ai_findings = self._run_ai_analysis(result)
            self._merge_ai_findings(result, ai_findings)
        else:
            logger.warning("No API key configured. Skipping AI-enhanced analysis.")

        # Phase 3: スコアリング
        logger.info("Phase 3: Computing scores...")
        scorer = Scorer()
        result.score = scorer.score(result)

        # 使用量とコストを記録
        result.model_usage = self._usage
        result.total_cost_usd = self._compute_total_cost(result)

        return result

    def _run_multi_provider_analysis(
        self,
        result: AnalysisResult,
        api_keys: dict[str, str],
    ) -> None:
        """マルチプロバイダー並列分析を実行。

        設定されたプロバイダー（1〜3社）をThreadPoolExecutorで並列実行し、
        各社の結果を AnalysisResult.ai_results に格納。
        """
        summary = self._build_analysis_summary(result)
        context = json.dumps({
            "code_findings": result.code_analysis.findings[:20],
            "doc_claims": [c.get("text", "") for c in result.doc_analysis.claims[:10]],
            "consistency_score": result.consistency.consistency_score,
            "contradictions": result.consistency.contradictions[:5],
        }, ensure_ascii=False)

        providers: list[AIProvider] = []
        for name, key in api_keys.items():
            try:
                provider = create_provider(name, key)
                providers.append(provider)
            except ValueError as e:
                logger.warning(f"Skipping unknown provider {name}: {e}")

        if not providers:
            return

        # 並列実行
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._execute_provider, p, summary, context): p
                for p in providers
            }

            for future in as_completed(futures):
                provider = futures[future]
                try:
                    ai_result = future.result()
                    result.ai_results[provider.provider_name] = ai_result

                    # AI検出レッドフラグをコード分析結果にマージ
                    for flag in ai_result.red_flags:
                        result.code_analysis.red_flags.append(flag)

                    logger.info(
                        f"  {provider.provider_name}: verdict={ai_result.verdict}, "
                        f"confidence={ai_result.confidence}, cost=${ai_result.cost_usd:.4f}"
                    )
                except Exception as e:
                    logger.error(f"Provider {provider.provider_name} failed: {e}")
                    result.ai_results[provider.provider_name] = AIProviderResult(
                        provider=provider.provider_name,
                        model_id=provider.model_id,
                        error=str(e),
                    )

    def _execute_provider(
        self,
        provider: AIProvider,
        summary: str,
        context: str,
    ) -> AIProviderResult:
        """単一プロバイダーの分析を実行し、AIProviderResultに変換。"""
        raw = provider.analyze(summary, context)

        if raw.get("error") or raw.get("parse_error"):
            return AIProviderResult(
                provider=provider.provider_name,
                model_id=provider.model_id,
                error=raw.get("error", "JSON parse error"),
                usage=provider.usage,
            )

        # dimension_scores の正規化
        dim_scores = raw.get("dimension_scores", {})

        # red_flags の変換
        red_flags: list[RedFlag] = []
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        for flag_data in raw.get("red_flags", []):
            if isinstance(flag_data, dict) and "title" in flag_data:
                red_flags.append(RedFlag(
                    category=f"ai_{provider.provider_name}",
                    title=flag_data.get("title", "Unknown"),
                    description=flag_data.get("description", ""),
                    severity=severity_map.get(
                        flag_data.get("severity", "medium"), Severity.MEDIUM
                    ),
                ))

        # コスト計算
        usage = provider.usage
        cost = estimate_provider_cost(
            provider.provider_name,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )

        return AIProviderResult(
            provider=provider.provider_name,
            model_id=provider.model_id,
            dimension_scores=dim_scores,
            red_flags=red_flags,
            verdict=raw.get("verdict", ""),
            confidence=raw.get("confidence", 0),
            executive_summary=raw.get("executive_summary", ""),
            usage=usage,
            cost_usd=cost,
        )

    # --- 従来の3段階パイプライン（後方互換） ---

    def _run_ai_analysis(self, result: AnalysisResult) -> dict[str, Any]:
        """従来の Haiku→Sonnet→Opus 3段階AI分析パイプラインを実行。"""
        findings: dict[str, Any] = {
            "haiku_scan": {},
            "sonnet_analysis": {},
            "opus_judgment": {},
        }

        summary = self._build_analysis_summary(result)

        logger.info("  Tier 1: Haiku scan...")
        findings["haiku_scan"] = self._haiku_scan(summary)

        logger.info("  Tier 2: Sonnet deep analysis...")
        findings["sonnet_analysis"] = self._sonnet_analyze(summary, findings["haiku_scan"])

        logger.info("  Tier 3: Opus final judgment...")
        findings["opus_judgment"] = self._opus_judge(summary, findings["sonnet_analysis"])

        return findings

    def _haiku_scan(self, summary: str) -> dict[str, Any]:
        """Tier 1: Haikuによる高速スキャン。"""
        model = MODELS["haiku"]

        prompt = f"""You are a technical due diligence scanner. Quickly classify this project
and identify obvious red flags.

PROJECT ANALYSIS SUMMARY:
{summary}

Respond in JSON format:
{{
  "project_type": "api_wrapper|genuine_product|framework|library|tool",
  "complexity_level": "trivial|simple|moderate|complex|enterprise",
  "immediate_red_flags": ["flag1", "flag2"],
  "areas_needing_deep_analysis": ["area1", "area2"],
  "initial_risk_level": "low|medium|high|critical"
}}"""

        try:
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=model.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage("haiku", response.usage)
            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Haiku scan failed: {e}")
            return {"error": str(e)}

    def _sonnet_analyze(self, summary: str, haiku_result: dict) -> dict[str, Any]:
        """Tier 2: Sonnetによる深層分析。"""
        model = MODELS["sonnet"]

        prompt = f"""You are a senior technical due diligence analyst. Perform a deep analysis
of this AI startup's technology.

PROJECT ANALYSIS SUMMARY:
{summary}

INITIAL SCAN RESULTS (from fast pass):
{json.dumps(haiku_result, indent=2)}

Analyze the following dimensions in detail:
1. Code Originality: Is this genuine IP or an API wrapper?
2. Technical Depth: Is the implementation sophisticated or superficial?
3. Engineering Maturity: CI/CD, tests, documentation, code quality
4. Claim Verification: Do documentation claims match code evidence?
5. Team Capability: What does the commit history reveal about the team?
6. Security Posture: Are there security concerns?

Respond in JSON format:
{{
  "dimensions": {{
    "code_originality": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "technical_depth": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "engineering_maturity": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "claim_verification": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "team_capability": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }},
    "security_posture": {{
      "score": 0-100,
      "rationale": "...",
      "evidence": ["..."]
    }}
  }},
  "additional_red_flags": [
    {{"title": "...", "description": "...", "severity": "critical|high|medium|low"}}
  ],
  "strengths": ["..."],
  "weaknesses": ["..."]
}}"""

        try:
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=model.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage("sonnet", response.usage)
            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Sonnet analysis failed: {e}")
            return {"error": str(e)}

    def _opus_judge(self, summary: str, sonnet_result: dict) -> dict[str, Any]:
        """Tier 3: Opusによる最終判定。"""
        model = MODELS["opus"]

        prompt = f"""You are the final arbiter in a technical due diligence process for an
AI startup investment. You must deliver a definitive verdict.

PROJECT SUMMARY:
{summary}

DETAILED ANALYSIS (from deep analysis pass):
{json.dumps(sonnet_result, indent=2)}

Deliver your final judgment:
1. Overall assessment: Is this a sound technical investment?
2. Deal-breaker analysis: Are there any findings that should block investment?
3. Specific conditions: What must be addressed before/after investment?
4. Comparable analysis: How does this compare to typical startups at this stage?

Respond in JSON format:
{{
  "verdict": "strong_invest|invest_with_conditions|cautious|pass|strong_pass",
  "confidence": 0-100,
  "executive_summary": "2-3 sentence summary for investment committee",
  "deal_breakers": ["..."],
  "conditions": ["..."],
  "strengths_to_leverage": ["..."],
  "risks_to_monitor": ["..."],
  "comparable_assessment": "..."
}}"""

        try:
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=model.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage("opus", response.usage)
            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Opus judgment failed: {e}")
            return {"error": str(e)}

    def _build_analysis_summary(self, result: AnalysisResult) -> str:
        """全分析結果のテキストサマリーを生成。"""
        lines = [
            f"Project: {result.project_name}",
            f"",
            f"=== CODE ANALYSIS ===",
            f"Total files: {result.code_analysis.total_files}",
            f"Total lines: {result.code_analysis.total_lines}",
            f"Languages: {result.code_analysis.languages}",
            f"API wrapper ratio: {result.code_analysis.api_wrapper_ratio:.1%}",
            f"Has tests: {result.code_analysis.has_tests}",
            f"Has CI/CD: {result.code_analysis.has_ci_cd}",
            f"Has docs: {result.code_analysis.has_documentation}",
            f"Dependencies: {result.code_analysis.dependency_count}",
            f"Code findings: {result.code_analysis.findings[:10]}",
            f"Code red flags: {len(result.code_analysis.red_flags)}",
            f"",
            f"=== DOCUMENT ANALYSIS ===",
            f"Total claims: {len(result.doc_analysis.claims)}",
            f"Performance claims: {len(result.doc_analysis.performance_claims)}",
            f"Architecture claims: {len(result.doc_analysis.architecture_claims)}",
            f"Technical claims: {len(result.doc_analysis.technical_claims)}",
            f"Doc red flags: {len(result.doc_analysis.red_flags)}",
            f"",
            f"=== GIT FORENSICS ===",
            f"Total commits: {result.git_forensics.total_commits}",
            f"Unique authors: {result.git_forensics.unique_authors}",
            f"First commit: {result.git_forensics.first_commit_date}",
            f"Last commit: {result.git_forensics.last_commit_date}",
            f"Rush commit ratio: {result.git_forensics.rush_commit_ratio:.1%}",
            f"Suspicious patterns: {result.git_forensics.suspicious_patterns}",
            f"Git red flags: {len(result.git_forensics.red_flags)}",
            f"",
            f"=== CONSISTENCY CHECK ===",
            f"Verified claims: {len(result.consistency.verified_claims)}",
            f"Unverified claims: {len(result.consistency.unverified_claims)}",
            f"Contradictions: {len(result.consistency.contradictions)}",
            f"Consistency score: {result.consistency.consistency_score:.1f}%",
            f"",
            f"=== RED FLAGS SUMMARY ===",
        ]

        all_flags = (
            result.code_analysis.red_flags
            + result.doc_analysis.red_flags
            + result.git_forensics.red_flags
            + result.consistency.red_flags
        )
        for flag in all_flags:
            lines.append(f"  [{flag.severity.value}] {flag.title}: {flag.description[:100]}")

        return "\n".join(lines)

    def _merge_ai_findings(
        self, result: AnalysisResult, ai_findings: dict[str, Any]
    ) -> None:
        """従来パイプラインのAI所見をマージ。"""
        sonnet = ai_findings.get("sonnet_analysis", {})

        for flag_data in sonnet.get("additional_red_flags", []):
            if isinstance(flag_data, dict) and "title" in flag_data:
                severity_map = {
                    "critical": Severity.CRITICAL,
                    "high": Severity.HIGH,
                    "medium": Severity.MEDIUM,
                    "low": Severity.LOW,
                }
                result.code_analysis.red_flags.append(
                    RedFlag(
                        category="ai_detected",
                        title=flag_data.get("title", "Unknown"),
                        description=flag_data.get("description", ""),
                        severity=severity_map.get(
                            flag_data.get("severity", "medium"), Severity.MEDIUM
                        ),
                    )
                )

    def _track_usage(self, tier: str, usage: Any) -> None:
        """トークン使用量を記録。"""
        if hasattr(usage, "input_tokens"):
            self._usage[tier]["input_tokens"] += usage.input_tokens
            self._usage[tier]["output_tokens"] += usage.output_tokens

    def _compute_total_cost(self, result: AnalysisResult) -> float:
        """全プロバイダーのAPI合計コストを計算。"""
        total = 0.0

        # 従来パイプラインのコスト
        for tier, tokens in self._usage.items():
            if tokens["input_tokens"] > 0 or tokens["output_tokens"] > 0:
                total += estimate_cost(
                    tier, tokens["input_tokens"], tokens["output_tokens"]
                )

        # マルチプロバイダーのコスト
        for ai_result in result.ai_results.values():
            total += ai_result.cost_usd

        return round(total, 4)


def _parse_json_response(text: str) -> dict[str, Any]:
    """AIの応答からJSON部分を抽出してパース。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"raw_response": text, "parse_error": True}
