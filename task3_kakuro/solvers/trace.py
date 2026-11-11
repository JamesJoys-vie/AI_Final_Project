"""
Records every solver step with a snapshot of all domains, so the UI can replay, pause and scrub
through constraint propagation and backtracking.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, NamedTuple, Optional, Tuple

Variable = Tuple[int, int]


class TraceEvent(NamedTuple):
    kind: str
    message: str
    depth: int
    domains: Dict[Variable, FrozenSet[int]]
    assignment: Dict[Variable, int]
    variable: Optional[Variable] = None
    value: Optional[int] = None
    constraint: Optional[int] = None
    removed: Optional[Dict[Variable, FrozenSet[int]]] = None


class SolverTrace:
    """kinds: start, preprocess, revise, assign, wipeout, backtrack, solution, fail."""

    def __init__(self, max_events: int = 50_000):
        self.events: List[TraceEvent] = []
        self.max_events = max_events
        self.truncated = False

    def record(self, kind: str, message: str, depth: int, domains, assignment, **details) -> None:
        if len(self.events) >= self.max_events:
            self.truncated = True
            return
        self.events.append(TraceEvent(kind, message, depth, dict(domains), dict(assignment), **details))

    def __len__(self) -> int:
        return len(self.events)
