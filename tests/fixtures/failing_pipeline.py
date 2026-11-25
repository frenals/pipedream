"""A deliberately failing pipeline used by the CLI tests."""

from pipedream import Pipeline, step


@step
def boom(ctx):
    raise ValueError("intentional failure (used by tests)")


@step(depends_on=["boom"])
def unreachable(ctx, boom):
    raise AssertionError("must never run")


pipeline = Pipeline("failing", [boom, unreachable])
