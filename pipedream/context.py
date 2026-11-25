"""Run context passed to every step."""
from __future__ import annotations


class RunContext:
    """Carries upstream results and run metadata between steps.

    Every step receives the context as its first argument (conventionally
    named ``ctx``).  Upstream results are available by step name::

        @step(depends_on=["extract"])
        def transform(ctx, extract):     # injected: `extract` is the result
            raw = ctx["extract"]          # ... or read it from the context
            params = ctx.params           # pipeline parameters (read-only)

    The context is written by the engine and read by steps, so treat it as
    read-only inside step bodies.
    """

    def __init__(self, pipeline_name="", params=None):
        self.pipeline_name = pipeline_name
        self.params = dict(params or {})
        self._results = {}

    # -- mapping interface -------------------------------------------------

    def __getitem__(self, name):
        return self._results[name]

    def __contains__(self, name):
        return name in self._results

    def __iter__(self):
        return iter(self._results)

    def keys(self):
        return self._results.keys()

    def get(self, name, default=None):
        return self._results.get(name, default)

    # -- engine side --------------------------------------------------------

    def _publish(self, name, value):
        self._results[name] = value

    def __repr__(self):
        return f"<RunContext {self.pipeline_name!r} results={sorted(self._results)}>"
