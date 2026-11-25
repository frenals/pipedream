"""Tests for Pipeline containers, graphs and module discovery."""

import types

import pytest

from pipedream import DuplicateStepError, Pipeline, step


def test_add_wraps_plain_functions_and_is_chainable():
    pipeline = Pipeline("wrap")

    def plain(ctx):
        return 1

    def other(ctx):
        return 2

    pipeline.add(plain).add(other)
    assert set(pipeline.steps) == {"plain", "other"}


def test_duplicate_names_are_rejected():
    @step(name="dup")
    def a(ctx):
        return 1

    @step(name="dup")
    def b(ctx):
        return 2

    with pytest.raises(DuplicateStepError):
        Pipeline("dupes", [a, b])


def test_tree_graph_renders_names_and_marks_repeated_nodes():
    @step
    def root(ctx):
        return 1

    @step(depends_on=["root"])
    def left(ctx, root):
        return 2

    @step(depends_on=["root"])
    def right(ctx, root):
        return 3

    @step(depends_on=["left", "right"])
    def sink(ctx, left, right):
        return 4

    tree = Pipeline("diamond", [root, left, right, sink]).graph()
    assert "root" in tree
    assert "sink" in tree
    # the diamond sink is reachable via two paths; the second is marked
    assert "repeated" in tree


def test_tree_graph_marks_non_default_options():
    @step(retries=2, cache=False)
    def flaky(ctx):
        return 1

    tree = Pipeline("opts", [flaky]).graph()
    assert "retries=2" in tree
    assert "cache=off" in tree


def test_mermaid_graph():
    @step
    def a(ctx):
        return 1

    @step(depends_on=["a"])
    def b(ctx, a):
        return 2

    mermaid = Pipeline("mm", [a, b]).graph("mermaid")
    assert mermaid.startswith("flowchart TD")
    assert "-->" in mermaid


def test_empty_pipeline_tree():
    tree = Pipeline("empty").graph()
    assert "empty pipeline" in tree


def test_from_module_discovers_top_level_steps():
    mod = types.ModuleType("mymod")

    @step
    def first(ctx):
        return 1

    @step(depends_on=["first"])
    def second(ctx, first):
        return 2

    mod.first = first
    mod.second = second
    pipeline = Pipeline.from_module(mod)
    assert len(pipeline) == 2


def test_from_module_prefers_explicit_pipeline_attribute():
    mod = types.ModuleType("mymod")

    @step
    def stray(ctx):
        return 1

    explicit = Pipeline("explicit")
    mod.stray = stray
    mod.pipeline = explicit
    assert Pipeline.from_module(mod) is explicit
