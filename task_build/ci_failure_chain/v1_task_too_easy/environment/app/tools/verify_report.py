"""Reconcile a built report against finance's control totals.

Usage: python tools/verify_report.py dist/report.json
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROL = os.path.join(HERE, "..", "data", "control_totals.csv")


def cents(value):
    return "missing" if value is None else f"{value / 100:,.2f}"


def main(report_path):
    with open(report_path, encoding="utf-8") as handle:
        report = json.load(handle)
    with open(CONTROL, newline="", encoding="utf-8") as handle:
        controls = list(csv.DictReader(handle))

    problems = []
    for key in ("base_currency", "transactions", "duplicates_dropped", "accounts"):
        if key not in report:
            problems.append(f"report is missing top-level key {key!r}")
    accounts = report.get("accounts", {})

    expected = {}
    for row in controls:
        expected[(row["account"], row["month"])] = int(row["total_cents"])
    for (account, month), want in sorted(expected.items()):
        got = accounts.get(account, {}).get("months", {}).get(month)
        if got != want:
            problems.append(
                f"{account} {month}: report has {cents(got)}, finance control total is {cents(want)}"
            )
    for account, entry in sorted(accounts.items()):
        for month in entry.get("months", {}):
            if (account, month) not in expected:
                problems.append(f"{account} {month}: report has a month finance has no control total for")
        if entry.get("total_cents") != sum(entry.get("months", {}).values()):
            problems.append(f"{account}: total_cents does not equal the sum of its months")

    if problems:
        print("RECONCILIATION FAILED")
        for problem in problems:
            print("  -", problem)
        return 1
    print(f"reconciled {len(expected)} account-months")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
