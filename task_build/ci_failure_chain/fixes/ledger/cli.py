"""Command line entry point."""

import argparse
import csv
import json
import os

from ledger.aggregate import build_report
from ledger.config import load_settings
from ledger.parsing import parse_rows


def read_export(path):
    with open(path, newline="", encoding="cp1252") as handle:
        return list(csv.DictReader(handle))


def build(config_path, out_path):
    settings = load_settings(config_path)
    transactions = []
    dropped = 0
    for path in settings.inputs:
        rows = read_export(path)
        parsed = parse_rows(rows)
        dropped += len(rows) - len(parsed)
        transactions.extend(parsed)
    report = build_report(
        transactions, settings.fx_rates, settings.base_currency, dropped
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="build the monthly report")
    build_cmd.add_argument("--config", required=True)
    build_cmd.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.config, args.out)


if __name__ == "__main__":
    main()
