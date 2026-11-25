"""Exceptions raised by PipeDream.

Every error in this library derives from :class:`PipelineError`, so callers
can catch the whole family with a single ``except PipelineError``.
"""


class PipelineError(Exception):
    """Base class for every error raised by PipeDream."""


class DuplicateStepError(PipelineError):
    """Two steps in a pipeline share the same name."""

    def __init__(self, name):
        self.name = name
        super().__init__(f"duplicate step name: {name!r}")


class UnknownDependencyError(PipelineError):
    """A step depends on a name that is not defined in the pipeline."""

    def __init__(self, step_name, dependency, available):
        self.step_name = step_name
        self.dependency = dependency
        self.available = sorted(available)
        super().__init__(
            f"step {step_name!r} depends on unknown step {dependency!r}; "
            f"available steps: {', '.join(self.available) or '(none)'}"
        )


class CycleError(PipelineError):
    """The dependency graph contains a cycle."""

    def __init__(self, cycle):
        self.cycle = list(cycle)
        path = " -> ".join(self.cycle + self.cycle[:1])
        super().__init__(f"cycle detected in pipeline: {path}")


class StepArgumentError(PipelineError):
    """A step signature asks for arguments the pipeline cannot provide."""

    def __init__(self, step_name, missing, available):
        self.step_name = step_name
        self.missing = list(missing)
        self.available = list(available)
        hint = ", ".join(self.available) or "none"
        super().__init__(
            f"step {step_name!r} wants argument(s) {', '.join(self.missing)} "
            f"that no upstream step provides (upstream results available: {hint}); "
            f"either add the dependency, give the parameter a default, or read "
            f"the value from ctx['name']"
        )


class StepFailedError(PipelineError):
    """A step exhausted its retries and raised."""

    def __init__(self, step_name, attempts, cause):
        self.step_name = step_name
        self.attempts = attempts
        self.cause = cause
        super().__init__(
            f"step {step_name!r} failed after {attempts} attempt(s): "
            f"{type(cause).__name__}: {cause}"
        )
