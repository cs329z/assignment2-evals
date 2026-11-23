#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== [1/4] smoke: import the package =="
python -c "import ledger.cli"

echo "== [2/4] unit tests =="
python -m unittest discover -s tests -v

echo "== [3/4] build report =="
python -m ledger.cli build --config config/settings.json --out dist/report.json

echo "== [4/4] reconcile against finance control totals =="
python tools/verify_report.py dist/report.json

echo "CI passed"
