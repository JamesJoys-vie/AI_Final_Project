"""CLI: Min-Conflicts.   python run_min_conflicts.py --n 100 --strategy max_conflict"""
import argparse

from nqueens import MaxConflictSelector, MinConflictsSolver, RandomConflictedSelector


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--strategy", choices=["standard", "max_conflict"], default="max_conflict")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=100_000)
    a = p.parse_args()
    sel = RandomConflictedSelector() if a.strategy == "standard" else MaxConflictSelector()
    res = MinConflictsSolver(sel, a.max_steps).solve(a.n, seed=a.seed)
    if a.n <= 32:
        print(res.board.render())
    print(f"strategy={res.strategy} solved={res.solved} steps={res.steps} time={res.time:.4f}s "
          f"valid={res.board.is_valid_solution()}")


if __name__ == "__main__":
    main()
