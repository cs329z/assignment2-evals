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
