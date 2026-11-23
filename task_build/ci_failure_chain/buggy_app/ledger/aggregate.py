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
        if largest is None or cents > largest["amount_cents"]:
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
