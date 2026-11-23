#!/bin/bash
# Verifier for ci-failure-chain. Reward is 1 only if BOTH the visible pipeline and the
# hidden held-out checks pass. Directory overrides exist so this can be tested without Docker.
set -uo pipefail

APP="${APP_DIR:-/app}"
TESTS="${TESTS_DIR:-/tests}"
LOGS="${LOG_DIR:-/logs/verifier}"
PY="${PYTHON:-python}"

mkdir -p "$LOGS"
echo 0 > "$LOGS/reward.txt"

# 1. Restore everything the agent was told not to change (tests, tools, data, ci.sh).
rm -rf "$APP/tests" "$APP/tools" "$APP/data" "$APP/dist" "$APP/ci.sh"
cp -R "$TESTS/pristine/tests" "$APP/tests"
cp -R "$TESTS/pristine/tools" "$APP/tools"
cp -R "$TESTS/pristine/data" "$APP/data"
cp "$TESTS/pristine/ci.sh" "$APP/ci.sh"
find "$APP" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

# 2. The visible pipeline must pass end to end.
if ! (cd "$APP" && PATH="${PY_DIR:+$PY_DIR:}$PATH" timeout 300 bash ci.sh) > "$LOGS/ci.log" 2>&1; then
  echo "FAIL: ci.sh did not exit 0 (see ci.log)" | tee "$LOGS/summary.txt"
  tail -n 25 "$LOGS/ci.log"
  exit 0
fi

# 3. Hidden checks: run the CLI on held-out exports and compare to reference reports.
if ! (cd "$APP" && APP_DIR="$APP" TESTS_DIR="$TESTS" PYTHON="$PY" timeout 300 "$PY" "$TESTS/test_hidden.py") > "$LOGS/hidden.log" 2>&1; then
  echo "FAIL: hidden held-out checks failed (see hidden.log)" | tee "$LOGS/summary.txt"
  tail -n 40 "$LOGS/hidden.log"
  exit 0
fi

echo 1 > "$LOGS/reward.txt"
echo "PASS: ci.sh green and all held-out scenarios match" | tee "$LOGS/summary.txt"
