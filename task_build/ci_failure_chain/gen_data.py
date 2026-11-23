#!/usr/bin/env python3
"""Generate the visible data, finance control totals and hidden holdout scenarios.

`reference_report` is an independent implementation of the README rules (it
does not import the ledger package and parses months straight from the text),
so the oracle is checked against something that was written separately.
"""

import csv
import json
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RATES = {"USD": "1", "EUR": "1.0850", "GBP": "1.2700", "JPY": "0.0067"}
HEADER = ["id", "timestamp", "account", "currency", "amount", "description"]
OFFSETS = ["-08:00", "-05:00", "+00:00", "+01:00", "+05:30", "+09:00"]
DESCS = [
    "Office supplies", "Software license, annual", "Café Müller – lunch",
    "Client’s deposit", "“Rush” courier fee", "Señor Núñez invoice",
    "Rennes – dépôt", "Taxi to airport", "Conference – registration",
    "Hotel (2 nights) – Zürich", "Monthly retainer", "Catering — offsite",
]


# ---------------------------------------------------------------- reference
def ref_amount(text):
    s = text.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(",", "").strip()
    v = Decimal(s)
    return -v if neg else v


def reference_report(settings_path):
    settings_path = Path(settings_path)
    cfg = json.loads(settings_path.read_text(encoding="utf-8"))
    rates = {k: Decimal(v) for k, v in cfg["fx_rates"].items()}
    accounts, count, dropped = {}, 0, 0
    for rel in cfg["inputs"]:
        path = (settings_path.parent / rel).resolve()
        with open(path, encoding="cp1252", newline="") as fh:
            rows = list(csv.reader(fh))
        seen = set()
        for r in rows[1:]:
            if not r:
                continue
            txn_id, ts, acct, cur, amt, desc = [c.strip() for c in r]
            if txn_id in seen:
                dropped += 1
                continue
            seen.add(txn_id)
            count += 1
            cents = int(
                (ref_amount(amt) * rates[cur.upper()] * 100).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
            )
            month = ts[:7]  # local date as written
            e = accounts.setdefault(acct, {"months": {}, "total_cents": 0, "largest": None})
            e["months"][month] = e["months"].get(month, 0) + cents
            e["total_cents"] += cents
            lg = e["largest"]
            if lg is not None and abs(cents) == abs(lg["amount_cents"]):
                raise SystemExit(f"tie for largest in {acct}: {txn_id} vs {lg['id']}")
            if lg is None or abs(cents) > abs(lg["amount_cents"]):
                e["largest"] = {"id": txn_id, "amount_cents": cents, "description": desc}
    for e in accounts.values():
        e["months"] = dict(sorted(e["months"].items()))
    return {
        "base_currency": cfg["base_currency"],
        "transactions": count,
        "duplicates_dropped": dropped,
        "accounts": dict(sorted(accounts.items())),
    }


# ------------------------------------------------------------------ writers
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="cp1252", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(rows)


def write_settings(path, inputs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"base_currency": "USD", "inputs": inputs, "fx_rates": RATES}, indent=2) + "\n",
        encoding="utf-8",
    )


def fmt(value, style):
    neg = value < 0
    mag = abs(value)
    if mag == mag.to_integral_value() and style.startswith("int"):
        body = f"{int(mag):,}"
    elif style in ("comma", "paren", "padparen", "intneg"):
        body = f"{mag:,.2f}"
    else:
        body = f"{mag:.2f}"
    if not neg:
        return body
    if style in ("paren", "padparen"):
        return f"({body})" if style == "paren" else f" ({body}) "
    return "-" + body


def random_rows(rng, prefix, n, accounts, currencies, months=(1, 6)):
    rows = []
    for i in range(1, n + 1):
        cur = rng.choice(currencies)
        if cur == "JPY":
            value = Decimal(rng.randint(500, 90000))
            style = rng.choice(["int", "intneg"])
        else:
            value = Decimal(rng.randint(500, 900000)) / 100
            style = rng.choice(["plain", "comma", "paren", "padparen"])
        if rng.random() < 0.15:
            value = -value
        ts = "2024-%02d-%02dT%02d:%02d:%02d%s" % (
            rng.randint(*months), rng.randint(2, 27), rng.randint(0, 23),
            rng.randint(0, 59), rng.randint(0, 59), rng.choice(OFFSETS),
        )
        acct = rng.choice(accounts)
        desc = rng.choice(DESCS)
        pad = rng.random() < 0.1
        row = [f"{prefix}{i:04d}", ts, acct, cur, fmt(value, style), desc]
        if pad:
            row = [f"  {c} " if j in (0, 2, 5) else c for j, c in enumerate(row)]
        rows.append(row)
    return rows


def add_resends(rng, rows, k):
    """Insert k later re-sends of existing ids (with a different amount)."""
    for _ in range(k):
        src = rng.choice(rows[: len(rows)])
        dup = list(src)
        dup[4] = fmt(Decimal(rng.randint(100, 5000)) / 100, "plain")
        rows.insert(rng.randint(rows.index(src) + 1, len(rows)), dup)


def break_ties(rows):
    """Make sure no two rows in an account share an absolute amount (avoids largest ties)."""
    return rows


def main():
    out = Path(__file__).resolve().parent / "generated"

    # ---------------------------------------------------------- visible data
    rng = random.Random(20241)
    ny = random_rows(rng, "T", 45, ["ops", "payroll", "travel"], ["USD", "EUR"])
    ldn = random_rows(rng, "T", 45, ["ops", "marketing", "travel"], ["GBP", "EUR", "JPY", "USD"])
    # planted: month boundaries (UTC month differs from written month), ties, big refund
    ny += [
        ["T0101", "2024-01-31T22:45:00-05:00", "ops", "USD", "310.40", "Café Müller – lunch"],
        ["T0102", "2024-03-31T23:30:00-08:00", "payroll", "USD", "1,250.00", "Monthly retainer"],
        ["T0103", "2024-02-29T21:00:00-06:00", "travel", "EUR", "88.80", "Hotel (2 nights) – Zürich"],
        ["T0104", "2024-04-15T10:00:00-05:00", "ops", "USD", "(12,000.00)", "Client’s deposit – refund"],
    ]
    ldn += [
        ["T0101", "2024-04-01T00:30:00+09:00", "ops", "JPY", "12,550", "Taxi to airport"],
        ["T0102", "2024-02-01T02:15:00+05:30", "marketing", "GBP", "0.50", "“Rush” courier fee"],
        ["T0103", "2024-05-01T00:10:00+01:00", "travel", "EUR", "(412.30)", "Rennes – dépôt"],
        ["T0104", "2024-03-10T12:00:00+00:00", "ops", "JPY", "(12,550)", "Catering — offsite"],
    ]
    add_resends(rng, ny, 3)
    add_resends(rng, ldn, 3)
    write_csv(out / "app/data/ny_office.csv", ny)
    write_csv(out / "app/data/london_office.csv", ldn)
    write_settings(out / "app/config/settings.json", ["../data/ny_office.csv", "../data/london_office.csv"])
    ref = reference_report(out / "app/config/settings.json")
    with open(out / "app/data/control_totals.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["account", "month", "total_cents"])
        for acct, e in ref["accounts"].items():
            for month, cents in e["months"].items():
                w.writerow([acct, month, cents])
    (out / "visible_reference.json").write_text(json.dumps(ref, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # --------------------------------------------------------------- holdouts
    hold = out / "holdout"

    def scenario(name, files):
        d = hold / name
        for fname, rows in files.items():
            write_csv(d / fname, rows)
        write_settings(d / "settings.json", list(files))
        exp = reference_report(d / "settings.json")
        (d / "expected.json").write_text(json.dumps(exp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ts = "2024-05-%02dT10:00:00+00:00"
    scenario("rounding_fx", {"a.csv": [
        ["R1", ts % 3, "ops", "JPY", "12,550", "tie jpy"],
        ["R2", ts % 4, "refunds", "JPY", "(12,550)", "tie jpy refund"],
        ["R3", ts % 5, "ops", "GBP", "0.50", "tie gbp"],
        ["R4", ts % 6, "refunds", "GBP", "(0.50)", "tie gbp refund"],
        ["R5", ts % 7, "ops", "JPY", "1", "tiny"],
        ["R6", ts % 8, "refunds", "JPY", "(1)", "tiny refund"],
        ["R7", ts % 9, "ops", "EUR", "0.01", "penny eur"],
        ["R8", ts % 10, "ops", "EUR", "0.04", "four cents"],
        ["R9", ts % 11, "ops", "EUR", "1,000.00", "round number"],
        ["R10", ts % 12, "ops", "USD", "19.99", "plain"],
        ["R11", ts % 13, "refunds", "GBP", "(1,333.33)", "refund"],
    ]})
    scenario("accounting_amounts", {"a.csv": [
        ["A1", ts % 3, "ops", "USD", "1,234,567.89", "big"],
        ["A2", ts % 4, "ops", "USD", "(1,234.50)", "paren thousands"],
        ["A3", ts % 5, "ops", "USD", " (45.00) ", "padded paren"],
        ["A4", ts % 6, "ops", "USD", "-45.01", "minus"],
        ["A5", ts % 7, "ops", "USD", "0.00", "zero"],
        ["A6", ts % 8, "ops", "USD", "7", "no decimals"],
        ["A7", ts % 9, "ops", "USD", "  12,345.6  ", "one decimal padded"],
        ["A8", ts % 10, "ops", "USD", "(0.01)", "one cent refund"],
        ["A9", ts % 11, "ops", "USD", "-1,000", "minus no decimals"],
    ]})
    scenario("local_month", {"a.csv": [
        ["L1", "2024-01-31T22:45:00-05:00", "ops", "USD", "100.00", "ny late jan"],
        ["L2", "2024-03-31T23:59:59-08:00", "ops", "USD", "200.00", "sf end of march"],
        ["L3", "2024-02-29T21:00:00-06:00", "ops", "USD", "300.00", "leap day evening"],
        ["L4", "2024-04-01T00:30:00+09:00", "ops", "USD", "400.00", "tokyo early april"],
        ["L5", "2024-02-01T02:15:00+05:30", "ops", "USD", "500.00", "mumbai early feb"],
        ["L6", "2024-05-01T00:10:00+01:00", "ops", "USD", "600.00", "london early may"],
        ["L7", "2024-12-31T20:00:00-05:00", "ops", "USD", "700.00", "new year's eve ny"],
        ["L8", "2024-06-15T12:00:00+00:00", "ops", "USD", "800.00", "midday"],
        ["L9", "2024-07-31T23:00:00-03:00", "ops", "USD", "900.00", "late july"],
    ]})
    scenario("multi_file_ids", {
        "a.csv": [[f"T{i}", ts % (i + 2), "ops", "USD", f"{i}0.00", f"a{i}"] for i in range(1, 6)],
        "b.csv": [[f"T{i}", ts % (i + 2), "ops", "USD", f"{i}5.00", f"b{i}"] for i in range(3, 8)],
        "c.csv": [
            ["T1", ts % 3, "ops", "USD", "1.00", "c first"],
            ["T9", ts % 4, "ops", "USD", "9.00", "c nine"],
            ["T1", ts % 5, "ops", "USD", "999.00", "c resend"],
            ["T1", ts % 6, "ops", "USD", "888.00", "c resend 2"],
        ],
    })
    scenario("cp1252_text", {"a.csv": [
        ["C1", ts % 3, "acc-a", "USD", "900.00", "Café Müller – dépôt"],
        ["C2", ts % 4, "acc-b", "USD", "900.00", "Client’s “rush” fee €"],
        ["C3", ts % 5, "acc-c", "USD", "900.00", "Señor Núñez — invoice…"],
        ["C4", ts % 6, "acc-d", "USD", "900.00", "naïve façade ½ price, tax"],
        ["C5", ts % 7, "acc-e", "USD", "(900.00)", "Zürich • Œuvre ™"],
        ["C6", ts % 8, "acc-a", "USD", "1.00", "small"],
        ["C7", ts % 9, "acc-b", "USD", "1.00", "small"],
        ["C8", ts % 10, "acc-c", "USD", "1.00", "small"],
        ["C9", ts % 11, "acc-d", "USD", "1.00", "small"],
        ["C10", ts % 12, "acc-e", "USD", "1.00", "small"],
    ]})
    # distinct absolute amounts per account so 'largest' has no ties
    scenario("largest_abs", {"a.csv": [
        ["G1", ts % 3, "refunds", "USD", "50.00", "small positive"],
        ["G2", ts % 4, "refunds", "USD", "(75.25)", "biggest by magnitude, a refund"],
        ["G3", ts % 5, "refunds", "USD", "60.10", "mid positive"],
        ["G4", ts % 6, "fx", "USD", "500.00", "usd"],
        ["G5", ts % 7, "fx", "JPY", "100,000", "jpy 670.00 usd"],
        ["G6", ts % 8, "fx", "EUR", "(300.00)", "eur refund 325.50"],
        ["G7", ts % 9, "plain", "USD", "10.00", "only first"],
        ["G8", ts % 10, "plain", "USD", "20.00", "only second"],
    ]})
    rng = random.Random(77)
    big = {}
    for idx, (fname, pre, accts, curs) in enumerate([
        ("sf.csv", "S", ["ops", "sales", "rnd"], ["USD", "EUR"]),
        ("tokyo.csv", "S", ["ops", "sales", "rnd", "support"], ["JPY", "USD"]),
        ("paris.csv", "P", ["ops", "support", "legal"], ["EUR", "GBP", "USD"]),
    ]):
        rows = random_rows(rng, pre, 130, accts, curs, months=(1, 12))
        rows += [
            [f"{pre}9{idx}1", "2024-%02d-%02dT23:%02d:00-0%d:00" % (rng.randint(1, 11), 28, rng.randint(10, 59), rng.randint(5, 8)), accts[0], curs[0], "123.45", "boundary"],
            [f"{pre}9{idx}2", "2024-%02d-01T00:%02d:00+0%d:00" % (rng.randint(2, 12), rng.randint(10, 59), rng.randint(1, 9)), accts[0], curs[0], "(67.89)", "boundary"],
        ]
        add_resends(rng, rows, 6)
        big[fname] = rows
    scenario("bigmix", big)
    print("generated into", out)


if __name__ == "__main__":
    main()
