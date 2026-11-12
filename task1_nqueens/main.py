"""
Entry point of Task 1. Run from the `source` folder:
    python -m task1_nqueens                    -> interactive GUI
    python -m task1_nqueens sat 8              -> solve N=8 with Glucose3 and print the board
    python -m task1_nqueens minconflicts 64    -> standard vs heuristic Min-Conflicts on N=64
    python -m task1_nqueens benchmark --runs 20
"""
from __future__ import annotations

import sys
from typing import List, Optional, Sequence


def print_board(columns: List[int]) -> None:
    n = len(columns)
    for row in range(n):
        print(" ".join("Q" if columns[row] == col else "." for col in range(n)))


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv.pop(0) if argv else "gui"
    n = int(argv[0]) if argv and argv[0].isdigit() else 8

    if command == "sat":
        from task1_nqueens.solvers.sat_solver import SatNQueensSolver
        result = SatNQueensSolver().solve(n)
        print(result.summary())
        if n <= 30:
            print_board(result.columns)
    elif command == "minconflicts":
        from task1_nqueens.solvers.min_conflicts import MinConflictsSolver
        from task1_nqueens.solvers.variable_selectors import MaxConflictTabuSelector, RandomConflictedSelector
        for selector in (RandomConflictedSelector(), MaxConflictTabuSelector()):
            print(MinConflictsSolver(selector, seed=0).solve(n).summary())
    elif command == "benchmark":
        from task1_nqueens.experiments.benchmark import main as run_benchmark
        run_benchmark(argv)
    elif command == "gui":
        import pygame
        from task1_nqueens.ui.nqueens_app import NQueensApp
        NQueensApp().run()
        pygame.quit()
    else:
        print(f"Unknown command '{command}'. Use: gui | sat N | minconflicts N | benchmark")


if __name__ == "__main__":
    main()
