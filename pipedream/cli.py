"""Command line interface.

    python -m pipedream run   examples/01_sales_report.py
    python -m pipedream graph examples/02_churn_scoring.py --mermaid
    python -m pipedream list  examples/01_sales_report.py
    python -m pipedream clean examples/01_sales_report.py
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

from . import __version__
from .cache import Cache
from .pipeline import DEFAULT_CACHE_DIR, Pipeline


def _fail(message):
    print(f"pipedream: {message}", file=sys.stderr)
    raise SystemExit(1)


def _load_module(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        _fail(f"no such file: {path}")
    sys.path.insert(0, os.path.dirname(path))
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        _fail(f"could not import {path}: {type(exc).__name__}: {exc}")
    return module


def _find_pipeline(module):
    try:
        return Pipeline.from_module(module)
    except Exception as exc:
        _fail(str(exc))


def _parse_params(pairs):
    params = {}
    for pair in pairs or ():
        key, sep, value = pair.partition("=")
        if not sep or not key:
            _fail(f"--param expects KEY=VALUE, got {pair!r}")
        params[key] = value
    return params


def cmd_run(args):
    pipeline = _find_pipeline(_load_module(args.module))
    pipeline.params.update(_parse_params(args.param))
    result = pipeline.run(
        parallel=not args.serial,
        max_workers=args.jobs,
        use_cache=not args.no_cache,
        fail_fast=args.fail_fast,
        quiet=args.quiet,
        cache_dir=args.cache_dir,
    )
    return 0 if result.success else 1


def cmd_graph(args):
    pipeline = _find_pipeline(_load_module(args.module))
    print(pipeline.graph("mermaid" if args.mermaid else "tree"))
    return 0


def cmd_list(args):
    pipeline = _find_pipeline(_load_module(args.module))
    dag = pipeline.dag
    plural = "s" if len(pipeline) != 1 else ""
    print(f"{pipeline.name} — {len(pipeline)} step{plural}")
    for i, name in enumerate(dag.topo_order(), 1):
        print(f"  {i:>2}. {dag.steps[name].describe()}")
    return 0


def cmd_clean(args):
    pipeline = _find_pipeline(_load_module(args.module))
    removed = Cache(args.cache_dir, pipeline.name).clear()
    plural = "s" if removed != 1 else ""
    print(f"cleared {removed} cached result{plural} for {pipeline.name!r}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipedream",
        description="PipeDream — a zero-dependency DAG orchestrator for data science pipelines.",
    )
    parser.add_argument("--version", action="version",
                        version=f"pipedream {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("module", help="Python file that defines the pipeline")
    common.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR,
                        help="cache location (default: %(default)s)")

    p_run = sub.add_parser("run", parents=[common],
                           help="execute a pipeline")
    p_run.add_argument("--serial", action="store_true",
                       help="run steps one at a time (no thread pool)")
    p_run.add_argument("-j", "--jobs", type=int, default=None,
                       help="max parallel workers (default: auto)")
    p_run.add_argument("--no-cache", action="store_true",
                       help="skip reading and writing cached results")
    p_run.add_argument("--fail-fast", action="store_true",
                       help="stop scheduling new steps after the first failure")
    p_run.add_argument("--param", action="append", metavar="KEY=VALUE",
                       help="set a pipeline parameter (repeatable)")
    p_run.add_argument("--quiet", action="store_true",
                       help="no progress output, just the exit code")
    p_run.set_defaults(func=cmd_run)

    p_graph = sub.add_parser("graph", parents=[common],
                             help="print the DAG (tree or --mermaid)")
    p_graph.add_argument("--mermaid", action="store_true",
                         help="emit Mermaid flowchart syntax instead of a tree")
    p_graph.set_defaults(func=cmd_graph)

    p_list = sub.add_parser("list", parents=[common],
                            help="list the pipeline's steps")
    p_list.set_defaults(func=cmd_list)

    p_clean = sub.add_parser("clean", parents=[common],
                             help="delete cached results for the pipeline")
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
