"""Step objects and the ``@step`` decorator."""
from __future__ import annotations

import functools
import hashlib
import inspect


class Step:
    """A single unit of work inside a :class:`~pipedream.pipeline.Pipeline`.

    Steps are usually created with the :func:`step` decorator::

        @step(depends_on=["extract"], retries=2)
        def transform(ctx, extract):
            ...

    A ``Step`` wraps an ordinary function and adds pipeline metadata: its
    name, dependencies, retry policy and caching behaviour.  The wrapped
    function stays callable, so a step can also be used on its own.
    """

    def __init__(self, func, *, name=None, depends_on=(), retries=0,
                 retry_delay=0.2, backoff=2.0, cache=True, tags=()):
        self.func = func
        self.name = name or getattr(func, "__name__", "step")
        self.depends_on = tuple(self._as_name(d) for d in depends_on)
        self.retries = max(0, int(retries))
        self.retry_delay = max(0.0, float(retry_delay))
        self.backoff = max(1.0, float(backoff))
        self.cache = bool(cache)
        self.tags = tuple(tags)
        self._source_hash = None

    @staticmethod
    def _as_name(dep):
        return dep.name if isinstance(dep, Step) else str(dep)

    @property
    def source_hash(self):
        """Stable hash of the wrapped function's source code.

        Used as part of the cache key, so editing a step's code invalidates
        its cached results automatically.
        """
        if self._source_hash is None:
            try:
                source = inspect.getsource(self.func)
            except (OSError, TypeError):
                source = repr(self.func)
            self._source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return self._source_hash

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        return f"<Step {self.name} depends_on={list(self.depends_on)}>"

    def describe(self):
        """One-line human description used by ``pipedream list``."""
        deps = ", ".join(self.depends_on) or "(root)"
        bits = [f"deps: {deps}"]
        if self.retries:
            bits.append(f"retries={self.retries}")
        bits.append("cache=on" if self.cache else "cache=off")
        if self.tags:
            bits.append("#" + " #".join(self.tags))
        return f"{self.name} ({'; '.join(bits)})"


def step(func=None, *, name=None, depends_on=(), retries=0,
         retry_delay=0.2, backoff=2.0, cache=True, tags=()):
    """Turn a function into a pipeline :class:`Step`.

    Works bare or with options::

        @step                                # bare form
        def extract(ctx):
            ...

        @step(depends_on=["extract"], retries=2, cache=False)
        def transform(ctx, extract):         # upstream result injected by name
            ...

    Arguments:
        name:        override the step name (defaults to the function name).
        depends_on:  names (or Step objects) this step needs upstream.
        retries:     extra attempts after a failure (0 = fail immediately).
        retry_delay: seconds before the first retry; grows by ``backoff``.
        backoff:     multiplier applied to ``retry_delay`` after each retry.
        cache:       persist this step's result between runs (default true).
        tags:        free-form labels for documentation and filtering.
    """
    def make(func):
        wrapped = Step(func, name=name, depends_on=depends_on, retries=retries,
                       retry_delay=retry_delay, backoff=backoff, cache=cache,
                       tags=tags)
        functools.update_wrapper(wrapped, func, updated=())
        return wrapped

    return make(func) if func is not None else make
