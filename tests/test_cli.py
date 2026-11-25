"""End-to-end CLI tests (subprocess, like a real user would run it)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "pipedream", *args],
        capture_output=True, text=True, cwd=ROOT, timeout=120,
    )


def test_run_sales_report():
    proc = _run("run", "examples/01_sales_report.py", "--no-cache")
    assert proc.returncode == 0, proc.stderr
    assert "sales-report" in proc.stdout
    assert "revenue_by_region" in proc.stdout
    assert "Regional revenue" in proc.stdout


def test_run_churn_example():
    proc = _run("run", "examples/02_churn_scoring.py", "--no-cache")
    assert proc.returncode == 0, proc.stderr
    assert "Churn model" in proc.stdout
    assert "roc auc" in proc.stdout.lower()


def test_run_fan_out():
    proc = _run("run", "examples/03_fan_out_fan_in.py", "--no-cache")
    assert proc.returncode == 0, proc.stderr
    assert "aggregate_Nairobi" in proc.stdout
    assert "Regional revenue" in proc.stdout


def test_graph_tree():
    proc = _run("graph", "examples/01_sales_report.py")
    assert proc.returncode == 0, proc.stderr
    assert "customers" in proc.stdout
    assert "├──" in proc.stdout or "└──" in proc.stdout


def test_graph_mermaid():
    proc = _run("graph", "examples/01_sales_report.py", "--mermaid")
    assert proc.returncode == 0, proc.stderr
    assert "flowchart TD" in proc.stdout
    assert "-->" in proc.stdout


def test_list():
    proc = _run("list", "examples/01_sales_report.py")
    assert proc.returncode == 0, proc.stderr
    assert "customers" in proc.stdout
    assert "5 steps" in proc.stdout


def test_failing_pipeline_exits_nonzero():
    proc = _run("run", "tests/fixtures/failing_pipeline.py", "--no-cache")
    assert proc.returncode == 1
    assert "failed" in proc.stdout
    assert "skipped" in proc.stdout


def test_cache_roundtrip_via_cli(tmp_path):
    cache = str(tmp_path / "cache")
    first = _run("run", "examples/01_sales_report.py", "--cache-dir", cache)
    assert first.returncode == 0, first.stderr

    second = _run("run", "examples/01_sales_report.py", "--cache-dir", cache)
    assert second.returncode == 0, second.stderr
    assert "cached" in second.stdout

    cleaned = _run("clean", "examples/01_sales_report.py", "--cache-dir", cache)
    assert cleaned.returncode == 0, cleaned.stderr
    assert "cleared" in cleaned.stdout

    after_clean = _run("run", "examples/01_sales_report.py", "--cache-dir", cache)
    assert after_clean.returncode == 0, after_clean.stderr
    # the banner always says "cache on"; no step line should say "cached"
    assert "cached" not in after_clean.stdout.replace("cache on", "")


def test_missing_file_is_a_clean_error():
    proc = _run("run", "examples/does_not_exist.py")
    assert proc.returncode == 1
    assert "no such file" in proc.stderr
