"""Execution engine: scheduling, retries, caching and result bookkeeping.

The scheduler is a ready-queue on a ``ThreadPoolExecutor``: a step becomes
eligible the moment all of its dependencies have succeeded, so independent
branches overlap naturally without any layer-by-layer batching.  Because
steps typically do I/O (read files, call APIs, query databases), threads give
real parallelism while keeping everything in one process and one stdlib.
"""
from __future__ import annotations

import inspect
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from .cache import Cache, hash_params
from .context import RunContext
from .exceptions import StepArgumentError, StepFailedError

# -- statuses -----------------------------------------------------------------
PENDING = "pending"
RUNNING = "running"
SUCCESS = "success"
CACHED = "cached"
FAILED = "failed"
SKIPPED = "skipped"

_DONE_OK = (SUCCESS, CACHED)
_BLOCKING = (FAILED, SKIPPED)


class StepResult:
    """Bookkeeping for one step within a run."""

    __slots__ = ("name", "status", "attempts", "started_at", "finished_at",
                 "error", "note")

    def __init__(self, name):
        self.name = name
        self.status = PENDING
        self.attempts = 0
        self.started_at = None
        self.finished_at = None
        self.error = None
        self.note = ""

    @property
    def duration(self):
        if self.started_at is not None and self.finished_at is not None:
            return self.finished_at - self.started_at
        return 0.0

    @property
    def ok(self):
        return self.status in _DONE_OK


class RunResult:
    """Everything about one pipeline run."""

    def __init__(self, pipeline_name, step_results, values, started_at, finished_at):
        self.pipeline_name = pipeline_name
        self.steps = step_results        # name -> StepResult
        self.values = values             # name -> return value
        self.started_at = started_at
        self.finished_at = finished_at

    @property
    def duration(self):
        return self.finished_at - self.started_at

    @property
    def success(self):
        return all(r.ok for r in self.steps.values())

    def __getitem__(self, name):
        return self.values[name]

    def __contains__(self, name):
        return name in self.values

    def __len__(self):
        return len(self.steps)

    def __bool__(self):
        return self.success

    def summary(self):
        from .render import render_run_summary

        return render_run_summary(self)

    def __str__(self):
        return self.summary()


class Engine:
    """Runs a pipeline: schedules ready steps, retries, caches, reports."""

    def __init__(self, pipeline, *, parallel=True, max_workers=None,
                 use_cache=True, fail_fast=False, quiet=False, cache_dir=None):
        self.pipeline = pipeline
        self.dag = pipeline.dag
        self.parallel = bool(parallel)
        self.max_workers = max_workers
        self.fail_fast = fail_fast
        self.quiet = quiet
        self.use_cache = use_cache
        self._cache = (
            Cache(cache_dir if cache_dir is not None else pipeline.cache_dir,
                  pipeline.name)
            if use_cache else None
        )
        self._params_hash = hash_params(pipeline.params)

    # -- public API -------------------------------------------------------------

    def run(self):
        steps = self.pipeline.steps
        ctx = RunContext(self.pipeline.name, self.pipeline.params)
        results = {name: StepResult(name) for name in steps}
        values = {}
        workers = self._worker_count()
        start = time.perf_counter()
        self._banner(len(steps), workers)

        remaining = self.dag.topo_order()
        abort = False

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            while remaining or futures:
                # 1) cascade skips: anything downstream of a failure is skipped
                self._cascade_skips(remaining, results)

                # 2) submit every ready step unless we are aborting
                if not abort:
                    for name in list(remaining):
                        step = steps[name]
                        if not all(results[d].status in _DONE_OK
                                   for d in step.depends_on):
                            continue
                        if self._cache is not None and step.cache:
                            key = self._cache.key(
                                step, self._params_hash,
                                tuple(values[d] for d in step.depends_on))
                            found, value = self._cache.lookup(key)
                            if found:
                                values[name] = value
                                ctx._publish(name, value)
                                results[name].status = CACHED
                                results[name].note = "cache hit"
                                remaining.remove(name)
                                self._emit(name, results[name])
                                continue
                        results[name].status = RUNNING
                        results[name].started_at = time.perf_counter()
                        futures[pool.submit(self._execute, step, ctx)] = name
                        remaining.remove(name)

                # 3) nothing running and nothing ready: either aborting or stuck
                if not futures:
                    if remaining and not abort:
                        # Unreachable for a validated DAG; kept as a guard.
                        raise RuntimeError(
                            f"scheduler stalled with steps {remaining!r}")
                    break

                # 4) reap at least one completion
                done, _ = wait(set(futures), return_when=FIRST_COMPLETED)
                for future in done:
                    name = futures.pop(future)
                    step = steps[name]
                    record = results[name]
                    record.finished_at = time.perf_counter()
                    try:
                        value, attempts = future.result()
                    except StepFailedError as exc:
                        record.status = FAILED
                        record.attempts = exc.attempts
                        record.error = exc.cause
                        record.note = f"{type(exc.cause).__name__}: {exc.cause}"
                        if self.fail_fast:
                            abort = True
                        self._emit(name, record)
                        continue
                    values[name] = value
                    ctx._publish(name, value)
                    record.status = SUCCESS
                    record.attempts = attempts
                    if self._cache is not None and step.cache:
                        key = self._cache.key(
                            step, self._params_hash,
                            tuple(values[d] for d in step.depends_on))
                        self._cache.store(key, value)
                    self._emit(name, record)

        for record in results.values():
            if record.status == PENDING:
                record.note = "not started (fail-fast)"

        result = RunResult(self.pipeline.name, results, values,
                           start, time.perf_counter())
        self._footer(result)
        return result

    # -- step execution -----------------------------------------------------------

    def _execute(self, step, ctx):
        """Run one step with retries and exponential backoff."""
        attempts = 0
        delay = step.retry_delay
        while True:
            attempts += 1
            try:
                return self._invoke(step, ctx), attempts
            except Exception as exc:
                wiring_bug = isinstance(exc, StepArgumentError)
                if attempts > step.retries or wiring_bug:
                    raise StepFailedError(step.name, attempts, exc)
                if delay > 0:
                    time.sleep(delay)
                    delay *= step.backoff

    @staticmethod
    def _invoke(step, ctx):
        """Call a step function, injecting upstream results by parameter name.

        Conventions:
          * first parameter named ``ctx`` receives the :class:`RunContext`;
          * any other parameter whose name matches an upstream step receives
            that step's result;
          * parameters with defaults are left alone unless they match.
        """
        func = step.func
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            return func(ctx)
        params = list(signature.parameters.values())
        takes_ctx = bool(params) and params[0].name == "ctx"
        injectable = [p for p in (params[1:] if takes_ctx else params)
                      if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                    inspect.Parameter.KEYWORD_ONLY)]
        kwargs = {}
        for param in injectable:
            if param.name in ctx:
                kwargs[param.name] = ctx[param.name]
        missing = [p.name for p in injectable
                   if p.name not in ctx and p.default is inspect.Parameter.empty]
        if missing:
            raise StepArgumentError(step.name, missing, sorted(ctx.keys()))
        args = [ctx] if takes_ctx else []
        return func(*args, **kwargs)

    # -- scheduling helpers ----------------------------------------------------------

    def _cascade_skips(self, remaining, results):
        changed = True
        while changed:
            changed = False
            for name in list(remaining):
                blocked_by = next(
                    (d for d in self.pipeline.steps[name].depends_on
                     if results[d].status in _BLOCKING), None)
                if blocked_by is not None:
                    remaining.remove(name)
                    record = results[name]
                    record.status = SKIPPED
                    record.note = f"upstream {blocked_by!r} did not succeed"
                    self._emit(name, record)
                    changed = True

    def _worker_count(self):
        if not self.parallel:
            return 1
        if self.max_workers:
            return max(1, int(self.max_workers))
        cpu = os.cpu_count() or 1
        workers = min(8, cpu, max(1, len(self.pipeline)))
        if workers < 2 and len(self.pipeline) >= 2:
            workers = 2  # steps are usually I/O-bound; allow some overlap
        return workers

    # -- output ------------------------------------------------------------------------

    def _banner(self, n_steps, workers):
        if self.quiet:
            return
        from .render import paint

        plural = "s" if n_steps != 1 else ""
        if workers > 1:
            mode = f"parallel · {workers} workers"
        else:
            mode = "serial"
        cache_mode = "on" if self._cache is not None else "off"
        print()
        print(paint(f"◆ {self.pipeline.name} — {n_steps} step{plural} · "
                    f"{mode} · cache {cache_mode}", "1"))
        print()

    def _emit(self, name, record):
        if self.quiet:
            return
        from .render import render_step_line

        print(render_step_line(name, record))

    def _footer(self, result):
        if self.quiet:
            return
        from .render import render_run_summary

        print()
        print(render_run_summary(result))
        print()
