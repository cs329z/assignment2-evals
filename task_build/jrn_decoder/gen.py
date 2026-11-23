#!/usr/bin/env python3
"""Ground-truth generator for the jrn-format-decoder task.

Records are generated first, then ENCODED into the legacy .jrn layout, and the expected JSON is
derived from the same records. So the expected answers never depend on any decoder.

.jrn layout (never shown to the agent):
  0   4  magic  b"JRN\\x01"
  4   2  u16 big-endian   record count
  6   4  u32 big-endian   base timestamp (unix seconds)
  10  3  ASCII            default currency
  13  1  u8               number of accounts N
  14  .. N x (u8 length, UTF-8 name)
  ..     records:
         u8 flags  bit0 literal memo follows | bit1 negative | bit2 explicit currency follows | bit3 pending
                   bit4 memo is a BACK-REFERENCE (varint index into the table of distinct memos seen so far,
                        in order of first literal appearance; bit0 is then clear)
         LEB128 varint   seconds since previous record (first record: since base)
         u8              account index
         LEB128 varint   amount magnitude in minor units
         [3 bytes ASCII currency]            if bit2
         [LEB128 memo byte length, memo]     if bit0   (memo = UTF-8 XOR 0x5A; adds it to the memo table)
         [LEB128 memo table index]           if bit4
  last 4 : u32 LITTLE-endian  zlib.crc32 of bytes[4:-4]
Minor-unit exponent: JPY 0, KWD 3, everything else 2.
"""
import json
import random
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

XOR = 0x5A
EXP = {"JPY": 0, "KWD": 3}
ACCOUNTS = ["ops", "payroll", "travel", "marketing", "Café Müller", "rnd", "sales", "support",
            "legal", "facilities", "IT", "Ünïcode Ltd", "fx", "treasury", "audit", "hr"]
MEMOS = ["Taxi to airport", "Café Müller – lunch", "Client’s deposit", "Monthly retainer",
         "Zürich 🏨 hotel", "出張費", "Invoice #4021, net 30", "Refund: order 77", "Catering — offsite", ""]
CURS = ["USD", "EUR", "GBP", "JPY", "KWD", "CHF", "SGD"]


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def encode(spec):
    recs, accts, default, base = spec["records"], spec["accounts"], spec["default"], spec["base"]
    body = bytearray()
    body += struct.pack(">H", len(recs)) + struct.pack(">I", base) + default.encode("ascii")
    body.append(len(accts))
    for a in accts:
        b = a.encode("utf-8")
        assert len(b) < 256
        body.append(len(b))
        body += b
    prev = base
    table = {}
    for r in recs:
        flags = 0
        memo = r["memo"]
        if memo is not None:
            flags |= 16 if memo in table else 1
        if r["amount"] < 0:
            flags |= 2
        if r["currency"] != default or r.get("explicit"):
            flags |= 4
        if r["pending"]:
            flags |= 8
        body.append(flags)
        body += varint(r["ts"] - prev)
        prev = r["ts"]
        body.append(r["acct"])
        body += varint(abs(r["amount"]))
        if flags & 4:
            body += r["currency"].encode("ascii")
        if flags & 16:
            body += varint(table[memo])
        elif flags & 1:
            m = memo.encode("utf-8")
            body += varint(len(m)) + bytes(x ^ XOR for x in m)
            table[memo] = len(table)
    crc = zlib.crc32(bytes(body)) & 0xFFFFFFFF
    return b"JRN\x01" + bytes(body) + struct.pack("<I", crc)


def fmt_amount(minor, cur):
    e = EXP.get(cur, 2)
    sign = "-" if minor < 0 else ""
    mag = abs(minor)
    return f"{sign}{mag}" if e == 0 else f"{sign}{mag // 10**e}.{mag % 10**e:0{e}d}"


def expected(spec):
    return {
        "default_currency": spec["default"],
        "accounts": spec["accounts"],
        "records": [
            {
                "index": i,
                "timestamp": datetime.fromtimestamp(r["ts"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "account": spec["accounts"][r["acct"]],
                "amount": fmt_amount(r["amount"], r["currency"]),
                "currency": r["currency"],
                "memo": r["memo"],
                "status": "pending" if r["pending"] else "posted",
            }
            for i, r in enumerate(spec["records"])
        ],
    }


def rand_spec(rng, n, accounts, default="USD", curs=("USD",), base=None, max_gap=600,
              max_amt=500000, memo_p=0.6, pending_p=0.15, neg_p=0.25, explicit_p=0.1, memos=MEMOS):
    base = base if base is not None else rng.randint(1_600_000_000, 1_750_000_000)
    ts = base
    recs = []
    for _ in range(n):
        ts += rng.randint(0, max_gap)
        recs.append({
            "ts": ts,
            "acct": rng.randrange(len(accounts)),
            "amount": rng.randint(0, max_amt) * (-1 if rng.random() < neg_p else 1),
            "currency": rng.choice(curs),
            "memo": rng.choice(memos) if rng.random() < memo_p else None,
            "pending": rng.random() < pending_p,
            "explicit": rng.random() < explicit_p,
        })
    return {"default": default, "accounts": list(accounts), "base": base, "records": recs}


def write(spec, path_no_ext, expected_json=True):
    p = Path(path_no_ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.with_suffix(".jrn").write_bytes(encode(spec))
    if expected_json:
        p.with_suffix(".json").write_text(json.dumps(expected(spec), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    out = Path(__file__).resolve().parent / "generated"
    rng = random.Random(1999)

    # ----------------------------------------------------------------- samples (agent sees these + .json)
    s = out / "samples"
    write(rand_spec(rng, 6, ACCOUNTS[:3], memos=["Taxi to airport", "Monthly retainer", "Office supplies"],
                    pending_p=0, neg_p=0, explicit_p=0, memo_p=0.8), s / "s01_basic")
    write(rand_spec(rng, 14, ACCOUNTS[:4], neg_p=0.5, pending_p=0.4, memos=["Refund: order 77", "Taxi to airport"],
                    explicit_p=0), s / "s02_neg_pending")
    write(rand_spec(rng, 24, ACCOUNTS[:5], default="EUR", curs=("EUR", "USD", "GBP", "JPY", "KWD"),
                    explicit_p=0, max_amt=900000), s / "s03_multicurrency")
    big_accts = [f"acct-{i:03d}" for i in range(150)]
    sp = rand_spec(rng, 20, big_accts, max_gap=400000, max_amt=2_000_000_000, curs=("USD", "JPY"))
    sp["records"][3]["acct"] = 149
    sp["records"][4]["acct"] = 128
    write(sp, s / "s04_varints")
    sp = rand_spec(rng, 8, ACCOUNTS[:3], memo_p=1.0)
    sp["records"][0]["memo"] = "x" * 300 + " – long memo ✓"
    sp["records"][1]["memo"] = ""
    sp["records"][2]["memo"] = "Zürich 🏨 出張費"
    sp["records"][3]["memo"] = ""
    sp["records"][4]["memo"] = sp["records"][0]["memo"]
    sp["records"][5]["memo"] = ""
    write(sp, s / "s05_memos")
    write({"default": "USD", "accounts": ["ops", "payroll"], "base": 1_700_000_000, "records": []}, s / "s06_empty")
    write(rand_spec(rng, 12, ACCOUNTS[:4], default="GBP", curs=("GBP", "USD"), explicit_p=0.6), s / "s07_explicit_default")
    write(rand_spec(rng, 40, ACCOUNTS, curs=CURS, max_gap=90000, max_amt=10_000_000), s / "s08_mixed")

    sp = rand_spec(rng, 200, ACCOUNTS[:6], curs=("USD", "EUR"), memo_p=1.0)
    for i, rec in enumerate(sp["records"][:160]):
        rec["memo"] = f"memo-{i:04d}"
    for rec in sp["records"][160:]:
        rec["memo"] = f"memo-{rng.randrange(160):04d}"
    write(sp, s / "s09_many_memos")

    # ---------------------------------------------------------------- hidden holdout
    h = out / "holdout"
    for i in range(1, 9):
        r = random.Random(500 + i)
        write(rand_spec(r, r.randint(5, 120), r.sample(ACCOUNTS, r.randint(2, 12)),
                        default=r.choice(["USD", "EUR", "JPY", "KWD"]), curs=tuple(r.sample(CURS, 4)),
                        max_gap=r.choice([60, 5000, 400000]), max_amt=r.choice([5000, 10**7, 10**12]),
                        explicit_p=0.3), h / f"h{i:02d}_random")
    r = random.Random(900)
    write(rand_spec(r, 300, ACCOUNTS, curs=CURS, max_gap=3_000_000, max_amt=10**13, explicit_p=0.2), h / "h09_big_300")
    sp = rand_spec(r, 4, ACCOUNTS[:3], memo_p=1.0)
    sp["records"][1]["memo"] = "long " * 4000 + "é"      # ~20k bytes -> 3-byte length varint
    sp["records"][2]["memo"] = "ü" * 9000                # 2-byte chars
    write(sp, h / "h10_long_memos")
    write({"default": "KWD", "accounts": ["only"], "base": 1_720_000_000, "records": []}, h / "h11_empty")
    write(rand_spec(r, 1, ["solo"], curs=("JPY",), explicit_p=1.0), h / "h12_single_explicit")
    r2 = random.Random(901)
    sp = rand_spec(r2, 60, [f"a{i}" for i in range(255)], curs=CURS, explicit_p=0.3)
    for rec in sp["records"][:10]:
        rec["acct"] = r2.randint(128, 254)
    write(sp, h / "h13_many_accounts")
    r3 = random.Random(903)
    pool = [f"m{i}-{'é' * (i % 5)}-{'x' * (i % 40)}" for i in range(300)] + ["", "Zürich 🏨"]
    sp = rand_spec(r3, 500, ACCOUNTS, curs=CURS, memo_p=0.9, memos=pool, explicit_p=0.2)
    write(sp, h / "h16_memo_references")
    # corrupt files: expect exit code 2 and no stdout
    good = encode(rand_spec(random.Random(902), 25, ACCOUNTS[:5], curs=CURS))
    bad_crc = bytearray(good)
    bad_crc[len(bad_crc) // 2] ^= 0x01
    bad_magic = bytearray(good)
    bad_magic[0] = ord("X")
    for name, data in (("h14_bad_checksum", bytes(bad_crc)), ("h15_bad_magic", bytes(bad_magic))):
        (h / f"{name}.jrn").write_bytes(data)
        (h / f"{name}.json").write_text('{"__expect_exit_code__": 2}\n', encoding="utf-8")
    print("generated", len(list(out.rglob("*.jrn"))), "files into", out)


if __name__ == "__main__":
    main()
