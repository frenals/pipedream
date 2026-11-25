"""Tests for the content-addressed result cache."""

from pipedream import CACHED, SUCCESS, Pipeline, step


def _counter_pipeline():
    calls = {"n": 0}

    @step
    def data(ctx):
        calls["n"] += 1
        return [1, 2, 3]

    @step(depends_on=["data"], cache=False)
    def always_fresh(ctx, data):
        calls["n"] += 1
        return len(data)

    return Pipeline("cache-test", [data, always_fresh]), calls


def test_second_run_hits_cache(tmp_path):
    pipeline, calls = _counter_pipeline()
    cache = str(tmp_path / "cache")

    first = pipeline.run(quiet=True, cache_dir=cache)
    assert first.steps["data"].status == SUCCESS
    assert calls["n"] == 2

    second = pipeline.run(quiet=True, cache_dir=cache)
    assert second.steps["data"].status == CACHED
    assert second["data"] == [1, 2, 3]
    assert second.steps["always_fresh"].status == SUCCESS
    assert calls["n"] == 3  # only always_fresh re-executed


def test_param_change_invalidates_cache(tmp_path):
    pipeline, calls = _counter_pipeline()
    cache = str(tmp_path / "cache")
    pipeline.run(quiet=True, cache_dir=cache)
    pipeline.params["scale"] = "2"
    pipeline.run(quiet=True, cache_dir=cache)
    assert calls["n"] == 4  # data re-executed after the param change


def test_no_cache_flag_disables_lookup(tmp_path):
    pipeline, calls = _counter_pipeline()
    cache = str(tmp_path / "cache")
    pipeline.run(quiet=True, cache_dir=cache)
    pipeline.run(quiet=True, cache_dir=cache, use_cache=False)
    assert calls["n"] == 4


def test_unpicklable_results_are_simply_not_cached(tmp_path):
    calls = {"n": 0}

    @step
    def gen(ctx):
        calls["n"] += 1
        return (x for x in range(3))

    pipeline = Pipeline("unpicklable", [gen])
    cache = str(tmp_path / "cache")
    first = pipeline.run(quiet=True, cache_dir=cache)
    second = pipeline.run(quiet=True, cache_dir=cache)
    assert calls["n"] == 2
    assert first.steps["gen"].status == SUCCESS
    assert second.steps["gen"].status == SUCCESS  # not CACHED


def test_corrupt_cache_entries_are_ignored(tmp_path):
    @step
    def data(ctx):
        return {"a": 1}

    pipeline = Pipeline("corrupt", [data])
    cache = str(tmp_path / "cache")
    pipeline.run(quiet=True, cache_dir=cache)

    entries = list((tmp_path / "cache").rglob("*.result"))
    assert entries, "expected a cache entry to exist"
    entries[0].write_bytes(b"this is not a pickle")

    result = pipeline.run(quiet=True, cache_dir=cache)
    assert result.steps["data"].status == SUCCESS
    assert result["data"] == {"a": 1}


def test_none_results_are_cacheable(tmp_path):
    calls = {"n": 0}

    @step
    def nothing(ctx):
        calls["n"] += 1
        return None

    pipeline = Pipeline("nothing", [nothing])
    cache = str(tmp_path / "cache")
    pipeline.run(quiet=True, cache_dir=cache)
    second = pipeline.run(quiet=True, cache_dir=cache)
    assert calls["n"] == 1
    assert second.steps["nothing"].status == CACHED
    assert second["nothing"] is None


def test_keys_ignore_object_sharing_between_inputs(tmp_path):
    """Regression: pickle memoizes shared objects, which used to make cache
    keys unstable across round-trips when upstream outputs shared strings."""
    calls = {"n": 0}

    @step
    def a(ctx):
        return {"id": "shared-string", "n": 1}

    @step(depends_on=["a"])
    def b(ctx, a):
        return [a["id"], "other", a["id"]]  # shares objects with a's output

    @step(depends_on=["a", "b"])
    def sink(ctx, a, b):
        calls["n"] += 1
        return len(b)

    pipeline = Pipeline("sharing", [a, b, sink])
    cache = str(tmp_path / "cache")
    first = pipeline.run(quiet=True, cache_dir=cache)
    assert first.success
    second = pipeline.run(quiet=True, cache_dir=cache)
    assert second.steps["sink"].status == CACHED
    assert calls["n"] == 1
