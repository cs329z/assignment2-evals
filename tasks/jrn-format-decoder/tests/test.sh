#!/bin/bash
# Verifier for jrn-format-decoder: reward 1 only if EVERY hidden file is handled correctly.
# Directory overrides exist so this can be tested without Docker.
set -uo pipefail

APP="${APP_DIR:-/app}"
TESTS="${TESTS_DIR:-/tests}"
LOGS="${LOG_DIR:-/logs/verifier}"
PY="${PYTHON:-python}"

mkdir -p "$LOGS"
echo 0 > "$LOGS/reward.txt"

if [ ! -f "$APP/jrndecode.py" ]; then
  echo "FAIL: $APP/jrndecode.py does not exist" | tee "$LOGS/summary.txt"
  exit 0
fi

# The decoder must stand on its own: remove the samples so it cannot look answers up at runtime.
rm -rf "$APP/samples"

if APP_DIR="$APP" TESTS_DIR="$TESTS" PYTHON="$PY" SCORE_FILE="$LOGS/score.txt" \
   timeout 600 "$PY" "$TESTS/test_hidden.py" > "$LOGS/hidden.log" 2>&1; then
  echo 1 > "$LOGS/reward.txt"
  echo "PASS: all hidden files decoded correctly" | tee "$LOGS/summary.txt"
else
  echo "FAIL: $(cat "$LOGS/score.txt" 2>/dev/null) hidden files correct (see hidden.log)" | tee "$LOGS/summary.txt"
  grep '^FAIL' "$LOGS/hidden.log" | head -8
fi
