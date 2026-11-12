"""
Experiment 1 - compare the 4 search configurations on the same scenarios and depths.
Metrics: time (median of several runs), generated nodes, nodes per second, evaluated leaves, prunings,
transposition-table hits, effective branching factor, root value.
With --ablation, Heuristic Alpha-Beta is also run with its enhancements switched on one at a time.
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from task2_tank_battle.agents.search_agent import ABLATION_CONFIGS, SEARCH_CONFIGS, create_search_agent
from task2_tank_battle.ai.search import MinimaxSearch
from task2_tank_battle.experiments.scenarios import build_scenarios

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


class SearchBenchmark:
    """
    Every (scenario, depth, configuration) search is repeated `repeats` times and the MEDIAN time is reported,
    so one slow run (GC, OS scheduling) does not distort the comparison. Searches whose first run already
    takes longer than `long_run_seconds` are run only once (deep plain Minimax takes many seconds).
    """

    def __init__(self, depths=(1, 2, 3, 4), minimax_max_depth: int = 4, seed: int = 2024,
                 repeats: int = 5, long_run_seconds: float = 1.0, configs: Optional[Sequence[str]] = None):
        self.configs = list(configs or SEARCH_CONFIGS)
        self.depths = depths
        self.minimax_max_depth = minimax_max_depth
        self.seed = seed
        self.repeats = max(1, repeats)
        self.long_run_seconds = long_run_seconds

    def _timed_search(self, agent, state, depth: int, actions):
        """Return (action, value, stats of the first run, median elapsed seconds, number of runs)."""
        action, value, stats = agent.search.search(state, 0, depth, None, list(actions))
        times = [stats.elapsed]
        if stats.elapsed < self.long_run_seconds:
            for _ in range(self.repeats - 1):
                again_action, again_value, again_stats = agent.search.search(state, 0, depth, None, list(actions))
                if (again_action, again_value, again_stats.nodes_generated) != (action, value, stats.nodes_generated):
                    raise AssertionError("search is not deterministic for the same root order")
                times.append(again_stats.elapsed)
        return action, value, stats, statistics.median(times), len(times)

    def run(self, verbose: bool = True) -> List[Dict]:
        rows = []
        for scenario_name, state in build_scenarios().items():
            for depth in self.depths:
                root_values = {}
                for config in self.configs:
                    if self._config(config)[0] is MinimaxSearch and depth > self.minimax_max_depth:
                        continue
                    agent = create_search_agent(config, depth, None, self.seed)
                    # Same shuffled root order for every configuration -> fair comparison.
                    actions = list(agent.search.rules.legal_actions(state, 0))
                    random.Random(self.seed).shuffle(actions)
                    action, value, stats, elapsed, runs = self._timed_search(agent, state, depth, actions)
                    stats.elapsed = elapsed
                    root_values[config] = value
                    row = {"scenario": scenario_name, "config": config, "action": action.name, **stats.as_dict(),
                           "nodes_per_sec": round(stats.nodes_generated / elapsed) if elapsed > 0 else 0,
                           "runs": runs}
                    rows.append(row)
                    if verbose:
                        print(f"{scenario_name:8s} d={depth} {config:22s} {action.name:10s} "
                              f"nodes={stats.nodes_generated:>9,} time={row['time_ms']:>10.1f} ms "
                              f"nodes/s={row['nodes_per_sec']:>9,} prunes={stats.prunings:>7,} "
                              f"ebf={row['ebf']:.2f} value={row['value']}", flush=True)
                self._check_same_value(root_values, scenario_name, depth)
        return rows

    @staticmethod
    def _config(name: str):
        return SEARCH_CONFIGS.get(name) or ABLATION_CONFIGS[name]

    def _check_same_value(self, values: Dict[str, float], scenario: str, depth: int) -> None:
        """
        Configurations with the same evaluator must return exactly the same root value: Alpha-Beta and
        its enhancements prune and reorder the tree but never change the Minimax result.
        """
        by_evaluator: Dict[type, Dict[str, float]] = {}
        for config, value in values.items():
            by_evaluator.setdefault(self._config(config)[1], {})[config] = value
        for group in by_evaluator.values():
            if max(group.values()) - min(group.values()) > 1e-9:
                raise AssertionError(f"{scenario} d={depth}: root values differ {group}")

    @staticmethod
    def save(rows: List[Dict], path: Optional[Path] = None) -> Path:
        path = path or RESULTS_DIR / "search_benchmark.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def plot(rows: List[Dict], path: Optional[Path] = None) -> Optional[Path]:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return None
        path = path or RESULTS_DIR / "search_benchmark.png"

        def average(config: str, depth: int, key: str) -> float:
            values = [r[key] for r in rows if r["config"] == config and r["depth_cycles"] == depth]
            return sum(values) / len(values)

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        for config in dict.fromkeys(r["config"] for r in rows):
            depths = sorted({r["depth_cycles"] for r in rows if r["config"] == config})
            axes[0].plot(depths, [average(config, d, "nodes_generated") for d in depths], marker="o", label=config)
            axes[1].plot(depths, [average(config, d, "time_ms") for d in depths], marker="o", label=config)
        for ax, title in zip(axes, ("Generated nodes (avg)", "Time per decision, ms (avg)")):
            ax.set_yscale("log")
            ax.set_xlabel("Search depth (game cycles, 1 cycle = 2 plies)")
            ax.set_title(title)
            ax.grid(alpha=0.3)
        axes[0].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Compare the 4 search configurations on fixed scenarios")
    parser.add_argument("--depths", type=int, nargs="+", default=[1, 2, 3, 4])
    parser.add_argument("--minimax-max-depth", type=int, default=4,
                        help="skip (Heuristic) Minimax above this depth (it grows as 36^depth)")
    parser.add_argument("--repeats", type=int, default=5, help="runs per search; the median time is reported")
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--configs", nargs="+", default=None,
                        help=f"configurations to run (default: the 4 project configurations); "
                             f"ablation names: {', '.join(ABLATION_CONFIGS)}")
    parser.add_argument("--ablation", action="store_true",
                        help="also run Heuristic Alpha-Beta with its enhancements added one at a time")
    parser.add_argument("--output", default=None, help="CSV path (the plot is saved next to it)")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args(argv)

    configs = list(args.configs or SEARCH_CONFIGS)
    if args.ablation:
        configs += [name for name in ABLATION_CONFIGS if name not in configs]
    benchmark = SearchBenchmark(tuple(args.depths), args.minimax_max_depth, args.seed, args.repeats,
                                configs=configs)
    rows = benchmark.run()
    csv_path = benchmark.save(rows, Path(args.output) if args.output else None)
    print("CSV :", csv_path)
    if not args.no_plot:
        print("Plot:", benchmark.plot(rows, csv_path.with_suffix(".png")))


if __name__ == "__main__":
    main()
