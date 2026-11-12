"""
Constraint propagation for Kakuro runs (Lecture 08).
- GAC-3 (AC-3 generalized to n-ary constraints): keep value v of cell X only if some valid digit set
  of the run contains v AND the other cells can take the remaining digits of that set (a perfect matching).
- Forward checking: after X = v, remove v from X's run-mates and drop values that break the sum bounds.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence

from task3_kakuro.core.csp_model import KakuroCSP, RunConstraint, Variable
from task3_kakuro.solvers.combinations import digit_sets
from task3_kakuro.solvers.trace import SolverTrace

Domains = Dict[Variable, FrozenSet[int]]


def has_perfect_matching(cells: Sequence[Variable], digits: FrozenSet[int], domains: Domains) -> bool:
    """Can every cell get a DIFFERENT digit from `digits` within its own domain? (augmenting paths, Kuhn)"""
    owner: Dict[int, int] = {}

    def try_assign(i: int, seen: set) -> bool:
        for digit in domains[cells[i]] & digits:
            if digit in seen:
                continue
            seen.add(digit)
            if digit not in owner or try_assign(owner[digit], seen):
                owner[digit] = i
                return True
        return False

    return all(try_assign(i, set()) for i in range(len(cells)))


class Propagator:
    def __init__(self, csp: KakuroCSP):
        self.csp = csp
        self.revisions = 0
        self.pruned_values = 0

    # ------------------------------------------------------------------ GAC
    def revise(self, constraint: RunConstraint, domains: Domains) -> Optional[Dict[Variable, FrozenSet[int]]]:
        """REVISE for one run. Returns {cell: removed values}, or None on a domain wipe-out."""
        self.revisions += 1
        cells = constraint.cells
        supported: Dict[Variable, set] = {cell: set() for cell in cells}
        for digits in digit_sets(len(cells), constraint.total):
            if any(not (domains[cell] & digits) for cell in cells):
                continue
            if not has_perfect_matching(cells, digits, domains):
                continue
            for index, cell in enumerate(cells):
                others = cells[:index] + cells[index + 1:]
                for value in (domains[cell] & digits) - supported[cell]:
                    if has_perfect_matching(others, digits - {value}, domains):
                        supported[cell].add(value)
        removed = {}
        for cell in cells:
            lost = domains[cell] - supported[cell]
            if lost:
                removed[cell] = frozenset(lost)
                domains[cell] = frozenset(supported[cell])
                self.pruned_values += len(lost)
                if not domains[cell]:
                    return None
        return removed

    def gac3(self, domains: Domains, queue_constraints: Iterable[RunConstraint], trace: Optional[SolverTrace],
             assignment: Dict[Variable, int], depth: int) -> bool:
        """AC-3 loop: when a cell loses values, every OTHER run containing that cell is re-queued."""
        queue = deque(queue_constraints)
        in_queue = {c.index for c in queue}
        while queue:
            constraint = queue.popleft()
            in_queue.discard(constraint.index)
            removed = self.revise(constraint, domains)
            if removed is None:
                if trace is not None:
                    trace.record("wipeout", f"Domain wipe-out in {constraint}", depth, domains, assignment,
                                 constraint=constraint.index)
                return False
            if removed and trace is not None:
                detail = ", ".join(f"{cell}-{sorted(vals)}" for cell, vals in removed.items())
                trace.record("revise", f"Revise {constraint}: removed {detail}", depth, domains, assignment,
                             constraint=constraint.index, removed=removed)
            for cell in removed:
                for other in self.csp.constraints_of[cell]:
                    if other.index != constraint.index and other.index not in in_queue:
                        queue.append(other)
                        in_queue.add(other.index)
        return True

    # ------------------------------------------------------------------ forward checking
    def forward_check(self, variable: Variable, domains: Domains, assignment: Dict[Variable, int],
                      trace: Optional[SolverTrace], depth: int) -> bool:
        for constraint in self.csp.constraints_of[variable]:
            removed = {}
            for cell in constraint.cells:
                if cell in assignment:
                    continue
                keep = frozenset(v for v in domains[cell]
                                 if constraint.is_consistent({**self._run_assignment(constraint, assignment), cell: v}))
                if keep != domains[cell]:
                    removed[cell] = domains[cell] - keep
                    self.pruned_values += len(removed[cell])
                    domains[cell] = keep
                    if not keep:
                        if trace is not None:
                            trace.record("wipeout", f"Forward checking empties {cell}", depth, domains, assignment,
                                         constraint=constraint.index)
                        return False
            if removed and trace is not None:
                detail = ", ".join(f"{cell}-{sorted(vals)}" for cell, vals in removed.items())
                trace.record("revise", f"Forward check {constraint}: removed {detail}", depth, domains, assignment,
                             constraint=constraint.index, removed=removed)
        return True

    @staticmethod
    def _run_assignment(constraint: RunConstraint, assignment: Dict[Variable, int]) -> Dict[Variable, int]:
        return {cell: assignment[cell] for cell in constraint.cells if cell in assignment}

    def all_constraints(self) -> List[RunConstraint]:
        return list(self.csp.constraints)
