"""AIプロバイダー抽象化レイヤー。

Claude / Gemini / ChatGPT の3社を統一インターフェースで呼び出し、
各社独立した分析結果を返す。投資家が各自契約しているAPIキー（BYOK）を
使用し、最大3社同時にクロス検証を行う。
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

# --- 6軸分析プロンプトテンプレート ---
_ANALYSIS_PROMPT = """You are a senior technical due diligence analyst evaluating an AI startup
for investment. Analyze the following project summary and provide scores for each dimension.

PROJECT ANALYSIS SUMMARY:
{summary}

ADDITIONAL CONTEXT (from local analysis):
{context}

Score the following 6 dimensions (0-100 scale) with rationale and evidence:
1. Technical Originality: Is this genuine IP or an API wrapper?
2. Technology Advancement: How cutting-edge is the technology?
3. Implementation Depth: Is the implementation production-grade?
4. Architecture Quality: Is the architecture scalable and well-designed?
5. Claim Consistency: Do documentation claims match code evidence?
6. Security Posture: Are there security concerns?

Also provide:
- An executive summary (2-3 sentences for investment committee)
- A verdict: "strong_invest", "invest_with_conditions", "cautious", "pass", or "strong_pass"
- A confidence score (0-100)
- A list of red flags with severity (critical, high, medium, low)

Respond in JSON format:
{{
  "dimension_scores": {{
    "technical_originality": 0-100,
    "technology_advancement": 0-100,
    "implementation_depth": 0-100,
    "architecture_quality": 0-100,
    "claim_consistency": 0-100,
    "security_posture": 0-100
  }},
  "red_flags": [
    {{"title": "...", "description": "...", "severity": "critical|high|medium|low"}}
  ],
  "verdict": "...",
  "confidence": 0-100,
  "executive_summary": "..."
}}"""


class AIProvider(ABC):
    """AIプロバイダーの基底クラス。

    各プロバイダー（Claude, Gemini, ChatGPT）はこのクラスを継承し、
    統一された analyze() メソッドで分析結果を返す。
    """

    def __init__(self, api_key: str, model_id: str) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._input_tokens = 0
        self._output_tokens = 0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダー名（"claude", "gemini", "chatgpt"）を返す。"""
        ...

    @abstractmethod
    def analyze(self, summary: str, context: str) -> dict[str, Any]:
        """分析を実行し、結果をdictで返す。

        Args:
            summary: プロジェクトの分析サマリー（コード/ドキュメント/Git情報）。
            context: ローカル分析結果の追加コンテキスト。

        Returns:
            dimension_scores, red_flags, verdict, confidence,
            executive_summary を含むdict。
        """
        ...

    @property
    def usage(self) -> dict[str, int]:
        """トークン使用量を返す。"""
        return {"input_tokens": self._input_tokens, "output_tokens": self._output_tokens}

    @property
    def model_id(self) -> str:
        return self._model_id

    def _build_prompt(self, summary: str, context: str) -> str:
        """共通の分析プロンプトを生成。"""
        return _ANALYSIS_PROMPT.format(summary=summary, context=context)


class AnthropicProvider(AIProvider):
    """Anthropic Claude プロバイダー。

    既存のHaiku→Sonnet→Opus 3段階パイプラインを単一の高品質モデル呼び出しに
    ラップし、統一インターフェースで結果を返す。
    """

    @property
    def provider_name(self) -> str:
        return "claude"

    def analyze(self, summary: str, context: str) -> dict[str, Any]:
        """Claude APIで分析を実行。"""
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        prompt = self._build_prompt(summary, context)

        try:
            response = client.messages.create(
                model=self._model_id,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            if hasattr(response.usage, "input_tokens"):
                self._input_tokens += response.usage.input_tokens
                self._output_tokens += response.usage.output_tokens

            return _parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {"error": str(e)}


class GoogleProvider(AIProvider):
    """Google Gemini プロバイダー。

    google-generativeai SDK を使用してGemini APIで分析を実行。
    """

    @property
    def provider_name(self) -> str:
        return "gemini"

    def analyze(self, summary: str, context: str) -> dict[str, Any]:
        """Gemini APIで分析を実行。"""
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model_id)
        prompt = self._build_prompt(summary, context)

        try:
            response = model.generate_content(prompt)

            # トークン使用量の追跡
            if hasattr(response, "usage_metadata"):
                meta = response.usage_metadata
                self._input_tokens += getattr(meta, "prompt_token_count", 0)
                self._output_tokens += getattr(meta, "candidates_token_count", 0)

            return _parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return {"error": str(e)}


class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT プロバイダー。

    openai SDK を使用してChatGPT APIで分析を実行。
    """

    @property
    def provider_name(self) -> str:
        return "chatgpt"

    def analyze(self, summary: str, context: str) -> dict[str, Any]:
        """ChatGPT APIで分析を実行。"""
        import openai

        client = openai.OpenAI(api_key=self._api_key)
        prompt = self._build_prompt(summary, context)

        try:
            response = client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": "You are a senior technical due diligence analyst. Always respond in valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8192,
                temperature=0.1,
            )

            # トークン使用量の追跡
            if response.usage:
                self._input_tokens += response.usage.prompt_tokens
                self._output_tokens += response.usage.completion_tokens

            content = response.choices[0].message.content or ""
            return _parse_json_response(content)
        except Exception as e:
            logger.error(f"ChatGPT analysis failed: {e}")
            return {"error": str(e)}


# --- プロバイダーファクトリ ---

# デフォルトモデルID定義
_DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",
    "chatgpt": "gpt-4o",
}

# コスト定義 (USD per million tokens)
PROVIDER_COSTS: dict[str, dict[str, float]] = {
    "claude": {"input": 3.00, "output": 15.00},
    "gemini": {"input": 0.10, "output": 0.40},
    "chatgpt": {"input": 2.50, "output": 10.00},
}


def create_provider(provider_name: str, api_key: str, model_id: str | None = None) -> AIProvider:
    """プロバイダー名とAPIキーからAIProviderインスタンスを生成。

    Args:
        provider_name: "claude", "gemini", "chatgpt" のいずれか。
        api_key: 各社のAPIキー。
        model_id: 使用するモデルID（省略時はデフォルト）。

    Returns:
        対応するAIProviderインスタンス。

    Raises:
        ValueError: 未知のプロバイダー名の場合。
    """
    model = model_id or _DEFAULT_MODELS.get(provider_name, "")

    if provider_name == "claude":
        return AnthropicProvider(api_key=api_key, model_id=model)
    elif provider_name == "gemini":
        return GoogleProvider(api_key=api_key, model_id=model)
    elif provider_name == "chatgpt":
        return OpenAIProvider(api_key=api_key, model_id=model)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'claude', 'gemini', or 'chatgpt'.")


def estimate_provider_cost(provider_name: str, input_tokens: int, output_tokens: int) -> float:
    """プロバイダーのAPI使用コストを推定。

    Args:
        provider_name: "claude", "gemini", "chatgpt" のいずれか。
        input_tokens: 入力トークン数。
        output_tokens: 出力トークン数。

    Returns:
        推定コスト（USD）。
    """
    costs = PROVIDER_COSTS.get(provider_name, {"input": 0, "output": 0})
    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]
    return round(input_cost + output_cost, 6)


def _parse_json_response(text: str) -> dict[str, Any]:
    """AI応答からJSON部分を抽出してパース。

    マークダウンコードブロックの除去にも対応。
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
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
