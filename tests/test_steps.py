"""Tests for Step and the @step decorator."""

from pipedream import Step, step


def test_bare_decorator():
    @step
    def extract(ctx):
        return 1

    assert isinstance(extract, Step)
    assert extract.name == "extract"
    assert extract.depends_on == ()
    assert extract(None) == 1  # Step stays callable like the plain function


def test_decorator_with_options():
    @step(name="clean-data", depends_on=["extract"], retries=3,
          retry_delay=0.01, cache=False, tags=("etl",))
    def clean(ctx):
        return 2

    assert clean.name == "clean-data"
    assert clean.depends_on == ("extract",)
    assert clean.retries == 3
    assert clean.retry_delay == 0.01
    assert clean.cache is False
    assert clean.tags == ("etl",)


def test_depends_on_accepts_step_objects_and_names():
    @step
    def a(ctx):
        return 1

    @step(depends_on=[a, "c"])
    def b(ctx):
        return 2

    assert b.depends_on == ("a", "c")


def test_source_hash_is_stable_and_discriminating():
    @step
    def one(ctx):
        return 1

    @step
    def two(ctx):
        return 2

    assert one.source_hash != two.source_hash
    assert one.source_hash == one.source_hash


def test_docstring_and_metadata_survive_wrapping():
    @step
    def documented(ctx):
        """I have a docstring."""
        return 1

    assert documented.func.__doc__ == "I have a docstring."
    assert documented.__name__ == "documented"


def test_describe_mentions_non_defaults():
    @step(retries=2, cache=False, tags=("nightly",))
    def fancy(ctx):
        return 1

    text = fancy.describe()
    assert "retries=2" in text
    assert "cache=off" in text
    assert "#nightly" in text
