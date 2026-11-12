"""Solves N-Queens by handing the CNF formula to Glucose3 (PySAT), a CDCL SAT solver."""
from __future__ import annotations

import time
from typing import Iterable, Tuple

from task1_nqueens.logic.cnf_encoder import NQueensCnfEncoder
from task1_nqueens.solvers.solve_result import SolveResult


class SatNQueensSolver:
    name = "Glucose3 (PySAT)"

    def solve(self, n: int, fixed_queens: Iterable[Tuple[int, int]] = ()) -> SolveResult:
        """
        `fixed_queens` are passed as SAT assumptions: the solver must keep them (used by "Complete my board").
        """
        from pysat.solvers import Glucose3

        start = time.perf_counter()
        encoder = NQueensCnfEncoder(n)
        formula = encoder.encode()
        encode_time = time.perf_counter() - start
        assumptions = [encoder.mapper.to_variable(row, col) for row, col in fixed_queens]

        solve_start = time.perf_counter()
        with Glucose3(bootstrap_with=formula.clauses) as solver:
            satisfiable = solver.solve(assumptions=assumptions)
            model = solver.get_model() if satisfiable else None
        solve_time = time.perf_counter() - solve_start

        columns = None
        if model:
            # Positive literals in the model are squares holding a queen.
            columns = [-1] * n
            for literal in model:
                if literal > 0:
                    row, col = encoder.mapper.to_cell(literal)
                    columns[row] = col
        return SolveResult(self.name, n, bool(satisfiable), columns, solve_time, 0,
                           len(formula.clauses), formula.variable_count,
                           {"encode_time": encode_time, **formula.clauses_by_kind})
