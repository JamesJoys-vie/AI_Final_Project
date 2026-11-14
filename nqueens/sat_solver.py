"""Solve N-Queens with the Glucose3 SAT solver from PySAT."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

try:
    from pysat.solvers import Glucose3  # type: ignore
except ImportError:
    Glucose3 = None

from .board import Board
from .cnf_encoder import NQueensCNFEncoder

@dataclass
class SATResult:
    n: int
    satisfiable: bool
    board: Optional[Board]
    num_vars: int
    num_clauses: int
    encode_time: float
    load_time: float
    solve_time: float
    conflicts: int = 0
    decisions: int = 0
    propagations: int = 0

    @property
    def total_time(self) -> float:
        return self.encode_time + self.load_time + self.solve_time


class GlucoseQueenSolver:
    def __init__(self, add_column_alo: bool = False):
        if Glucose3 is None:
            raise ImportError("PySAT is not installed. Run: pip install python-sat")
        self.add_column_alo = add_column_alo

    def solve(self, n: int) -> SATResult:
        encoder = NQueensCNFEncoder(n, self.add_column_alo)

        # 1. Encode CNF
        t0 = time.perf_counter()
        cnf = encoder.encode()
        encode_time = time.perf_counter() - t0

        # 2. Load into Glucose3 using fast C-level append_formula
        with Glucose3() as solver:
            t0 = time.perf_counter()
            solver.append_formula(cnf.clauses)
            load_time = time.perf_counter() - t0

            # 3. Solve
            t0 = time.perf_counter()
            sat = solver.solve()
            solve_time = time.perf_counter() - t0

            model = solver.get_model() if sat else None
            stats = solver.accum_stats() or {}

        board = None
        if sat and model:
            board = Board(n, [encoder.mapper.cell(v) for v in model if v > 0])

        return SATResult(
            n=n, satisfiable=sat, board=board, num_vars=cnf.num_vars, num_clauses=cnf.num_clauses,
            encode_time=encode_time, load_time=load_time, solve_time=solve_time,
            conflicts=stats.get("conflicts", 0), decisions=stats.get("decisions", 0),
            propagations=stats.get("propagations", 0),
        )