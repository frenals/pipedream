"""Pipeline: a named collection of steps forming a DAG."""
from __future__ import annotations

from .dag import DAG
from .exceptions import DuplicateStepError
from .steps import Step

DEFAULT_CACHE_DIR = ".pipedream_cache"


class Pipeline:
    """A named DAG of steps.

    >>> pipeline = Pipeline("sales-etl", [extract, transform, load])
    >>> result = pipeline.run()

    Steps can also be registered one at a time with :meth:`add`, which is
    chainable and happily wraps plain functions.
    """

    def __init__(self, name, steps=(), *, description="", params=None,
                 cache_dir=DEFAULT_CACHE_DIR):
        self.name = name
        self.description = description
        self.params = dict(params or {})
        self.cache_dir = cache_dir
        self._steps = {}
        for s in steps:
            self._register(s)
        self._validate()

    def add(self, s):
        """Register a step (chainable).  Plain callables are wrapped for you."""
        self._register(s)
        self._validate()
        return self

    def _register(self, s):
        if not isinstance(s, Step):
            s = Step(s)
        if s.name in self._steps:
            raise DuplicateStepError(s.name)
        self._steps[s.name] = s

    def _validate(self):
        """Fail fast on unknown dependencies and cycles (builds the DAG)."""
        self.dag  # noqa: B018 - property access validates the graph

    # -- introspection --------------------------------------------------------

    @property
    def steps(self):
        return dict(self._steps)

    @property
    def dag(self):
        return DAG(self._steps)

    def graph(self, style="tree"):
        """Render the DAG as text: ``tree`` (ASCII) or ``mermaid``."""
        from .render import render_mermaid, render_tree

        if style == "mermaid":
            return render_mermaid(self)
        return render_tree(self)

    def __len__(self):
        return len(self._steps)

    def __iter__(self):
        return iter(self._steps.values())

    def __repr__(self):
        return f"<Pipeline {self.name!r} steps={len(self._steps)}>"

    # -- execution -------------------------------------------------------------

    def run(self, *, parallel=True, max_workers=None, use_cache=True,
            fail_fast=False, quiet=False, cache_dir=None):
        """Execute the pipeline and return a :class:`~pipedream.engine.RunResult`.

        Arguments:
            parallel:     schedule independent steps on a thread pool (default).
            max_workers:  cap on parallel steps (default: auto).
            use_cache:    reuse cached results from previous runs (default).
            fail_fast:    stop scheduling new steps after the first failure.
            quiet:        suppress progress output.
            cache_dir:    override the cache location for this run.
        """
        from .engine import Engine

        engine = Engine(
            self,
            parallel=parallel,
            max_workers=max_workers,
            use_cache=use_cache,
            fail_fast=fail_fast,
            quiet=quiet,
            cache_dir=cache_dir if cache_dir is not None else self.cache_dir,
        )
        return engine.run()

    # -- discovery ---------------------------------------------------------------

    @classmethod
    def from_module(cls, module):
        """Find a pipeline in a module.

        Looks for a module-level ``pipeline`` attribute, then a
        ``build_pipeline()`` callable, and finally collects every ``Step``
        defined at top level (in definition order).
        """
        candidate = getattr(module, "pipeline", None)
        if isinstance(candidate, cls):
            return candidate
        builder = getattr(module, "build_pipeline", None)
        if callable(builder):
            built = builder()
            if isinstance(built, cls):
                return built
        found = [v for v in vars(module).values() if isinstance(v, Step)]
        if not found:
            raise LookupError(
                f"no pipeline found in {getattr(module, '__name__', module)!r}: "
                f"expected a `pipeline` attribute, a build_pipeline() function, "
                f"or module-level @step functions"
            )
        name = getattr(module, "__name__", "pipeline") or "pipeline"
        return cls(name.rsplit(".", 1)[-1], found)
