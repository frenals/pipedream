"""PipeDream — a zero-dependency DAG orchestrator for data science pipelines.

Compose pipelines from plain functions::

    from pipedream import step, Pipeline

    @step
    def extract(ctx):
        return [1, 2, 3]

    @step(depends_on=["extract"], retries=2)
    def transform(ctx, extract):
        return [x * 10 for x in extract]

    pipeline = Pipeline("demo", [extract, transform])
    result = pipeline.run()

The entire package is standard-library Python: no virtualenv gymnastics, no
container images, no scheduler to babysit — just ``import pipedream``.
"""

from .context import RunContext
from .dag import DAG
from .data import generate_customers, generate_sales
from .engine import (
    CACHED,
    FAILED,
    PENDING,
    RUNNING,
    SKIPPED,
    SUCCESS,
    Engine,
    RunResult,
    StepResult,
)
from .exceptions import (
    CycleError,
    DuplicateStepError,
    PipelineError,
    StepArgumentError,
    StepFailedError,
    UnknownDependencyError,
)
from .pipeline import Pipeline
from .steps import Step, step

__version__ = "0.1.0"

__all__ = [
    "CACHED",
    "CycleError",
    "DAG",
    "DuplicateStepError",
    "FAILED",
    "Engine",
    "PENDING",
    "Pipeline",
    "PipelineError",
    "RUNNING",
    "RunContext",
    "RunResult",
    "SKIPPED",
    "Step",
    "StepArgumentError",
    "StepFailedError",
    "StepResult",
    "SUCCESS",
    "UnknownDependencyError",
    "generate_customers",
    "generate_sales",
    "run",
    "step",
]


def run(pipeline, **kwargs):
    """Shorthand for ``pipeline.run(**kwargs)``."""
    return pipeline.run(**kwargs)
