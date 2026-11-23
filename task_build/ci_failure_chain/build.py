#!/usr/bin/env python3
"""Assemble tasks/ci-failure-chain from buggy_app/, fixes/ and generated/."""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent.parent / "tasks" / "ci-failure-chain"
APP = TASK / "environment" / "app"
PRISTINE = TASK / "tests" / "pristine"

def copy(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))

copy(HERE / "buggy_app", APP)
copy(HERE / "generated" / "app", APP)           # data/, control totals, settings
for name in ("tests", "tools", "data"):
    copy(APP / name, PRISTINE / name)
shutil.copy2(APP / "ci.sh", PRISTINE / "ci.sh")
copy(HERE / "generated" / "holdout", TASK / "tests" / "holdout")

# solution/solve.sh: writes the fixed files over the buggy ones
parts = ["#!/bin/bash", "set -euo pipefail", ""]
for f in sorted((HERE / "fixes").rglob("*.py")):
    rel = f.relative_to(HERE / "fixes")
    parts.append(f"cat > /app/{rel} <<'__LEDGER_EOF__'")
    parts.append(f.read_text(encoding="utf-8").rstrip("\n"))
    parts.append("__LEDGER_EOF__")
    parts.append("")
(TASK / "solution" / "solve.sh").write_text("\n".join(parts), encoding="utf-8")
(TASK / "solution" / "solve.sh").chmod(0o755)
print("assembled", TASK)
