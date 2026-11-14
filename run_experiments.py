"""Reproduce every table / figure of Task 1 -> results/*.csv, results/*.png"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from nqueens.benchmark import MinConflictsBenchmark, SATBenchmark
from nqueens.plots import plot_min_conflicts, plot_sat


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sat-ns", type=int, nargs="+", default=[4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64])
    p.add_argument("--mc-ns", type=int, nargs="+", default=[8, 16, 32, 64, 128, 256, 512, 1000, 2000])
    p.add_argument("--runs", type=int, default=30)
    p.add_argument("--out", default="results")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(exist_ok=True)

    sat = SATBenchmark(a.sat_ns).run()
    sat.to_csv(out / "sat_results.csv", index=False)
    plot_sat(sat).savefig(out / "sat_results.png", dpi=150)

    raw, summary = MinConflictsBenchmark(a.mc_ns, runs=a.runs).run()
    raw.to_csv(out / "mc_raw.csv", index=False)
    summary.to_csv(out / "mc_summary.csv", index=False)
    plot_min_conflicts(summary).savefig(out / "mc_results.png", dpi=150)
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
