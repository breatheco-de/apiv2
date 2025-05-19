from typing import Dict, TypedDict


class PricingRatio(TypedDict):
    pricing_ratio: float
    currency: str


GENERAL_PRICING_RATIOS: Dict[str, PricingRatio] = {
    "ve": {"pricing_ratio": 0.8, "currency": "USD"},
    "mx": {"pricing_ratio": 1.0, "currency": "USD"},
    "us": {"pricing_ratio": 1.0, "currency": "USD"},
    "co": {"pricing_ratio": 0.9, "currency": "USD"},
    "cl": {"pricing_ratio": 0.95, "currency": "USD"},
    "ar": {"pricing_ratio": 0.7, "currency": "USD"},
    "pe": {"pricing_ratio": 0.85, "currency": "USD"},
    "ec": {"pricing_ratio": 0.8, "currency": "USD"},
    "do": {"pricing_ratio": 0.9, "currency": "USD"},
    "cr": {"pricing_ratio": 0.9, "currency": "USD"},
    "pa": {"pricing_ratio": 0.95, "currency": "USD"},
    "uy": {"pricing_ratio": 0.9, "currency": "USD"},
    "br": {"pricing_ratio": 1.0, "currency": "USD"},
    "es": {"pricing_ratio": 1.0, "currency": "EUR"},
}
