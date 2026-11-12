"""
Experiments of Task 1.
(a) Glucose3: number of CNF clauses and running time for increasing N (N >= 4), per CNF encoding.
(b) Min-Conflicts: standard vs proposed heuristic, same N, same seeds (=> same initial boards),
    for both initial assignments (random / greedy).
Slow configurations are capped at a smaller N (SAT_MAX_N, MC_MAX_N) so the full run stays within minutes.
"""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from task1_nqueens.core.board import is_valid_solution
from task1_nqueens.logic.cnf_encoder import NQueensCnfEncoder
from task1_nqueens.solvers.min_conflicts import MinConflictsSolver
from task1_nqueens.solvers.sat_solver import SatNQueensSolver
from task1_nqueens.solvers.variable_selectors import MaxConflictTabuSelector, RandomConflictedSelector

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
SAT_SIZES = (4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 80, 100, 128, 160, 200)
MC_SIZES = (8, 16, 32, 64, 128, 256, 512, 1000, 2000, 5000, 10000)
INITS = ("random", "greedy")
MC_MAX_N = {"random": 5000, "greedy": 10000}
SAT_ENCODINGS = {  # name -> (at-most-one encoding, redundant column ALO)
    "pairwise": ("pairwise", False),
    "pairwise+alo": ("pairwise", True),
    "seqcounter": ("seqcounter", False),
    "seqcounter+alo": ("seqcounter", True),
}
DEFAULT_SAT_ENCODINGS = ("pairwise", "pairwise+alo", "seqcounter+alo")
# Largest N per encoding: plain pairwise search passes ~25 s at N=128, pairwise formulas exceed 3.5M clauses
# beyond N=128, and seqcounter without column ALO takes minutes at N=100.
SAT_MAX_N = {"pairwise": 100, "pairwise+alo": 128, "seqcounter": 64, "seqcounter+alo": 200}


def write_csv(rows: List[Dict], name: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / name
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


class SatExperiment:
    """
    Each encoding is (at-most-one encoding, column ALO). `solve_ms` = load + search, as before;
    seqcounter without column ALO is not in the default set because its search time explodes (minutes at N=100).
    Every configuration is solved `repeats` times and the median of each timing is reported
    (Glucose3 is deterministic, so the formula and the model are identical between repeats).
    """

    def __init__(self, sizes: Sequence[int] = SAT_SIZES, encodings: Sequence[str] = DEFAULT_SAT_ENCODINGS,
                 repeats: int = 3):
        self.sizes = sizes
        self.encodings = encodings
        self.repeats = repeats

    def run(self) -> List[Dict]:
        rows = []
        print(f"{'N':>5}  {'encoding':<16}{'variables':>10}{'clauses':>12}{'encode ms':>11}"
              f"{'load ms':>10}{'search ms':>11}{'solve ms':>11}  valid")
        for n in self.sizes:
            for encoding in self.encodings:
                if n > SAT_MAX_N[encoding]:
                    continue
                amo, column_alo = SAT_ENCODINGS[encoding]
                results = [SatNQueensSolver(amo, column_alo).solve(n) for _ in range(self.repeats)]
                result = results[0]
                assert result.clauses == NQueensCnfEncoder(n, amo, column_alo).clause_count()
                if encoding == "pairwise":
                    assert result.clauses == NQueensCnfEncoder.expected_clause_count(n)
                valid = all(is_valid_solution(r.columns) for r in results)

                def median_ms(key: str) -> float:
                    values = [r.elapsed if key == "solve" else r.extra[f"{key}_time"] for r in results]
                    return round(statistics.median(values) * 1000, 3)

                rows.append({"n": n, "encoding": encoding, "variables": result.variables,
                             "clauses": result.clauses, "repeats": self.repeats,
                             "encode_ms": median_ms("encode"), "load_ms": median_ms("load"),
                             "search_ms": median_ms("search"), "solve_ms": median_ms("solve"), "valid": valid})
                row = rows[-1]
                print(f"{n:>5}  {encoding:<16}{result.variables:>10,}{result.clauses:>12,}{row['encode_ms']:>11.2f}"
                      f"{row['load_ms']:>10.2f}{row['search_ms']:>11.2f}{row['solve_ms']:>11.2f}  {valid}")
        return rows


class MinConflictsExperiment:
    """Both strategies are run on the same seeds; within one `init` mode, the same seed gives the same start board."""

    def __init__(self, sizes: Sequence[int] = MC_SIZES, runs: int = 20, inits: Sequence[str] = INITS):
        self.sizes = sizes
        self.runs = runs
        self.inits = inits
        self.selectors = (RandomConflictedSelector, MaxConflictTabuSelector)

    def run(self) -> List[Dict]:
        rows = []
        print(f"{'N':>5}  {'init':<7}{'strategy':<34}{'success':>9}{'init pairs':>11}"
              f"{'mean steps':>12}{'median':>9}{'restarts':>9}{'mean ms':>10}{'median ms':>11}")
        for n in self.sizes:
            for init in self.inits:
                if n > MC_MAX_N[init]:
                    continue
                for selector_cls in self.selectors:
                    steps, times, initial, restarts, success = [], [], [], [], 0
                    for seed in range(self.runs):
                        result = MinConflictsSolver(selector_cls(), seed=seed, init=init).solve(n)
                        if result.solved and is_valid_solution(result.columns):
                            success += 1
                        steps.append(result.steps)
                        times.append(result.elapsed * 1000)
                        initial.append(result.extra["initial_pairs"])
                        restarts.append(result.restarts)
                    row = {"n": n, "init": init, "strategy": selector_cls.name, "runs": self.runs,
                           "success_rate": success / self.runs,
                           "mean_initial_pairs": round(statistics.mean(initial), 1),
                           "mean_steps": round(statistics.mean(steps), 1),
                           "median_steps": statistics.median(steps),
                           "mean_restarts": round(statistics.mean(restarts), 2),
                           "mean_ms": round(statistics.mean(times), 2),
                           "median_ms": round(statistics.median(times), 2),
                           "stdev_ms": round(statistics.pstdev(times), 2)}
                    rows.append(row)
                    print(f"{n:>5}  {init:<7}{row['strategy']:<34}{row['success_rate']:>8.0%}"
                          f"{row['mean_initial_pairs']:>11}{row['mean_steps']:>12}{row['median_steps']:>9}"
                          f"{row['mean_restarts']:>9}{row['mean_ms']:>10}{row['median_ms']:>11}")
        return rows


def plot(sat_rows: List[Dict], mc_rows: List[Dict]) -> Optional[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, grid = plt.subplots(2, 2, figsize=(13, 9))
    axes = grid.flatten()
    for encoding in dict.fromkeys(r["encoding"] for r in sat_rows):
        data = [r for r in sat_rows if r["encoding"] == encoding]
        ns = [r["n"] for r in data]
        axes[0].plot(ns, [r["clauses"] for r in data], marker="o", label=encoding)
        axes[1].plot(ns, [r["encode_ms"] + r["solve_ms"] for r in data], marker="o", label=encoding)
    axes[0].set_title("CNF clauses vs N")
    axes[0].legend(fontsize=8)
    axes[1].set_title("Glucose3 encode + solve time (ms)")
    axes[1].legend(fontsize=8)
    for init, strategy in sorted({(r["init"], r["strategy"]) for r in mc_rows}):
        data = [r for r in mc_rows if r["strategy"] == strategy and r["init"] == init]
        style = {"marker": "o", "linestyle": "-" if init == "random" else "--", "label": f"{strategy}, {init} init"}
        axes[2].plot([r["n"] for r in data], [r["mean_steps"] for r in data], **style)
        axes[3].plot([r["n"] for r in data], [r["median_ms"] for r in data], **style)
    axes[2].set_title("Min-Conflicts mean steps")
    axes[3].set_title("Min-Conflicts median time (ms)")
    for ax in axes[2:]:
        ax.set_xscale("log")
        ax.legend(fontsize=7)
    for ax in axes:
        ax.set_xlabel("N")
        ax.set_yscale("log")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    path = RESULTS_DIR / "nqueens_experiments.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="N-Queens experiments")
    parser.add_argument("--runs", type=int, default=20, help="Min-Conflicts runs per N and strategy")
    parser.add_argument("--sat-max", type=int, default=200, help="largest SAT N (per-encoding caps still apply)")
    parser.add_argument("--sat-repeats", type=int, default=3, help="SAT timings are the median of this many runs")
    parser.add_argument("--mc-max", type=int, default=10000,
                        help="largest Min-Conflicts N (per-init caps still apply)")
    parser.add_argument("--init", choices=("random", "greedy", "both"), default="both",
                        help="Min-Conflicts initial assignment (default: run both)")
    parser.add_argument("--sat-encodings", nargs="+", choices=tuple(SAT_ENCODINGS), default=DEFAULT_SAT_ENCODINGS,
                        help="CNF encodings to compare (default: pairwise pairwise+alo seqcounter+alo)")
    args = parser.parse_args(argv)
    inits = INITS if args.init == "both" else (args.init,)
    sat_rows = SatExperiment([n for n in SAT_SIZES if n <= args.sat_max], args.sat_encodings,
                             args.sat_repeats).run()
    mc_rows = MinConflictsExperiment([n for n in MC_SIZES if n <= args.mc_max], args.runs, inits).run()
    print("CSV :", write_csv(sat_rows, "sat_glucose3.csv"), write_csv(mc_rows, "min_conflicts.csv"))
    print("Plot:", plot(sat_rows, mc_rows))


if __name__ == "__main__":
    main()
