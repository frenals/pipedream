"""Tests for DAG construction, validation and traversal."""

import pytest

from pipedream import CycleError, Pipeline, UnknownDependencyError, step


def _pipeline(steps):
    return Pipeline("dag-test", steps)


def test_topo_order_respects_dependencies():
    @step
    def a(ctx):
        return 1

    @step(depends_on=["a"])
    def b(ctx, a):
        return a + 1

    @step(depends_on=["b"])
    def c(ctx, b):
        return b + 1

    order = _pipeline([a, b, c]).dag.topo_order()
    assert order.index("a") < order.index("b") < order.index("c")


def test_diamond_layers_and_roots():
    @step
    def a(ctx):
        return 1

    @step(depends_on=["a"])
    def b(ctx, a):
        return a

    @step(depends_on=["a"])
    def c(ctx, a):
        return a

    @step(depends_on=["b", "c"])
    def d(ctx, b, c):
        return b + c

    dag = _pipeline([a, b, c, d]).dag
    assert dag.layers() == [["a"], ["b", "c"], ["d"]]
    assert dag.roots() == ["a"]


def test_cycle_is_detected_with_the_offending_path():
    @step(depends_on=["b"])
    def a(ctx):
        return 1

    @step(depends_on=["a"])
    def b(ctx):
        return 2

    with pytest.raises(CycleError) as err:
        _pipeline([a, b])
    message = str(err.value)
    assert "a" in message and "b" in message
    assert "->" in message


def test_self_dependency_is_a_cycle():
    @step(depends_on=["loop"])
    def loop(ctx):
        return 1

    with pytest.raises(CycleError):
        _pipeline([loop])


def test_unknown_dependency_names_everything_available():
    @step(depends_on=["ghost"])
    def lonely(ctx):
        return 1

    with pytest.raises(UnknownDependencyError) as err:
        _pipeline([lonely])
    assert "ghost" in str(err.value)
    assert "lonely" in str(err.value)


def test_dependents_query():
    @step
    def root(ctx):
        return 1

    @step(depends_on=["root"])
    def left(ctx, root):
        return 2

    @step(depends_on=["root"])
    def right(ctx, root):
        return 3

    dag = _pipeline([root, left, right]).dag
    assert sorted(dag.dependents("root")) == ["left", "right"]
    assert dag.deps("left") == ("root",)
    assert len(dag) == 3
