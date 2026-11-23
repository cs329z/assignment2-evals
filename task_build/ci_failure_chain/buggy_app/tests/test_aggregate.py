import unittest
from decimal import Decimal

from ledger.aggregate import build_report
from ledger.models import Transaction

RATES = {"USD": Decimal("1"), "EUR": Decimal("1.0850")}


def txn(txn_id, amount, currency="USD", account="ops", when="2024-01-15T09:00:00+00:00"):
    return Transaction.from_row(
        {
            "id": txn_id,
            "timestamp": when,
            "account": account,
            "currency": currency,
            "amount": amount,
            "description": f"desc {txn_id}",
        }
    )


class BuildReportTests(unittest.TestCase):
    def test_sums_per_account_and_month(self):
        report = build_report([txn("A", "10.00"), txn("B", "5.25")], RATES, "USD")
        self.assertEqual(report["accounts"]["ops"]["months"], {"2024-01": 1525})
        self.assertEqual(report["accounts"]["ops"]["total_cents"], 1525)

    def test_converts_currency(self):
        report = build_report([txn("A", "100.00", currency="EUR")], RATES, "USD")
        self.assertEqual(report["accounts"]["ops"]["total_cents"], 10850)

    def test_reports_largest_and_counts(self):
        report = build_report(
            [txn("A", "10.00"), txn("B", "99.00"), txn("C", "5.00")],
            RATES,
            "USD",
            duplicates_dropped=2,
        )
        self.assertEqual(report["accounts"]["ops"]["largest"]["id"], "B")
        self.assertEqual(report["transactions"], 3)
        self.assertEqual(report["duplicates_dropped"], 2)


if __name__ == "__main__":
    unittest.main()
