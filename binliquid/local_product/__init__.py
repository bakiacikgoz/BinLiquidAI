from __future__ import annotations

from binliquid.local_product.claim_guard import evaluate_platform_claims
from binliquid.local_product.platforms import detect_current_target, parse_target
from binliquid.local_product.readiness import evaluate_local_product_readiness

__all__ = [
    "detect_current_target",
    "evaluate_local_product_readiness",
    "evaluate_platform_claims",
    "parse_target",
]

