#!/bin/bash
set -euo pipefail

cat > /app/ledger/aggregate.py <<'__LEDGER_EOF__'
"""Aggregation of transactions into the monthly report."""

from ledger.money import to_cents


def build_report(transactions, rates, base_currency, duplicates_dropped=0):
    accounts = {}
    for txn in transactions:
        cents = to_cents(txn.amount * rates[txn.currency])
        entry = accounts.setdefault(
            txn.account, {"months": {}, "total_cents": 0, "largest": None}
        )
        entry["months"][txn.month] = entry["months"].get(txn.month, 0) + cents
        entry["total_cents"] += cents
        largest = entry["largest"]
        if largest is None or abs(cents) > abs(largest["amount_cents"]):
            entry["largest"] = {
                "id": txn.txn_id,
                "amount_cents": cents,
                "description": txn.description,
            }
    for entry in accounts.values():
        entry["months"] = dict(sorted(entry["months"].items()))
    return {
        "base_currency": base_currency,
        "transactions": len(transactions),
        "duplicates_dropped": duplicates_dropped,
        "accounts": dict(sorted(accounts.items())),
    }
__LEDGER_EOF__

cat > /app/ledger/cli.py <<'__LEDGER_EOF__'
"""Command line entry point."""

import argparse
import csv
import json
import os

from ledger.aggregate import build_report
from ledger.config import load_settings
from ledger.parsing import parse_rows


def read_export(path):
    with open(path, newline="", encoding="cp1252") as handle:
        return list(csv.DictReader(handle))


def build(config_path, out_path):
    settings = load_settings(config_path)
    transactions = []
    dropped = 0
    for path in settings.inputs:
        rows = read_export(path)
        parsed = parse_rows(rows)
        dropped += len(rows) - len(parsed)
        transactions.extend(parsed)
    report = build_report(
        transactions, settings.fx_rates, settings.base_currency, dropped
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="build the monthly report")
    build_cmd.add_argument("--config", required=True)
    build_cmd.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.config, args.out)


if __name__ == "__main__":
    main()
__LEDGER_EOF__

cat > /app/ledger/models.py <<'__LEDGER_EOF__'
"""Core data types."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    occurred_at: datetime
    account: str
    currency: str
    amount: Decimal
    description: str

    @property
    def month(self) -> str:
        """Calendar month (YYYY-MM) the transaction is booked in.

        Uses the date as written in the export (the booking office's local
        time), not the UTC date.
        """
        return self.occurred_at.strftime("%Y-%m")

    @classmethod
    def from_row(cls, row):
        # Imported lazily: parsing imports this module at import time.
        from ledger.parsing import parse_amount, parse_timestamp

        return cls(
            txn_id=row["id"].strip(),
            occurred_at=parse_timestamp(row["timestamp"]),
            account=row["account"].strip(),
            currency=row["currency"].strip().upper(),
            amount=parse_amount(row["amount"]),
            description=row["description"].strip(),
        )
__LEDGER_EOF__

cat > /app/ledger/money.py <<'__LEDGER_EOF__'
"""Money helpers."""

from decimal import ROUND_HALF_UP, Decimal


def to_cents(amount: Decimal) -> int:
    """Convert an amount in major units to whole cents, ties away from zero."""
    return int((amount * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
__LEDGER_EOF__

cat > /app/ledger/parsing.py <<'__LEDGER_EOF__'
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
__LEDGER_EOF__
