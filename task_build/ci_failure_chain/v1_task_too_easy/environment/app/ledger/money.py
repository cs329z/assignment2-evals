"""Money helpers."""

from decimal import Decimal


def to_cents(amount: Decimal) -> int:
    """Convert an amount in major units to whole cents."""
    return int(amount * 100)
