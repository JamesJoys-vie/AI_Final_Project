"""CLI: solve N-Queens with Glucose3.
Usage:
    python run_sat.py --n 8
    python run_sat.py --ns 4 8 16 32 64
"""
import argparse

from nqueens.benchmark import SATBenchmark
from nqueens.sat_solver import GlucoseQueenSolver


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, help="solve a single instance and print result")
    p.add_argument("--ns", type=int, nargs="+", help="benchmark several sizes")
    p.add_argument("--column-alo", action="store_true", help="add redundant at-least-one-per-column clauses")
    p.add_argument("--show-board", action="store_true", help="force print board even for large N")
    a = p.parse_args()

    if a.n:
        res = GlucoseQueenSolver(a.column_alo).solve(a.n)
        if res.board and (a.n <= 32 or a.show_board):
            print(res.board.render())
        elif not res.satisfiable:
            print(f"N={a.n} is UNSATISFIABLE")
        print(f"N={a.n} | clauses={res.num_clauses:,} | solve={res.solve_time:.4f}s | "
              f"total={res.total_time:.4f}s | valid={res.board.is_valid_solution() if res.board else False}")
    else:
        ns = a.ns or [4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64]
        df = SATBenchmark(ns, a.column_alo).run()
        print("\nSummary Table:")
        print(df[["N", "variables", "clauses", "sat", "valid", "solve_s", "total_s"]].to_string(index=False))


if __name__ == "__main__":
    main()