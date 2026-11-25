"""Tests for the execution engine: scheduling, retries, failures, output."""

import time

from pipedream import FAILED, PENDING, SKIPPED, SUCCESS, Pipeline, step


def test_values_flow_downstream():
    @step
    def a(ctx):
        return 10

    @step(depends_on=["a"])
    def b(ctx, a):
        return a * 2

    result = Pipeline("flow", [a, b]).run(quiet=True, use_cache=False)
    assert result.success
    assert result["a"] == 10
    assert result["b"] == 20
    assert result.values["b"] == 20


def test_signature_injection_without_ctx_parameter():
    @step
    def a(ctx):
        return 5

    @step(depends_on=["a"])
    def b(a):
        return a + 1

    result = Pipeline("inject", [a, b]).run(quiet=True, use_cache=False)
    assert result["b"] == 6


def test_params_reach_steps():
    @step
    def show(ctx):
        return ctx.params.get("answer", 0)

    result = Pipeline("params", [show], params={"answer": 42}).run(quiet=True, use_cache=False)
    assert result["show"] == 42


def test_retries_survive_flaky_steps():
    calls = {"n": 0}

    @step(retries=3, retry_delay=0.01)
    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = Pipeline("flaky", [flaky]).run(quiet=True, use_cache=False)
    assert result.success
    assert result["flaky"] == "ok"
    assert calls["n"] == 3
    assert result.steps["flaky"].attempts == 3


def test_failure_skips_downstream_but_not_siblings():
    ran = []

    @step
    def ok_sibling(ctx):
        ran.append("sibling")
        return 1

    @step(retries=1, retry_delay=0.01)
    def bad(ctx):
        ran.append("bad")
        raise ValueError("boom")

    @step(depends_on=["bad"])
    def downstream(ctx, bad):
        ran.append("downstream")

    result = Pipeline("fail", [ok_sibling, bad, downstream]).run(quiet=True, use_cache=False)
    assert not result.success
    assert not bool(result)
    assert result.steps["bad"].status == FAILED
    assert result.steps["bad"].attempts == 2
    assert result.steps["bad"].error is not None
    assert result.steps["downstream"].status == SKIPPED
    assert result.steps["ok_sibling"].status == SUCCESS
    assert "downstream" not in ran
    assert "sibling" in ran
    assert result["ok_sibling"] == 1


def test_fail_fast_leaves_later_steps_unstarted():
    @step
    def slow_ok(ctx):
        time.sleep(0.2)
        return 1

    @step
    def bad(ctx):
        raise RuntimeError("nope")

    @step(depends_on=["slow_ok"])
    def later(ctx, slow_ok):
        return 2

    result = Pipeline("fail-fast", [slow_ok, bad, later]).run(
        quiet=True, fail_fast=True, use_cache=False)
    assert result.steps["bad"].status == FAILED
    assert result.steps["slow_ok"].status == SUCCESS
    assert result.steps["later"].status == PENDING
    assert not result.success


def test_missing_argument_error_is_actionable():
    @step
    def a(ctx):
        return 1

    @step(depends_on=["a"])
    def picky(ctx, nonexistent):
        return 2

    result = Pipeline("picky", [a, picky]).run(quiet=True, use_cache=False)
    assert result.steps["picky"].status == FAILED
    assert "nonexistent" in result.steps["picky"].note


def _sleep_steps():
    def build(i):
        @step(name=f"sleepy_{i}", cache=False)
        def sleepy(ctx):
            time.sleep(0.25)
            return i
        return sleepy
    return [build(i) for i in range(4)]


def test_parallel_execution_is_actually_parallel():
    steps = _sleep_steps()
    started = time.perf_counter()
    result = Pipeline("par", steps).run(quiet=True, use_cache=False)
    elapsed = time.perf_counter() - started
    assert result.success
    assert all(r.status == SUCCESS for r in result.steps.values())
    assert elapsed < 0.75, f"parallel run took {elapsed:.2f}s"


def test_serial_execution_is_sequential():
    steps = _sleep_steps()
    started = time.perf_counter()
    Pipeline("serial", steps).run(quiet=True, parallel=False, use_cache=False)
    elapsed = time.perf_counter() - started
    assert elapsed >= 0.95, f"serial run took only {elapsed:.2f}s"


def test_quiet_run_prints_nothing(capsys):
    @step
    def a(ctx):
        return 1

    Pipeline("quiet", [a]).run(quiet=True, use_cache=False)
    assert capsys.readouterr().out == ""


def test_verbose_run_prints_progress(capsys):
    @step
    def hello(ctx):
        return 1

    result = Pipeline("loud", [hello]).run(use_cache=False)
    out = capsys.readouterr().out
    assert "hello" in out
    assert "loud" in out
    assert "completed" in out
    assert result.success


def test_run_result_summary_mentions_failures():
    @step
    def bad(ctx):
        raise ValueError("kaboom")

    result = Pipeline("summary", [bad]).run(quiet=True, use_cache=False)
    assert "FAILED" in result.summary()
    assert "kaboom" in result.summary()
