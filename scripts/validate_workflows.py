#!/usr/bin/env python3
"""Validate GitHub Actions workflow files the way GitHub parses them.

Guardrails for the exact failure we shipped once: a four-field cron string
(``0 */12 * *``) that GitHub rejects at parse time, failing the run before
any job starts. This script fails loudly on:

* cron strings that are not exactly five fields of valid syntax
* schedules that can never fire (month 0, day-of-week 7 with DOM-bound
  crontab(5) semantics, impossible ranges)
* jobs without a ``runs-on``, or a ``steps`` that isn't a list
* ``uses:`` actions without both owner and repo

Run from the repo root (or pass paths)::

    python scripts/validate_workflows.py            # .github/workflows/*.yml
    python scripts/validate_workflows.py path1 path2
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# PyYAML is third-party, but this script runs in CI (``pip install pyyaml``)
# and locally in dev environments; the *library* stays zero-dependency.
try:
    import yaml
except ImportError:  # pragma: no cover
    print("error: PyYAML is required for workflow validation "
          "(pip install pyyaml)")
    sys.exit(2)

MONTHS = {  # jan-dec aliases, crontab(5) style
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}
FIELD_RANGES = {  # GitHub accepts 0-7 for DOW (both 0 and 7 = Sunday)
    "minute": (0, 59), "hour": (0, 23), "dom": (1, 31),
    "month": (1, 12), "dow": (0, 7),
}


class CronError(ValueError):
    """Raised when a cron field is not valid crontab(5) syntax."""


def _value(token: str, field: str) -> int:
    """Resolve one token to an int, honoring month/day names."""
    token = token.lower()
    if field == "month" and token in MONTHS:
        return MONTHS[token]
    if field == "dow" and token in DAYS:
        return DAYS[token]
    if not re.fullmatch(r"\d+", token):
        raise CronError(f"non-numeric {field} value {token!r}")
    return int(token)


def _check_range(value: int, field: str) -> int:
    lo, hi = FIELD_RANGES[field]
    if not lo <= value <= hi:
        raise CronError(f"{field} value {value} out of range {lo}-{hi}")
    return value


def validate_cron_field(field: str, text: str) -> None:
    """Validate one five-field-cron field (lists, ranges, steps, names)."""
    if field not in FIELD_RANGES:
        raise CronError(f"unknown field {field!r}")
    for part in text.split(","):
        if not part:
            raise CronError(f"empty list item in {field} {text!r}")
        step = 1
        body = part
        if "/" in part:
            body, _, step_text = part.partition("/")
            if not step_text or not re.fullmatch(r"\d+", step_text):
                raise CronError(f"bad step in {field} {part!r}")
            step = int(step_text)
            if step < 1:
                raise CronError(f"step must be >= 1 in {field} {part!r}")
        if body == "*":
            lo, hi = FIELD_RANGES[field]
            if step > (hi - lo + 1):
                raise CronError(
                    f"step {step} exceeds {field} range {lo}-{hi} in {part!r}")
            continue  # */N and * are fine anywhere
        m = re.fullmatch(r"(\w+)-(\w+)", body)
        if m:
            lo = _check_range(_value(m.group(1), field), field)
            hi = _check_range(_value(m.group(2), field), field)
            if lo > hi:
                raise CronError(f"descending range in {field} {part!r}")
            if (hi - lo) < step and step != 1:
                raise CronError(f"step {step} larger than range in {field} {part!r}")
        elif re.fullmatch(r"\w+", body):
            _check_range(_value(body, field), field)
        else:
            raise CronError(f"unparseable {field} field {part!r}")


def validate_cron(expr: str) -> None:
    """Validate a five-field cron expression, or raise CronError."""
    fields = expr.split()
    if len(fields) != 5:
        raise CronError(
            f"expected 5 fields (minute hour day-of-month month "
            f"day-of-week), got {len(fields)}: {expr!r}"
        )
    for name, text in zip(FIELD_RANGES, fields):
        validate_cron_field(name, text)


def validate_workflow(path: Path) -> list[str]:
    """Return a list of human-readable problems (empty = valid)."""
    problems: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{path}: YAML parse error: {exc}"]
    if not isinstance(doc, dict):
        return [f"{path}: not a mapping at top level"]
    on = doc.get("on") or doc.get(True)  # YAML 1.1 parses bare `on:` as True
    if on is None:
        problems.append(f"{path}: no 'on:' trigger section")
    elif isinstance(on, dict):
        for entry in on.get("schedule") or []:
            if not isinstance(entry, dict) or "cron" not in entry:
                problems.append(f"{path}: schedule entry without cron: {entry!r}")
                continue
            try:
                validate_cron(entry["cron"])
            except CronError as exc:
                problems.append(f"{path}: {exc}")
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        problems.append(f"{path}: no jobs")
    else:
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                problems.append(f"{path}: job {job_name!r} is not a mapping")
                continue
            if "runs-on" not in job:
                problems.append(f"{path}: job {job_name!r} has no runs-on")
            steps = job.get("steps")
            if steps is not None and not isinstance(steps, list):
                problems.append(f"{path}: job {job_name!r} steps is not a list")
            for i, step in enumerate(steps or []):
                if isinstance(step, dict) and "uses" in step:
                    ref = str(step["uses"])
                    if "/" not in ref or ref.startswith(("http", "/")):
                        problems.append(
                            f"{path}: step {i} uses {ref!r} without owner/repo")
    return problems


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args:
        paths = [Path(p) for p in args]
    else:
        root = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        paths = sorted(root.glob("*.yml"))
    if not paths:
        print("no workflow files found")
        return 0
    failed = False
    for path in paths:
        problems = validate_workflow(path)
        if problems:
            failed = True
            for problem in problems:
                print(f"✗ {problem}")
        else:
            print(f"✓ {path} valid")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
