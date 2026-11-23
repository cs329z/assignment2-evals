"""Parsing helpers for ERP export rows."""

from datetime import datetime
from decimal import Decimal

from ledger.models import Transaction


def parse_amount(text: str) -> Decimal:
    """Parse an accounting-style amount: ``1,234.50``, ``-45.00`` or ``(45.00)``."""
    text = text.strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    value = Decimal(text.replace(",", "").strip())
    return -value if negative else value


def parse_timestamp(text: str) -> datetime:
    return datetime.fromisoformat(text.strip())


def parse_rows(rows):
    """Turn raw CSV rows of ONE export into Transactions, dropping repeated ids."""
    seen = set()
    transactions = []
    for row in rows:
        txn = Transaction.from_row(row)
        if txn.txn_id in seen:
            continue
        seen.add(txn.txn_id)
        transactions.append(txn)
    return transactions
