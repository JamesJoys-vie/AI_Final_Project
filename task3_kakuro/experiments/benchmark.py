"""
Experiments of Task 3: correctness (every solution is re-checked), stability (10 shuffled variable
orders per configuration) and effectiveness (assignments, backtracks, pruned values, time).
"""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from task3_kakuro.core.csp_model import KakuroCSP
from task3_kakuro.core.puzzle import PuzzleLoader
from task3_kakuro.solvers.backtracking import BacktrackingSolver, SolverConfig

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# From the weakest to the strongest combination of techniques.
EXPERIMENT_CONFIGS = (
    SolverConfig("none", False, False, False, False),
    SolverConfig("fc", False, False, False, False),
    SolverConfig("fc", True, False, False, False),
    SolverConfig("fc", True, True, True, False),
    SolverConfig("mac", False, False, False, False),
    SolverConfig("mac", True, True, True, False),
    SolverConfig("mac", True, True, True, True),
)


def config_name(config: SolverConfig) -> str:
    return config.label + (" + initial GAC" if config.preprocess else "")


class KakuroBenchmark:
    def __init__(self, puzzles: Sequence[str], seeds: int = 10, node_limit: int = 200_000):
        self.puzzles = puzzles
        self.seeds = seeds
        self.node_limit = node_limit

    def run(self) -> List[Dict]:
        rows = []
        for name in self.puzzles:
            csp = KakuroCSP(PuzzleLoader.load(name))
            print(f"\n{name}: {len(csp.variables)} variables, {len(csp.constraints)} run constraints")
            print(f"  {'configuration':<52}{'solved':>8}{'assign':>10}{'backtr.':>10}{'pruned':>10}{'ms':>10}")
            for config in EXPERIMENT_CONFIGS:
                runs = [BacktrackingSolver(config, self.node_limit, seed).solve(csp) for seed in range(self.seeds)]
                solutions = {tuple(sorted(r.solution.items())) for r in runs if r.solved}
                row = {
                    "puzzle": name, "config": config_name(config), "runs": self.seeds,
                    "solved_rate": sum(r.solved for r in runs) / self.seeds,
                    "distinct_solutions": len(solutions),
                    "mean_assignments": round(statistics.mean(r.assignments for r in runs), 1),
                    "stdev_assignments": round(statistics.pstdev(r.assignments for r in runs), 1),
                    "mean_backtracks": round(statistics.mean(r.backtracks for r in runs), 1),
                    "mean_pruned": round(statistics.mean(r.pruned_values for r in runs), 1),
                    "mean_ms": round(statistics.mean(r.elapsed * 1000 for r in runs), 2),
                    "stdev_ms": round(statistics.pstdev(r.elapsed * 1000 for r in runs), 2),
                }
                rows.append(row)
                print(f"  {row['config']:<52}{row['solved_rate']:>7.0%}{row['mean_assignments']:>10}"
                      f"{row['mean_backtracks']:>10}{row['mean_pruned']:>10}{row['mean_ms']:>10}")
        return rows

    @staticmethod
    def save(rows: List[Dict]) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / "kakuro_benchmark.csv"
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path


def plot(rows: List[Dict]) -> Optional[Path]:
    """Bar chart of mean assignments per configuration (log scale), one group per puzzle."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    puzzles = sorted({r["puzzle"] for r in rows})
    configs = [r["config"] for r in rows if r["puzzle"] == puzzles[0]]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    width = 0.8 / len(puzzles)
    for i, puzzle in enumerate(puzzles):
        values = [float(r["mean_assignments"]) for r in rows if r["puzzle"] == puzzle]
        ax.bar([k + i * width for k in range(len(configs))], values, width, label=puzzle)
    ax.set_xticks([k + width * (len(puzzles) - 1) / 2 for k in range(len(configs))])
    ax.set_xticklabels([c.replace("BT + ", "").replace(" + ", "\n") for c in configs], fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("Mean assignments (10 shuffled orders)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = RESULTS_DIR / "kakuro_benchmark.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def print_solution(name: str) -> None:
    csp = KakuroCSP(PuzzleLoader.load(name))
    stats = BacktrackingSolver().solve(csp)
    puzzle = csp.puzzle
    print(f"{name}: {'valid solution' if stats.solved else 'no solution'} "
          f"({stats.assignments} assignments, {stats.elapsed * 1000:.2f} ms)")
    for row in range(puzzle.rows):
        print("  " + " ".join(str(stats.solution[(row, col)]) if stats.solution and (row, col) in stats.solution
                              else "#" for col in range(puzzle.cols)))


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Kakuro solver experiments")
    parser.add_argument("--puzzles", nargs="*", default=PuzzleLoader.available())
    parser.add_argument("--seeds", type=int, default=10)
    args = parser.parse_args(argv)
    for name in args.puzzles:
        print_solution(name)
    benchmark = KakuroBenchmark(args.puzzles, args.seeds)
    rows = benchmark.run()
    print("\nCSV:", benchmark.save(rows))
    print("Plot:", plot(rows))


if __name__ == "__main__":
    main()
