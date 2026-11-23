#!/usr/bin/env python3
"""Decode a legacy .jrn journal file to JSON on stdout. Exit 2 if the file is invalid."""
import json
import struct
import sys
import zlib
from datetime import datetime, timezone

XOR_KEY = 0x5A
EXPONENT = {"JPY": 0, "KWD": 3}


class BadFile(Exception):
    pass


def read_varint(buf, pos):
    value = shift = 0
    while True:
        if pos >= len(buf):
            raise BadFile("truncated varint")
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7


def money(minor, currency):
    exp = EXPONENT.get(currency, 2)
    sign = "-" if minor < 0 else ""
    mag = abs(minor)
    if exp == 0:
        return f"{sign}{mag}"
    return f"{sign}{mag // 10 ** exp}.{mag % 10 ** exp:0{exp}d}"


def decode(data):
    if data[:4] != b"JRN\x01" or len(data) < 4 + 10 + 4:
        raise BadFile("bad magic")
    body = data[4:-4]
    if zlib.crc32(body) & 0xFFFFFFFF != struct.unpack("<I", data[-4:])[0]:
        raise BadFile("bad checksum")
    try:
        count, base = struct.unpack_from(">HI", body, 0)
        default = body[6:9].decode("ascii")
        n_accounts = body[9]
        pos = 10
        accounts = []
        for _ in range(n_accounts):
            length = body[pos]
            accounts.append(body[pos + 1:pos + 1 + length].decode("utf-8"))
            pos += 1 + length
        records, now, memos = [], base, []
        for index in range(count):
            flags = body[pos]
            pos += 1
            delta, pos = read_varint(body, pos)
            now += delta
            account = accounts[body[pos]]
            pos += 1
            minor, pos = read_varint(body, pos)
            currency = default
            if flags & 4:
                currency = body[pos:pos + 3].decode("ascii")
                pos += 3
            memo = None
            if flags & 16:
                ref, pos = read_varint(body, pos)
                memo = memos[ref]
            elif flags & 1:
                length, pos = read_varint(body, pos)
                memo = bytes(b ^ XOR_KEY for b in body[pos:pos + length]).decode("utf-8")
                pos += length
                memos.append(memo)
            records.append({
                "index": index,
                "timestamp": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "account": account,
                "amount": money(-minor if flags & 2 else minor, currency),
                "currency": currency,
                "memo": memo,
                "status": "pending" if flags & 8 else "posted",
            })
    except (IndexError, struct.error, UnicodeDecodeError) as exc:
        raise BadFile(str(exc))
    return {"default_currency": default, "accounts": accounts, "records": records}


def main():
    if len(sys.argv) != 2:
        print("usage: jrndecode.py FILE.jrn", file=sys.stderr)
        return 2
    with open(sys.argv[1], "rb") as handle:
        data = handle.read()
    try:
        result = decode(data)
    except BadFile as exc:
        print(f"invalid .jrn file: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
