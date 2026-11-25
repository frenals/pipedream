"""Terminal rendering: progress lines, run summaries, DAG trees, tables.

Everything here degrades gracefully: without a TTY (or with ``NO_COLOR``
set) the ANSI colours disappear but the layout stays identical, so logs
captured by CI remain readable.
"""
from __future__ import annotations

import os
import re
import sys

from .engine import CACHED, FAILED, PENDING, RUNNING, SKIPPED, SUCCESS

_COLOR = (
    sys.stdout.isatty()
    and os.environ.get("NO_COLOR") is None
    and os.environ.get("TERM", "") != "dumb"
)

# status -> (symbol, ansi colour code)
_SYMBOLS = {
    PENDING: ("○", "2"),
    RUNNING: ("▸", "36"),
    SUCCESS: ("✓", "32"),
    CACHED: ("↻", "36"),
    FAILED: ("✗", "31"),
    SKIPPED: ("⊘", "33"),
}
_WORDS = {
    PENDING: "pending", RUNNING: "running", SUCCESS: "ok",
    CACHED: "cached", FAILED: "failed", SKIPPED: "skipped",
}


def paint(text, code):
    """Wrap text in an ANSI colour if the terminal supports it."""
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _fmt_seconds(seconds):
    if seconds >= 60:
        minutes = int(seconds // 60)
        return f"{minutes}m{seconds - minutes * 60:04.1f}s"
    return f"{seconds:.2f}s"


def _first_line(text, limit=64):
    line = str(text).strip().splitlines()[0] if str(text).strip() else ""
    return line if len(line) <= limit else line[: limit - 1] + "…"


def render_step_line(name, record):
    """One progress line: ``  ✓ orders ........... ok      0.01s``."""
    symbol, colour = _SYMBOLS[record.status]
    parts = []
    if record.status in (SUCCESS, FAILED):
        parts.append(_fmt_seconds(record.duration))
        if record.attempts > 1:
            parts.append(f"{record.attempts} tries")
    if record.status == CACHED:
        parts.append("cache hit")
    elif record.status == FAILED:
        parts.append(_first_line(record.note))
    elif record.note:
        parts.append(record.note)
    dots = "." * max(2, 30 - len(name))
    line = (f"  {paint(symbol, colour)} {name} "
            f"{paint(dots, '2')} {paint(_WORDS[record.status], colour)}")
    if parts:
        line += " " + paint(" · ".join(parts), "2")
    return line


def render_run_summary(result):
    """Final line(s) of a run."""
    counts = {}
    for record in result.steps.values():
        counts[record.status] = counts.get(record.status, 0) + 1

    bits = []
    for status, label in ((SUCCESS, "ok"), (CACHED, "cached"),
                          (FAILED, "failed"), (SKIPPED, "skipped"),
                          (PENDING, "not started")):
        if counts.get(status):
            bits.append(f"{counts[status]} {label}")
    tally = " · ".join(bits) or "no steps"
    duration = _fmt_seconds(result.duration)

    if result.success:
        return (paint("✓", "32") + " "
                + paint(f"{result.pipeline_name} completed in {duration}", "1")
                + f" — {tally}")

    lines = [paint("✗", "31") + " "
             + paint(f"{result.pipeline_name} FAILED in {duration}", "1")
             + f" — {tally}"]
    for record in result.steps.values():
        if record.status == FAILED:
            lines.append(paint(f"  ↳ {record.name}: {record.note}", "31"))
    return "\n".join(lines)


def _step_meta(step):
    bits = []
    if step.retries:
        bits.append(f"retries={step.retries}")
    if not step.cache:
        bits.append("cache=off")
    if step.tags:
        bits.append("#" + " #".join(step.tags))
    return "; ".join(bits)


def render_tree(pipeline):
    """ASCII tree view of the DAG; diamond joins are marked ``(repeated)``."""
    dag = pipeline.dag
    steps = pipeline.steps
    header = paint(pipeline.name, "1")
    if pipeline.description:
        header += paint(f" — {pipeline.description}", "2")
    lines = [header]
    seen = set()

    def walk(name, prefix):
        kids = dag.dependents(name)
        for i, kid in enumerate(kids):
            last = i == len(kids) - 1
            branch = "└── " if last else "├── "
            if kid in seen:
                suffix = paint(" (repeated)", "2")
            else:
                meta = _step_meta(steps[kid])
                suffix = paint(f"  [{meta}]", "2") if meta else ""
            lines.append(f"{prefix}{branch}{kid}{suffix}")
            if kid not in seen:
                seen.add(kid)
                walk(kid, prefix + ("    " if last else "│   "))

    roots = dag.roots()
    for i, root in enumerate(roots):
        last = i == len(roots) - 1
        meta = _step_meta(steps[root])
        suffix = paint(f"  [{meta}]", "2") if meta else ""
        lines.append(f"{'└── ' if last else '├── '}{root}{suffix}")
        seen.add(root)
        walk(root, "    " if last else "│   ")
    if not roots:
        lines.append(paint("  (empty pipeline)", "2"))
    return "\n".join(lines)


def render_mermaid(pipeline):
    """The same DAG as Mermaid ``flowchart`` syntax (renders on GitHub)."""

    def node_id(name):
        cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
        if not cleaned or cleaned[0].isdigit():
            cleaned = "n" + cleaned
        return cleaned

    lines = ["flowchart TD"]
    for name in pipeline.steps:
        lines.append(f'    {node_id(name)}["{name}"]')
    for name, step in pipeline.steps.items():
        for dep in step.depends_on:
            lines.append(f"    {node_id(dep)} --> {node_id(name)}")
    return "\n".join(lines)


def markdown_table(headers, rows):
    """Tiny markdown table builder for reports (no pandas required)."""
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)
