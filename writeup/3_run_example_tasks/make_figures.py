#!/usr/bin/env python3
"""Problem 7: figures comparing mini-SWE-agent trajectories on HumanEval, SWE-bench and Terminal-Bench.

Run from the repo root:  uv run python writeup/3_run_example_tasks/make_figures.py

Every figure is computed from the saved trajectories (agent/trajectory.json) in
writeup/3_run_example_tasks/artifacts/. Each bash command the agent ran is classified with simple,
keyword-based rules (see classify()); these are heuristics, not ground truth.
"""
import json
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
RUNS = {  # label -> job folder
    "HumanEval": "humaneval-agent",
    "SWE-bench": "swebench-django-11099",
    "Terminal-Bench": "terminal-bench-model-extraction",
}
CATS = ["Inspect", "Edit", "Run / test", "Submit", "Other"]
COLORS = {"Inspect": "#4C78A8", "Edit": "#E45756", "Run / test": "#54A24B", "Submit": "#999999", "Other": "#F2CF5B"}

INSPECT = {"cat", "ls", "find", "grep", "head", "tail", "sed", "wc", "file", "which", "pwd", "tree", "stat",
           "od", "xxd", "hexdump", "less", "diff", "echo", "env", "pip", "conda", "uname", "du", "df", "strings"}
GIT_INSPECT = {"log", "show", "diff", "status", "grep", "ls-files", "blame"}
WRITE_PAT = re.compile(
    r"(cat\s*(<<-?\s*['\"]?\w+['\"]?\s*)?>>?\s*\S)|(sed\s+-i)|(\btee\b)|(\bgit\s+apply\b)|(\bpatch\b\s)|"
    r"(\.write\()|(open\([^)]*['\"][wa]b?\+?['\"])|(np\.save)|(\bmv\s)|(\bcp\s)|(\btouch\b)|(\bchmod\b)|(>\s*/?[\w./-]+\.(py|npy|txt|json|sh))"
)


def load(job):
    """Return the list of bash commands (in order) from the first trial of a job, or None."""
    jobdir = ART / job
    if not jobdir.is_dir():
        return None
    for trial in sorted(p for p in jobdir.iterdir() if p.is_dir() and "__" in p.name):
        path = trial / "agent" / "trajectory.json"
        if path.is_file():
            data = json.loads(path.read_text())
            cmds = []
            for step in data["steps"]:
                if step.get("source") != "agent":
                    continue
                for call in step.get("tool_calls") or []:
                    cmd = (call.get("arguments") or {}).get("command")
                    if cmd:
                        cmds.append(cmd)
            return cmds
    return None


def program(cmd):
    """First program name of a command (skipping cd/source/env assignments); python variants -> 'python'."""
    text = cmd.strip()
    text = re.sub(r"^(cd\s+\S+\s*&&\s*|source\s+\S+\s*&&\s*|(\w+=\S+\s+)+)", "", text)
    first = text.split()[0] if text.split() else ""
    name = first.split("/")[-1]
    if re.fullmatch(r"python[\d.]*", name):
        return "python"
    if name == "git":
        parts = text.split()
        return f"git {parts[1]}" if len(parts) > 1 else "git"
    if name == "uv":
        return "uv"
    return name or "(empty)"


def classify(cmd):
    if "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in cmd:
        return "Submit"
    if WRITE_PAT.search(cmd) and not re.match(r"\s*(grep|git\s+(grep|log|show))", cmd):
        # writing code through python -c "... open(...,'w')" etc. counts as an edit
        return "Edit"
    prog = program(cmd)
    if prog in INSPECT or (prog.startswith("git ") and prog.split()[1] in GIT_INSPECT):
        return "Inspect"
    if prog == "python" or prog in {"pytest", "make", "bash", "sh", "uv", "./ci.sh", "ci.sh", "time", "timeout", "runtests.py"} or "runtests" in cmd or "pytest" in cmd:
        return "Run / test"
    return "Other"


def main():
    data = {}
    for label, job in RUNS.items():
        cmds = load(job)
        if cmds:
            data[label] = cmds
        else:
            print(f"[skip] no trajectory found for {label} ({job})")
    if not data:
        raise SystemExit("no trajectories found")

    labels = list(data)
    classes = {k: [classify(c) for c in v] for k, v in data.items()}

    # ---- 1. effort-distribution.png : share of commands per activity
    fig, ax = plt.subplots(figsize=(8, 4.2))
    left = [0.0] * len(labels)
    for cat in CATS:
        shares = [100 * classes[k].count(cat) / len(classes[k]) for k in labels]
        ax.barh(labels, shares, left=left, color=COLORS[cat], label=cat)
        for i, (s, l) in enumerate(zip(shares, left)):
            if s >= 6:
                ax.text(l + s / 2, i, f"{s:.0f}%", ha="center", va="center", color="white", fontsize=9)
        left = [l + s for l, s in zip(left, shares)]
    ax.set_xlabel("% of bash commands")
    ax.set_xlim(0, 100)
    ax.set_title("How each agent spent its commands (n = %s)" % ", ".join(f"{k}: {len(data[k])}" for k in labels), fontsize=10)
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(HERE / "effort-distribution.png", dpi=160)
    plt.close(fig)

    # ---- 2. bash-command-usage.png : top programs per task
    counts = {k: Counter(program(c) for c in v) for k, v in data.items()}
    overall = Counter()
    for c in counts.values():
        overall.update(c)
    top = [p for p, _ in overall.most_common(9)]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    width = 0.8 / len(labels)
    palette = ["#4C78A8", "#F58518", "#54A24B"]
    for j, k in enumerate(labels):
        tot = sum(counts[k].values())
        vals = [100 * counts[k][p] / tot for p in top]
        ax.bar([i + j * width for i in range(len(top))], vals, width, label=f"{k} (n={tot})", color=palette[j % 3])
    ax.set_xticks([i + width * (len(labels) - 1) / 2 for i in range(len(top))])
    ax.set_xticklabels(top, rotation=30, ha="right")
    ax.set_ylabel("% of that task's commands")
    ax.set_title("Most-used command-line programs (first word of each command)", fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(HERE / "bash-command-usage.png", dpi=160)
    plt.close(fig)

    # ---- 3. exploration-to-implementation.png : timeline, first edit = transition
    fig, axes = plt.subplots(len(labels), 1, figsize=(9, 1.5 * len(labels) + 0.9), sharex=False)
    axes = [axes] if len(labels) == 1 else list(axes)
    summary = {}
    for ax, k in zip(axes, labels):
        cl = classes[k]
        for i, cat in enumerate(cl):
            ax.bar(i, 1, width=0.9, color=COLORS[cat])
        first_edit = next((i for i, c in enumerate(cl) if c == "Edit"), None)
        if first_edit is not None:
            ax.axvline(first_edit - 0.5, color="black", lw=1.5, ls="--")
            ax.text(first_edit - 0.3, 1.08, f"first edit: command {first_edit + 1} of {len(cl)} ({100 * (first_edit + 1) / len(cl):.0f}%)",
                    fontsize=8, va="bottom")
        summary[k] = (first_edit + 1 if first_edit is not None else None, len(cl))
        ax.set_yticks([])
        ax.set_xlim(-0.6, len(cl) - 0.4)
        ax.set_ylim(0, 1.5)
        ax.set_ylabel(k, rotation=0, ha="right", va="center", fontsize=10)
        ax.set_xlabel("command number" if ax is axes[-1] else "")
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[c]) for c in CATS]
    fig.legend(handles, CATS, ncol=5, loc="lower center", frameon=False, fontsize=9)
    fig.suptitle("Exploration vs implementation: dashed line = first command that writes a file", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(HERE / "exploration-to-implementation.png", dpi=160)
    plt.close(fig)

    print("\n=== numbers for the write-up ===")
    for k in labels:
        n = len(classes[k])
        print(f"{k}: {n} commands;", ", ".join(f"{c}={classes[k].count(c)} ({100 * classes[k].count(c) / n:.0f}%)" for c in CATS))
        print(f"   first edit at command {summary[k][0]} of {summary[k][1]}")
        print("   top programs:", counts[k].most_common(6))


if __name__ == "__main__":
    main()
