import unittest
from decimal import Decimal

from ledger.parsing import parse_amount, parse_rows


def row(txn_id, amount="10.00"):
    return {
        "id": txn_id,
        "timestamp": "2024-01-15T09:00:00+00:00",
        "account": "ops",
        "currency": "USD",
        "amount": amount,
        "description": "x",
    }


class ParseAmountTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_amount("10.50"), Decimal("10.50"))

    def test_thousands_separator(self):
        self.assertEqual(parse_amount("1,234.50"), Decimal("1234.50"))

    def test_minus_sign(self):
        self.assertEqual(parse_amount("-45.00"), Decimal("-45.00"))


class ParseRowsTests(unittest.TestCase):
    def test_drops_repeated_ids(self):
        rows = [row("T1"), row("T2"), row("T1")]
        self.assertEqual([t.txn_id for t in parse_rows(rows)], ["T1", "T2"])

    def test_keeps_distinct_ids(self):
        rows = [row("T1"), row("T3")]
        self.assertEqual(len(parse_rows(rows)), 2)


if __name__ == "__main__":
    unittest.main()
