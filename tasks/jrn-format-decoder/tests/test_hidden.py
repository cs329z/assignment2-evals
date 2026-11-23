"""Run the agent's /app/jrndecode.py on hidden .jrn files and compare to ground truth.

Ground truth (*.json next to each *.jrn) was produced from the generating records, not from any
decoder. Valid files must decode to exactly the expected JSON; corrupt files must exit with
status 2 and print nothing to stdout.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(os.environ.get("APP_DIR", "/app"))
HOLDOUT = Path(os.environ.get("TESTS_DIR", "/tests")) / "holdout"
PY = os.environ.get("PYTHON", sys.executable)
SCORE = os.environ.get("SCORE_FILE")


def first_difference(actual, expected, path="$"):
    if type(actual) is not type(expected):
        return f"{path}: type {type(actual).__name__} != {type(expected).__name__}"
    if isinstance(expected, dict):
        for key in sorted(set(actual) | set(expected)):
            if key not in actual:
                return f"{path}.{key}: missing"
            if key not in expected:
                return f"{path}.{key}: unexpected"
            found = first_difference(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: {len(actual)} items, expected {len(expected)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            found = first_difference(a, e, f"{path}[{i}]")
            if found:
                return found
    elif actual != expected:
        return f"{path}: got {actual!r}, expected {expected!r}"
    return None


def run_one(jrn, expected):
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "input.jrn"
        data.write_bytes(jrn.read_bytes())
        try:
            proc = subprocess.run(
                [PY, str(APP / "jrndecode.py"), str(data)], cwd=tmp, capture_output=True,
                timeout=60, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired:
            return "timed out"
    if "__expect_exit_code__" in expected:
        want = expected["__expect_exit_code__"]
        if proc.returncode != want:
            return f"exit code {proc.returncode}, expected {want}"
        if proc.stdout.strip():
            return "wrote to stdout for an invalid file"
        return None
    if proc.returncode != 0:
        return f"exit code {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[-300:]}"
    try:
        actual = json.loads(proc.stdout.decode("utf-8"))
    except ValueError as exc:
        return f"stdout is not valid JSON ({exc})"
    return first_difference(actual, expected)


def main():
    files = sorted(HOLDOUT.glob("*.jrn"))
    failures = []
    for jrn in files:
        expected = json.loads(jrn.with_suffix(".json").read_text(encoding="utf-8"))
        problem = run_one(jrn, expected)
        print(("FAIL " if problem else "ok   ") + jrn.name + (f"  -> {problem}" if problem else ""))
        if problem:
            failures.append(jrn.name)
    passed = len(files) - len(failures)
    print(f"\n{passed}/{len(files)} hidden files decoded correctly")
    if SCORE:
        Path(SCORE).write_text(f"{passed}/{len(files)}\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
