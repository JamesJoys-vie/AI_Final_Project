"""
BACKTRACKING-SEARCH (Lecture 08) with pluggable heuristics:
variable ordering  : MRV (+ Degree tie-break) or static row-major order
value ordering     : LCV or ascending digits
inference          : MAC (GAC-3 after each assignment), forward checking, or none
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from task3_kakuro.core.csp_model import KakuroCSP, Variable
from task3_kakuro.solvers.combinations import possible_digits
from task3_kakuro.solvers.propagation import Domains, Propagator
from task3_kakuro.solvers.trace import SolverTrace


@dataclass(frozen=True)
class SolverConfig:
    inference: str = "mac"
    mrv: bool = True
    degree: bool = True
    lcv: bool = True
    preprocess: bool = True

    @property
    def label(self) -> str:
        order = ("MRV+Degree" if self.degree else "MRV") if self.mrv else "Static"
        return f"BT + {self.inference.upper()} + {order} + {'LCV' if self.lcv else 'Ascending'}"


@dataclass
class SolveStats:
    config: str
    solved: bool = False
    assignments: int = 0
    backtracks: int = 0
    revisions: int = 0
    pruned_values: int = 0
    elapsed: float = 0.0
    hit_limit: bool = False
    solution: Optional[Dict[Variable, int]] = None
    extra: Dict[str, int] = field(default_factory=dict)


class NodeLimitReached(Exception):
    pass


class BacktrackingSolver:
    def __init__(self, config: SolverConfig = SolverConfig(), node_limit: int = 2_000_000,
                 shuffle_seed: Optional[int] = None):
        self.config = config
        self.node_limit = node_limit
        self.shuffle_seed = shuffle_seed

    def solve(self, csp: KakuroCSP, trace: Optional[SolverTrace] = None) -> SolveStats:
        self.csp = csp
        self.trace = trace
        self.propagator = Propagator(csp)
        self.stats = SolveStats(self.config.label)
        # A seed shuffles the variable order (static order and tie-breaks) to test stability.
        self.variable_order = list(csp.variables)
        if self.shuffle_seed is not None:
            random.Random(self.shuffle_seed).shuffle(self.variable_order)
        start = time.perf_counter()
        domains: Domains = dict(csp.domains)
        assignment: Dict[Variable, int] = {}
        self._record("start", f"Start: {len(csp.variables)} variables, {len(csp.constraints)} run constraints",
                     0, domains, assignment)

        ok = True
        if self.config.preprocess:
            ok = self._preprocess(domains, assignment)
        try:
            result = self._backtrack(assignment, domains, 1) if ok else None
        except NodeLimitReached:
            result, self.stats.hit_limit = None, True

        self.stats.elapsed = time.perf_counter() - start
        self.stats.revisions = self.propagator.revisions
        self.stats.pruned_values = self.propagator.pruned_values
        self.stats.solved = result is not None and csp.is_solution(result)
        self.stats.solution = dict(result) if result else None
        if result:
            self._record("solution", f"Solution found after {self.stats.assignments} assignments", 0,
                         {v: frozenset({result[v]}) for v in csp.variables}, result)
        else:
            self._record("fail", "No solution" + (" (node limit)" if self.stats.hit_limit else ""), 0,
                         domains, assignment)
        return self.stats

    def _record(self, kind: str, message: str, depth: int, domains, assignment, **details) -> None:
        if self.trace is not None:
            self.trace.record(kind, message, depth, domains, assignment, **details)

    # ------------------------------------------------------------------ preprocessing
    def _preprocess(self, domains: Domains, assignment: Dict[Variable, int]) -> bool:
        """Node consistency from the digit-set table, then GAC-3 on all runs before searching."""
        for constraint in self.csp.constraints:
            allowed = possible_digits(len(constraint.cells), constraint.total)
            for cell in constraint.cells:
                domains[cell] = domains[cell] & allowed
        self._record("preprocess", "Node consistency: keep digits that appear in some valid sum set", 0,
                     domains, assignment)
        if any(not d for d in domains.values()):
            return False
        return self.propagator.gac3(domains, self.csp.constraints, self.trace, assignment, 0)

    # ------------------------------------------------------------------ search
    def _backtrack(self, assignment: Dict[Variable, int], domains: Domains, depth: int):
        if len(assignment) == len(self.csp.variables):
            return assignment
        variable = self._select_variable(assignment, domains)
        for value in self._order_values(variable, assignment, domains):
            if not self._consistent(variable, value, assignment):
                continue
            self.stats.assignments += 1
            if self.stats.assignments > self.node_limit:
                raise NodeLimitReached()
            assignment[variable] = value
            new_domains = dict(domains)
            new_domains[variable] = frozenset({value})
            self._record("assign", f"Assign {variable} = {value}", depth, new_domains, assignment,
                         variable=variable, value=value)
            if self._infer(variable, new_domains, assignment, depth):
                result = self._backtrack(assignment, new_domains, depth + 1)
                if result is not None:
                    return result
            del assignment[variable]
            self.stats.backtracks += 1
            self._record("backtrack", f"Backtrack: undo {variable} = {value}", depth, domains, assignment,
                         variable=variable, value=value)
        return None

    def _consistent(self, variable: Variable, value: int, assignment: Dict[Variable, int]) -> bool:
        trial = {**assignment, variable: value}
        return all(c.is_consistent({cell: trial[cell] for cell in c.cells if cell in trial})
                   for c in self.csp.constraints_of[variable])

    def _infer(self, variable: Variable, domains: Domains, assignment: Dict[Variable, int], depth: int) -> bool:
        if self.config.inference == "mac":
            return self.propagator.gac3(domains, self.csp.constraints_of[variable], self.trace, assignment, depth)
        if self.config.inference == "fc":
            return self.propagator.forward_check(variable, domains, assignment, self.trace, depth)
        return True

    def _select_variable(self, assignment: Dict[Variable, int], domains: Domains) -> Variable:
        """MRV = fewest remaining values; Degree = most constraints with unassigned cells (tie-break)."""
        unassigned = [v for v in self.variable_order if v not in assignment]
        if not self.config.mrv:
            return unassigned[0]

        def key(v: Variable):
            degree = sum(1 for n in self.csp.neighbors[v] if n not in assignment) if self.config.degree else 0
            return len(domains[v]), -degree

        return min(unassigned, key=key)

    def _order_values(self, variable: Variable, assignment: Dict[Variable, int], domains: Domains) -> List[int]:
        """
        LCV: try first the value that leaves the MOST options to the unassigned cells of its runs
        (each option is re-checked against the sum and all-different rules).
        """
        values = sorted(domains[variable])
        if not self.config.lcv:
            return values

        def remaining_options(value: int) -> int:
            trial = {**assignment, variable: value}
            options = 0
            for constraint in self.csp.constraints_of[variable]:
                partial = {cell: trial[cell] for cell in constraint.cells if cell in trial}
                for cell in constraint.cells:
                    if cell not in trial:
                        options += sum(1 for v in domains[cell] if constraint.is_consistent({**partial, cell: v}))
            return options

        return sorted(values, key=remaining_options, reverse=True)
