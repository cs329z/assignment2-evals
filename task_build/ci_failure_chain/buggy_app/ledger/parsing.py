"""Parsing helpers for ERP export rows."""

from datetime import datetime
from decimal import Decimal

from ledger.models import Transaction


def parse_amount(text: str) -> Decimal:
    """Parse an accounting-style amount such as ``1,234.50``."""
    return Decimal(text.strip().replace(",", ""))


def parse_timestamp(text: str) -> datetime:
    return datetime.fromisoformat(text.strip())


def parse_rows(rows, seen=set()):
    """Turn raw CSV rows into Transactions, dropping repeated ids."""
    transactions = []
    for row in rows:
        txn = Transaction.from_row(row)
        if txn.txn_id in seen:
            continue
        seen.add(txn.txn_id)
        transactions.append(txn)
    return transactions
