"""Configuration management for the Due Diligence Engine."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a single Claude model tier."""

    model_id: str
    purpose: str
    input_cost_per_mtok: float  # USD per million input tokens
    output_cost_per_mtok: float  # USD per million output tokens
    max_tokens: int = 4096


# Pricing as of 2026-03 (illustrative; update as Anthropic changes pricing)
MODELS = {
    "haiku": ModelConfig(
        model_id="claude-haiku-4-5-20250315",
        purpose="scan",
        input_cost_per_mtok=0.80,
        output_cost_per_mtok=4.00,
        max_tokens=4096,
    ),
    "sonnet": ModelConfig(
        model_id="claude-sonnet-4-20250514",
        purpose="analyze",
        input_cost_per_mtok=3.00,
        output_cost_per_mtok=15.00,
        max_tokens=8192,
    ),
    "opus": ModelConfig(
        model_id="claude-opus-4-20250514",
        purpose="judge",
        input_cost_per_mtok=15.00,
        output_cost_per_mtok=75.00,
        max_tokens=4096,
    ),
}


@dataclass
class PricingTier:
    """SaaS pricing tier."""

    name: str
    cost_multiplier: float  # multiplier on top of API cost
    max_repos_per_month: int
    max_file_size_mb: int
    features: list[str] = field(default_factory=list)


# ============================================================
# Two monetization models:
#
# 1. BYOK (Bring Your Own Key) — FREE
#    User provides their own ANTHROPIC_API_KEY.
#    They pay Anthropic directly. DDE is free to use.
#    Best for: technical VCs, engineers who can set up API keys.
#
# 2. SaaS (Managed API) — 2x markup on API cost
#    User doesn't need an API key. We handle everything.
#    We charge 2x the actual API cost via Stripe.
#    Best for: non-technical VCs who want "just paste URL".
# ============================================================

PRICING_TIERS: dict[str, PricingTier] = {
    "byok": PricingTier(
        name="BYOK (自社APIキー)",
        cost_multiplier=0.0,  # Free — user pays Anthropic directly
        max_repos_per_month=999,
        max_file_size_mb=500,
        features=[
            "basic_report", "score", "slides", "pdf",
            "git_forensics", "tech_level_rating", "purge_certificate",
        ],
    ),
    "starter": PricingTier(
        name="Starter SaaS",
        cost_multiplier=2.0,
        max_repos_per_month=5,
        max_file_size_mb=50,
        features=["basic_report", "score", "tech_level_rating"],
    ),
    "professional": PricingTier(
        name="Professional SaaS",
        cost_multiplier=2.0,
        max_repos_per_month=25,
        max_file_size_mb=200,
        features=[
            "basic_report", "score", "slides", "pdf",
            "git_forensics", "tech_level_rating",
        ],
    ),
    "enterprise": PricingTier(
        name="Enterprise SaaS",
        cost_multiplier=2.0,
        max_repos_per_month=999,
        max_file_size_mb=500,
        features=[
            "basic_report", "score", "slides", "pdf",
            "git_forensics", "tech_level_rating",
            "purge_certificate", "priority_support",
            "custom_evaluation_framework",
        ],
    ),
}


# ============================================================
# チケット制料金体系（JPY・日本市場向け）
# ============================================================

TICKET_TIERS: dict[str, dict] = {
    "single": {
        "name": "1 Report",
        "name_ja": "1件",
        "price_jpy": 3000,
        "tickets": 1,
        "unit_price": 3000,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_SINGLE", ""),
        "account_required": False,
    },
    "pack_10": {
        "name": "10 Reports",
        "name_ja": "10件パック",
        "price_jpy": 28000,
        "tickets": 10,
        "unit_price": 2800,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PACK_10", ""),
        "account_required": True,
    },
    "pack_50": {
        "name": "50 Reports",
        "name_ja": "50件パック",
        "price_jpy": 120000,
        "tickets": 50,
        "unit_price": 2400,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PACK_50", ""),
        "account_required": True,
    },
    "pack_100": {
        "name": "100 Reports",
        "name_ja": "100件パック",
        "price_jpy": 220000,
        "tickets": 100,
        "unit_price": 2200,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PACK_100", ""),
        "account_required": True,
    },
}

# レポートTTL（日数）
REPORT_TTL_DAYS = 90


@dataclass
class Config:
    """Application-wide configuration."""

    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    openai_api_key: str = ""
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    saas_host: str = "0.0.0.0"
    saas_port: int = 8000
    data_dir: Path = field(default_factory=lambda: Path.home() / ".dde")
    temp_dir: Path = field(default_factory=lambda: Path.home() / ".dde" / "tmp")
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "dde_output")
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            google_ai_api_key=os.environ.get("GOOGLE_AI_API_KEY", ""),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            stripe_api_key=os.environ.get("STRIPE_API_KEY", ""),
            stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
            saas_host=os.environ.get("DDE_HOST", "0.0.0.0"),
            saas_port=int(os.environ.get("DDE_PORT", "8000")),
            data_dir=Path(os.environ.get("DDE_DATA_DIR", str(Path.home() / ".dde"))),
            log_level=os.environ.get("DDE_LOG_LEVEL", "INFO"),
        )

    def get_ai_api_keys(self) -> dict[str, str]:
        """環境変数から設定されたAI APIキーをdict形式で返す。

        Returns:
            {"claude": "sk-...", "gemini": "...", "chatgpt": "sk-..."} 形式。
            キーが未設定のプロバイダーは含まれない。
        """
        keys: dict[str, str] = {}
        if self.anthropic_api_key:
            keys["claude"] = self.anthropic_api_key
        if self.google_ai_api_key:
            keys["gemini"] = self.google_ai_api_key
        if self.openai_api_key:
            keys["chatgpt"] = self.openai_api_key
        return keys

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors: list[str] = []
        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is not set")
        return errors


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config.from_env()


def estimate_cost(
    model_tier: str,
    input_tokens: int,
    output_tokens: int,
    saas_multiplier: float = 1.0,
) -> float:
    """Estimate API cost for a given model and token count.

    Args:
        model_tier: One of 'haiku', 'sonnet', 'opus'.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        saas_multiplier: SaaS markup multiplier (default 1.0 for CLI).

    Returns:
        Estimated cost in USD.
    """
    model = MODELS.get(model_tier)
    if not model:
        raise ValueError(f"Unknown model tier: {model_tier}")

    input_cost = (input_tokens / 1_000_000) * model.input_cost_per_mtok
    output_cost = (output_tokens / 1_000_000) * model.output_cost_per_mtok
    return (input_cost + output_cost) * saas_multiplier
