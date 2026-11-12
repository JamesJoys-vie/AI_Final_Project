"""
Experiment 3 - real-time play: how deep does each configuration search within a fixed time budget?

Every agent decides exactly as in the GUI and the tournament: iterative deepening (depth 1, 2, 3, ...) until
the deadline, keeping the deepest COMPLETED search. The same states, budgets and seeds are used for every
configuration. Metrics per decision: completed depth, generated nodes, wall time.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from task2_tank_battle.agents.search_agent import SEARCH_CONFIGS, create_search_agent
from task2_tank_battle.core.game_rules import WIN_SCORE
from task2_tank_battle.core.game_state import GameState
from task2_tank_battle.core.map_loader import MapLoader, build_initial_state
from task2_tank_battle.experiments.plot_style import INK, MUTED, SURFACE, color_of, style_axes
from task2_tank_battle.experiments.scenarios import build_scenarios

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
DEFAULT_BUDGETS = (0.05, 0.15, 0.5)


def experiment_states(seed: int = 2024) -> Dict[str, GameState]:
    """The 4 benchmark scenarios, the start of every bundled map and 3 random maps (13, 17, 21 cells)."""
    states = dict(build_scenarios())
    for name in MapLoader.available_maps():
        states[f"map:{name}"] = MapLoader.load(name)
    for size in (13, 17, 21):
        map_name = "Random symmetric" if size == 13 else f"Random symmetric {size}x{size}"
        states[f"random {size}x{size}"] = build_initial_state(map_name, seed)
    return states


class DepthBudgetExperiment:
    def __init__(self, budgets: Sequence[float] = DEFAULT_BUDGETS, configs: Optional[Sequence[str]] = None,
                 max_depth: int = 12, repeats: int = 3, seed: int = 2024):
        self.budgets = tuple(budgets)
        self.configs = list(configs or SEARCH_CONFIGS)
        self.max_depth = max_depth
        self.repeats = max(1, repeats)
        self.seed = seed

    def decide(self, config: str, state: GameState, budget: float) -> Dict:
        """One timed decision of player 1 (fresh agent, as at the start of a match)."""
        agent = create_search_agent(config, self.max_depth, budget, self.seed)
        agent.reset(0)
        start = time.perf_counter()
        agent.choose_action(state, 0)
        elapsed = time.perf_counter() - start
        stats = agent.last_stats
        return {"depth": stats.depth if stats is not None else 0,
                "nodes": stats.nodes_generated if stats is not None else 0,
                "time_ms": elapsed * 1000,
                "decided": stats is not None and abs(stats.value) >= WIN_SCORE / 2}

    def run(self, verbose: bool = True, states: Optional[Dict[str, GameState]] = None) -> List[Dict]:
        """Median over `repeats` decisions (timing noise can move the last completed depth by one)."""
        rows = []
        for state_name, state in (states or experiment_states(self.seed)).items():
            for budget in self.budgets:
                for config in self.configs:
                    runs = [self.decide(config, state, budget) for _ in range(self.repeats)]
                    row = {"state": state_name, "budget_ms": round(budget * 1000), "config": config,
                           "depth": statistics.median(r["depth"] for r in runs),
                           "nodes": round(statistics.median(r["nodes"] for r in runs)),
                           "time_ms": round(statistics.median(r["time_ms"] for r in runs), 2),
                           "forced_result": any(r["decided"] for r in runs)}
                    rows.append(row)
                    if verbose:
                        print(f"{state_name:22s} {row['budget_ms']:>4d} ms {config:22s} depth={row['depth']:<4} "
                              f"nodes={row['nodes']:>9,} time={row['time_ms']:>8.1f} ms"
                              f"{'  (forced win/loss found)' if row['forced_result'] else ''}", flush=True)
        return rows

    @staticmethod
    def summary(rows: List[Dict]) -> List[Dict]:
        """Average completed depth and nodes per (configuration, budget) over all states."""
        result = []
        for config in dict.fromkeys(r["config"] for r in rows):
            for budget in sorted({r["budget_ms"] for r in rows}):
                group = [r for r in rows if r["config"] == config and r["budget_ms"] == budget]
                result.append({"config": config, "budget_ms": budget,
                               "avg_depth": round(statistics.mean(r["depth"] for r in group), 2),
                               "min_depth": min(r["depth"] for r in group),
                               "max_depth": max(r["depth"] for r in group),
                               "avg_nodes": round(statistics.mean(r["nodes"] for r in group)),
                               "avg_time_ms": round(statistics.mean(r["time_ms"] for r in group), 1)})
        return result

    @staticmethod
    def save(rows: List[Dict], path: Optional[Path] = None) -> Path:
        path = path or RESULTS_DIR / "depth_budget.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        for target, data in ((path, rows),
                             (path.with_name(path.stem + "_summary.csv"), DepthBudgetExperiment.summary(rows))):
            with open(target, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(data[0].keys()))
                writer.writeheader()
                writer.writerows(data)
        return path

    @staticmethod
    def plot(rows: List[Dict], path: Optional[Path] = None) -> Optional[Path]:
        """Grouped bars: average completed depth per time budget, one bar per configuration (labelled)."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return None
        path = path or RESULTS_DIR / "depth_budget.png"
        summary = DepthBudgetExperiment.summary(rows)
        configs = list(dict.fromkeys(r["config"] for r in summary))
        budgets = sorted({r["budget_ms"] for r in summary})
        value = {(r["config"], r["budget_ms"]): r["avg_depth"] for r in summary}

        fig, ax = plt.subplots(figsize=(9, 4.4), facecolor=SURFACE)
        group_width = 0.8
        bar_width = group_width / len(configs)
        for index, config in enumerate(configs):
            xs = [b + (index - (len(configs) - 1) / 2) * bar_width for b in range(len(budgets))]
            heights = [value[(config, budget)] for budget in budgets]
            bars = ax.bar(xs, heights, width=bar_width * 0.88, color=color_of(config, index),
                          edgecolor=SURFACE, linewidth=1, label=config, zorder=3)
            for bar, height in zip(bars, heights):
                ax.text(bar.get_x() + bar.get_width() / 2, height + 0.08, f"{height:.1f}",
                        ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xticks(range(len(budgets)))
        style_axes(ax)
        ax.set_xticklabels([f"{b} ms per move" for b in budgets], color=INK)
        ax.set_ylabel("Completed search depth (cycles, avg)", color=MUTED)
        ax.set_title("Depth reached by iterative deepening within the time budget", color=INK, loc="left")
        ax.legend(frameon=False, fontsize=8, ncol=len(configs), loc="upper left", bbox_to_anchor=(0, -0.1))
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=SURFACE)
        plt.close(fig)
        return path


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Search depth reached within a time budget per move")
    parser.add_argument("--budgets", type=float, nargs="+", default=list(DEFAULT_BUDGETS),
                        help="time budgets in seconds")
    parser.add_argument("--configs", nargs="+", default=None)
    parser.add_argument("--max-depth", type=int, default=12, help="iterative deepening stops at this depth")
    parser.add_argument("--repeats", type=int, default=3, help="decisions per case; the median is reported")
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--output", default=None, help="CSV path (summary CSV and plot are saved next to it)")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args(argv)

    experiment = DepthBudgetExperiment(args.budgets, args.configs, args.max_depth, args.repeats, args.seed)
    rows = experiment.run()
    path = experiment.save(rows, Path(args.output) if args.output else None)
    print(f"\n{'Configuration':22s}{'Budget':>8s}{'Avg depth':>11s}{'Min':>5s}{'Max':>5s}{'Avg nodes':>11s}")
    for r in experiment.summary(rows):
        print(f"{r['config']:22s}{r['budget_ms']:>6d}ms{r['avg_depth']:>11.2f}{r['min_depth']:>5}{r['max_depth']:>5}"
              f"{r['avg_nodes']:>11,}")
    print("CSV :", path)
    if not args.no_plot:
        print("Plot:", experiment.plot(rows, path.with_suffix(".png")))


if __name__ == "__main__":
    main()
