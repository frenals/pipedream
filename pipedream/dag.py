"""Directed acyclic graph with cycle detection and topological ordering."""
from __future__ import annotations

from .exceptions import CycleError, UnknownDependencyError

_WHITE, _GRAY, _BLACK = 0, 1, 2


class DAG:
    """A validated dependency graph built from an ordered ``{name: Step}`` dict.

    Construction validates that every dependency exists and that the graph is
    acyclic; both problems raise immediately (with the offending path) instead
    of surfacing as a hung run later.
    """

    def __init__(self, steps):
        self.steps = dict(steps)
        self._validate_deps()
        self._dependents = {name: [] for name in self.steps}
        for name, s in self.steps.items():
            for dep in s.depends_on:
                self._dependents[dep].append(name)
        self._detect_cycles()

    def _validate_deps(self):
        for name, s in self.steps.items():
            for dep in s.depends_on:
                if dep not in self.steps:
                    raise UnknownDependencyError(name, dep, self.steps)
            if name in s.depends_on:
                raise CycleError([name])

    def _detect_cycles(self):
        colour = {n: _WHITE for n in self.steps}
        path = []

        def visit(node):
            colour[node] = _GRAY
            path.append(node)
            for nxt in self._dependents[node]:
                if colour[nxt] == _GRAY:
                    cycle_start = path.index(nxt)
                    raise CycleError(path[cycle_start:] + [nxt])
                if colour[nxt] == _WHITE:
                    visit(nxt)
            path.pop()
            colour[node] = _BLACK

        for node in list(self.steps):
            if colour[node] == _WHITE:
                visit(node)

    # -- queries -------------------------------------------------------------

    def deps(self, name):
        """Names this step depends on."""
        return self.steps[name].depends_on

    def dependents(self, name):
        """Names that depend on this step."""
        return list(self._dependents[name])

    def roots(self):
        """Steps with no dependencies."""
        return [n for n, s in self.steps.items() if not s.depends_on]

    def topo_order(self):
        """Kahn's algorithm; deterministic (definition order among ready steps)."""
        indegree = {n: len(self.steps[n].depends_on) for n in self.steps}
        ready = [n for n in self.steps if indegree[n] == 0]
        order = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for nxt in self._dependents[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)
        if len(order) != len(self.steps):  # defensive; cycles raise earlier
            raise CycleError([n for n in self.steps if n not in set(order)])
        return order

    def depth(self, name):
        """Length of the longest dependency chain ending at ``name``."""
        memo = {}

        def compute(n):
            if n not in memo:
                deps = self.steps[n].depends_on
                memo[n] = 0 if not deps else 1 + max(compute(d) for d in deps)
            return memo[n]

        return compute(name)

    def layers(self):
        """Steps grouped by depth — everything in a layer may start together."""
        grouped = {}
        for n in self.steps:
            grouped.setdefault(self.depth(n), []).append(n)
        return [grouped[k] for k in sorted(grouped)]

    def __len__(self):
        return len(self.steps)
