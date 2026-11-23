import unittest
from decimal import Decimal

from ledger.money import to_cents


class ToCentsTests(unittest.TestCase):
    def test_exact_amounts(self):
        self.assertEqual(to_cents(Decimal("19.99")), 1999)
        self.assertEqual(to_cents(Decimal("0")), 0)
        self.assertEqual(to_cents(Decimal("-3.50")), -350)

    def test_rounds_half_up(self):
        self.assertEqual(to_cents(Decimal("10.005")), 1001)
        self.assertEqual(to_cents(Decimal("10.004")), 1000)


if __name__ == "__main__":
    unittest.main()
