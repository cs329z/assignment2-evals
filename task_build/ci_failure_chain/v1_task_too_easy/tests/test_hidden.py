"""Hidden held-out checks.

Every scenario under /tests/holdout is a set of ERP exports plus settings and the report the
README rules require (produced by an independent reference implementation). The agent's CLI
is run as a black box on each one, so any valid way of fixing the code is accepted.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(os.environ.get("APP_DIR", "/app"))
HOLDOUT = Path(os.environ.get("TESTS_DIR", "/tests")) / "holdout"
PY = os.environ.get("PYTHON", sys.executable)


def diff(actual, expected, path="report"):
    """Short human-readable list of differences between two JSON values."""
    out = []
    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in sorted(set(actual) | set(expected)):
            if key not in actual:
                out.append(f"{path}.{key}: missing (expected {expected[key]!r})")
            elif key not in expected:
                out.append(f"{path}.{key}: unexpected (got {actual[key]!r})")
            else:
                out.extend(diff(actual[key], expected[key], f"{path}.{key}"))
    elif actual != expected:
        out.append(f"{path}: got {actual!r}, expected {expected!r}")
    return out


class HoldoutTests(unittest.TestCase):
    def run_scenario(self, name):
        folder = HOLDOUT / name
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            proc = subprocess.run(
                [PY, "-m", "ledger.cli", "build", "--config", str(folder / "settings.json"), "--out", str(out)],
                cwd=APP, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 0, f"CLI failed on {name}:\n{proc.stderr[-1500:]}")
            actual = json.loads(out.read_text(encoding="utf-8"))
        expected = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
        problems = diff(actual, expected)
        self.assertEqual(problems, [], f"{name}: " + "; ".join(problems[:8]))


def _make(name):
    def test(self):
        self.run_scenario(name)
    return test


for _name in sorted(p.name for p in HOLDOUT.iterdir() if p.is_dir()):
    setattr(HoldoutTests, f"test_{_name}", _make(_name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
