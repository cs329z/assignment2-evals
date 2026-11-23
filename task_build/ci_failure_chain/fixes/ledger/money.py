"""Money helpers."""

from decimal import ROUND_HALF_UP, Decimal


def to_cents(amount: Decimal) -> int:
    """Convert an amount in major units to whole cents, ties away from zero."""
    return int((amount * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
