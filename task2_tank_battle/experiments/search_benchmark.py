"""
Experiment 1 - compare the 4 search configurations on the same scenarios and depths.
Metrics: time, generated nodes, evaluated leaves, prunings, effective branching factor, root value.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

from task2_tank_battle.agents.search_agent import SEARCH_CONFIGS, create_search_agent
from task2_tank_battle.experiments.scenarios import build_scenarios

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


class SearchBenchmark:
    def __init__(self, depths=(1, 2, 3, 4), minimax_max_depth: int = 4, seed: int = 2024):
        self.depths = depths
        self.minimax_max_depth = minimax_max_depth
        self.seed = seed

    def run(self, verbose: bool = True) -> List[Dict]:
        rows = []
        for scenario_name, state in build_scenarios().items():
            for depth in self.depths:
                root_values = {}
                for config in SEARCH_CONFIGS:
                    if "Minimax" in config and depth > self.minimax_max_depth:
                        continue
                    agent = create_search_agent(config, depth, None, self.seed)
                    # Same shuffled root order for every configuration -> fair comparison.
                    actions = list(agent.search.rules.legal_actions(state, 0))
                    random.Random(self.seed).shuffle(actions)
                    action, value, stats = agent.search.search(state, 0, depth, None, actions)
                    root_values[config] = value
                    row = {"scenario": scenario_name, "config": config, "action": action.name, **stats.as_dict()}
                    rows.append(row)
                    if verbose:
                        print(f"{scenario_name:8s} d={depth} {config:22s} {action.name:10s} "
                              f"nodes={stats.nodes_generated:>9,} time={row['time_ms']:>10.1f} ms "
                              f"prunes={stats.prunings:>7,} ebf={row['ebf']:.2f} value={row['value']}")
                self._check_same_value(root_values, "Minimax", "Alpha-Beta")
                self._check_same_value(root_values, "Heuristic Minimax", "Heuristic Alpha-Beta")
        return rows

    @staticmethod
    def _check_same_value(values: Dict[str, float], a: str, b: str) -> None:
        """Alpha-Beta must return exactly the Minimax value (pruning never changes the result)."""
        if a in values and b in values and abs(values[a] - values[b]) > 1e-9:
            raise AssertionError(f"{a} = {values[a]} but {b} = {values[b]}")

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
        for config in SEARCH_CONFIGS:
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


def main() -> None:
    benchmark = SearchBenchmark()
    rows = benchmark.run()
    print("CSV :", benchmark.save(rows))
    print("Plot:", benchmark.plot(rows))


if __name__ == "__main__":
    main()
