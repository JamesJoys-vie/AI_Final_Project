"""Experiment runners that return pandas DataFrames."""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

import pandas as pd

from .cnf_encoder import NQueensCNFEncoder
from .min_conflicts import (MaxConflictSelector, MinConflictsSolver,
                            RandomConflictedSelector, VariableSelector)


def count_clauses(ns: Iterable[int], add_column_alo: bool = False) -> pd.DataFrame:
    """Clause statistics only (no SAT solver needed)."""
    rows = []
    for n in ns:
        cnf = NQueensCNFEncoder(n, add_column_alo).encode()
        rows.append({"N": n, "variables": cnf.num_vars, "clauses": cnf.num_clauses, **cnf.stats})
    return pd.DataFrame(rows)


class SATBenchmark:
    """Glucose3 on increasing N: #clauses and running time."""

    def __init__(self, ns: Iterable[int], add_column_alo: bool = False):
        self.ns = list(ns)
        self.add_column_alo = add_column_alo

    def run(self, verbose: bool = True) -> pd.DataFrame:
        from .sat_solver import GlucoseQueenSolver  # lazy: needs python-sat
        solver = GlucoseQueenSolver(self.add_column_alo)
        rows = []
        for n in self.ns:
            res = solver.solve(n)
            ok = res.board.is_valid_solution() if res.board else False
            rows.append({"N": n, "variables": res.num_vars, "clauses": res.num_clauses,
                         "sat": res.satisfiable, "valid": ok,
                         "encode_s": res.encode_time, "load_s": res.load_time,
                         "solve_s": res.solve_time, "total_s": res.total_time,
                         "conflicts": res.conflicts, "decisions": res.decisions})
            if verbose:
                print(f"N={n:>4} | clauses={res.num_clauses:>9,} | solve={res.solve_time:8.4f}s "
                      f"| total={res.total_time:8.3f}s | valid={ok}")
        return pd.DataFrame(rows)


class MinConflictsBenchmark:
    """Standard vs heuristic variable selection; same seeds -> same initial boards (fair)."""

    def __init__(self, ns: Iterable[int], runs: int = 30, max_steps: int = 100_000, base_seed: int = 2024,
                 selectors: Optional[Dict[str, VariableSelector]] = None):
        self.ns = list(ns)
        self.runs = runs
        self.max_steps = max_steps
        self.base_seed = base_seed
        self.selectors = selectors or {"standard": RandomConflictedSelector(),
                                       "max_conflict": MaxConflictSelector()}

    def run(self, verbose: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
        raw = []
        for n in self.ns:
            for name, selector in self.selectors.items():
                solver = MinConflictsSolver(selector, self.max_steps)
                for i in range(self.runs):
                    res = solver.solve(n, seed=self.base_seed + i)
                    raw.append({"N": n, "strategy": name, "seed": res.seed, "solved": res.solved,
                                "valid": res.board.is_valid_solution(), "steps": res.steps, "time_s": res.time})
            if verbose:
                print(f"finished N={n}")
        raw_df = pd.DataFrame(raw)
        return raw_df, self.summarize(raw_df)

    @staticmethod
    def summarize(raw_df: pd.DataFrame) -> pd.DataFrame:
        solved = raw_df[raw_df["solved"]]
        g = raw_df.groupby(["N", "strategy"])
        out = g.agg(success_rate=("solved", "mean")).join(
            solved.groupby(["N", "strategy"]).agg(
                mean_steps=("steps", "mean"), median_steps=("steps", "median"),
                mean_time_s=("time_s", "mean"), std_time_s=("time_s", "std")))
        return out.reset_index()
