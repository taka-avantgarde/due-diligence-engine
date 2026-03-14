"""Stripe billing integration with 2x API cost pricing."""

from __future__ import annotations

import logging
from typing import Any

import stripe

from src.config import PRICING_TIERS, Config, estimate_cost

logger = logging.getLogger(__name__)


class BillingManager:
    """Manages Stripe billing with 2x API cost markup pricing.

    Pricing strategy:
    - Track actual API costs (input/output tokens per model tier)
    - Apply 2x multiplier as the SaaS margin
    - Create usage-based charges via Stripe metered billing
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        if config.stripe_api_key:
            stripe.api_key = config.stripe_api_key

    def compute_charge(
        self,
        model_usage: dict[str, dict[str, int]],
        tier: str = "starter",
    ) -> dict[str, Any]:
        """Compute the charge for an analysis run.

        Args:
            model_usage: Token usage per model tier.
                Example: {"haiku": {"input_tokens": 1000, "output_tokens": 500}, ...}
            tier: The user's pricing tier.

        Returns:
            Breakdown of costs and final charge.
        """
        pricing_tier = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])
        multiplier = pricing_tier.cost_multiplier

        breakdown: dict[str, dict[str, float]] = {}
        total_api_cost = 0.0

        for model_tier, tokens in model_usage.items():
            input_tokens = tokens.get("input_tokens", 0)
            output_tokens = tokens.get("output_tokens", 0)

            if input_tokens == 0 and output_tokens == 0:
                continue

            api_cost = estimate_cost(model_tier, input_tokens, output_tokens)
            total_api_cost += api_cost

            breakdown[model_tier] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "api_cost_usd": round(api_cost, 6),
                "charged_usd": round(api_cost * multiplier, 6),
            }

        total_charge = round(total_api_cost * multiplier, 4)

        # Minimum charge floor
        minimum_charge = 0.50  # 50 cents minimum per analysis
        final_charge = max(total_charge, minimum_charge)

        return {
            "breakdown": breakdown,
            "total_api_cost_usd": round(total_api_cost, 4),
            "multiplier": multiplier,
            "total_charge_usd": final_charge,
            "tier": tier,
            "minimum_applied": final_charge == minimum_charge,
        }

    async def create_usage_record(
        self,
        stripe_subscription_item_id: str,
        quantity_cents: int,
        analysis_id: str,
    ) -> dict[str, Any] | None:
        """Create a Stripe usage record for metered billing.

        Args:
            stripe_subscription_item_id: The Stripe subscription item ID.
            quantity_cents: Charge amount in cents.
            analysis_id: The analysis ID for idempotency.

        Returns:
            Stripe usage record or None on failure.
        """
        if not self._config.stripe_api_key:
            logger.warning("Stripe not configured. Skipping usage record.")
            return None

        try:
            record = stripe.SubscriptionItem.create_usage_record(
                stripe_subscription_item_id,
                quantity=quantity_cents,
                idempotency_key=f"dde_{analysis_id}",
            )
            logger.info(
                f"Created usage record: {quantity_cents} cents for analysis {analysis_id}"
            )
            return dict(record)
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating usage record: {e}")
            return None

    async def create_checkout_session(
        self,
        tier: str,
        success_url: str,
        cancel_url: str,
    ) -> str | None:
        """Create a Stripe Checkout session for new subscriptions.

        Args:
            tier: Pricing tier to subscribe to.
            success_url: URL to redirect on success.
            cancel_url: URL to redirect on cancel.

        Returns:
            Checkout session URL or None on failure.
        """
        if not self._config.stripe_api_key:
            logger.warning("Stripe not configured.")
            return None

        # Price IDs would be configured in Stripe Dashboard
        # These are placeholder mappings
        price_map = {
            "starter": "price_starter_monthly",
            "professional": "price_professional_monthly",
            "enterprise": "price_enterprise_monthly",
        }

        price_id = price_map.get(tier)
        if not price_id:
            logger.error(f"Unknown tier: {tier}")
            return None

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session.url
        except stripe.StripeError as e:
            logger.error(f"Stripe checkout error: {e}")
            return None

    def estimate_analysis_cost(
        self,
        file_count: int,
        total_lines: int,
        tier: str = "starter",
    ) -> dict[str, float]:
        """Estimate the cost of an analysis before running it.

        Args:
            file_count: Number of files to analyze.
            total_lines: Approximate total lines of code.
            tier: User's pricing tier.

        Returns:
            Estimated costs breakdown.
        """
        pricing_tier = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])

        # Rough token estimates based on file/line counts
        estimated_input_tokens = total_lines * 4  # ~4 tokens per line
        estimated_output_per_tier = {
            "haiku": min(estimated_input_tokens * 0.1, 4000),
            "sonnet": min(estimated_input_tokens * 0.3, 8000),
            "opus": min(estimated_input_tokens * 0.1, 4000),
        }

        total_api = 0.0
        for model_tier, output_est in estimated_output_per_tier.items():
            cost = estimate_cost(
                model_tier,
                int(estimated_input_tokens * 0.5),  # Not all input goes to every model
                int(output_est),
            )
            total_api += cost

        return {
            "estimated_api_cost_usd": round(total_api, 4),
            "estimated_charge_usd": round(
                max(total_api * pricing_tier.cost_multiplier, 0.50), 4
            ),
            "tier": tier,
            "multiplier": pricing_tier.cost_multiplier,
        }
