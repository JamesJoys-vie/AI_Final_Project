"""Solves N-Queens by handing the CNF formula to Glucose3 (PySAT), a CDCL SAT solver."""
from __future__ import annotations

import time
from typing import Iterable, Tuple

from task1_nqueens.logic.cnf_encoder import NQueensCnfEncoder
from task1_nqueens.solvers.solve_result import SolveResult


class SatNQueensSolver:
    """
    `amo` selects the at-most-one encoding ("pairwise" or "seqcounter"), `column_alo` adds the
    redundant "at least one queen per column" clauses (see NQueensCnfEncoder).
    """

    def __init__(self, amo: str = "pairwise", column_alo: bool = False):
        NQueensCnfEncoder(1, amo, column_alo)  # validates the options early
        self.amo = amo
        self.column_alo = column_alo

    @property
    def name(self) -> str:
        if self.amo == "pairwise" and not self.column_alo:
            return "Glucose3 (PySAT)"
        return f"Glucose3 (PySAT, {NQueensCnfEncoder(1, self.amo, self.column_alo).label})"

    def solve(self, n: int, fixed_queens: Iterable[Tuple[int, int]] = ()) -> SolveResult:
        """
        `fixed_queens` are passed as SAT assumptions: the solver must keep them (used by "Complete my board").
        Timing: `elapsed` = load (adding clauses to Glucose3) + search; both are also reported in `extra`.
        """
        from pysat.solvers import Glucose3

        start = time.perf_counter()
        encoder = NQueensCnfEncoder(n, self.amo, self.column_alo)
        formula = encoder.encode()
        encode_time = time.perf_counter() - start
        assumptions = [encoder.mapper.to_variable(row, col) for row, col in fixed_queens]

        load_start = time.perf_counter()
        with Glucose3(bootstrap_with=formula.clauses) as solver:
            search_start = time.perf_counter()
            satisfiable = solver.solve(assumptions=assumptions)
            search_time = time.perf_counter() - search_start
            model = solver.get_model() if satisfiable else None
        load_time = search_start - load_start

        columns = None
        if model:
            # Positive literals among the N^2 square variables are squares holding a queen
            # (auxiliary sequential-counter variables have ids > N^2 and are ignored).
            square_vars = n * n
            columns = [-1] * n
            for literal in model:
                if 0 < literal <= square_vars:
                    row, col = encoder.mapper.to_cell(literal)
                    columns[row] = col
        return SolveResult(self.name, n, bool(satisfiable), columns, load_time + search_time, 0,
                           len(formula.clauses), formula.variable_count,
                           {"encode_time": encode_time, "load_time": load_time, "search_time": search_time,
                            **formula.clauses_by_kind})
