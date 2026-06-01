"""Best-effort model pricing estimates.

Prices change over time. Keep this table as advisory only and prefer official
OpenAI pricing docs for billing decisions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


KNOWN_PRICING: dict[str, ModelPricing] = {
    "gpt-4.1-mini": ModelPricing(input_per_million=0.40, output_per_million=1.60),
    "gpt-4.1": ModelPricing(input_per_million=2.00, output_per_million=8.00),
}


def estimate_cost(model: str, input_tokens: int = 0, output_tokens: int = 0) -> float | None:
    pricing = KNOWN_PRICING.get(model)
    if pricing is None:
        return None
    return (
        input_tokens * pricing.input_per_million / 1_000_000
        + output_tokens * pricing.output_per_million / 1_000_000
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
