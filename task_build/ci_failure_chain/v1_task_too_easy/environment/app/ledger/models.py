"""Core data types."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from ledger.parsing import parse_amount, parse_timestamp


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
        """Calendar month (YYYY-MM) the transaction is booked in."""
        return self.occurred_at.astimezone(timezone.utc).strftime("%Y-%m")

    @classmethod
    def from_row(cls, row):
        return cls(
            txn_id=row["id"].strip(),
            occurred_at=parse_timestamp(row["timestamp"]),
            account=row["account"].strip(),
            currency=row["currency"].strip().upper(),
            amount=parse_amount(row["amount"]),
            description=row["description"].strip(),
        )
