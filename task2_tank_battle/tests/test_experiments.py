"""
Smoke tests for the experiment scripts (fast settings; the real runs are in results/).
Run from the repository root:  python -m unittest discover -s task2_tank_battle/tests -t .
"""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from task2_tank_battle.experiments.depth_budget import DepthBudgetExperiment, experiment_states
from task2_tank_battle.experiments.search_benchmark import SearchBenchmark
from task2_tank_battle.experiments.tournament import combine_match_files


class DepthBudgetTest(unittest.TestCase):
    def test_every_configuration_completes_at_least_depth_one(self):
        states = experiment_states()
        self.assertGreaterEqual(len(states), 12)
        experiment = DepthBudgetExperiment(budgets=(0.03,), repeats=1, max_depth=6)
        rows = experiment.run(verbose=False, states={"duel": states["duel"]})
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertGreaterEqual(row["depth"], 1, row)
            self.assertLessEqual(row["depth"], 6)
        summary = experiment.summary(rows)
        self.assertEqual([r["config"] for r in summary], [r["config"] for r in rows])

    def test_save_writes_rows_and_summary(self):
        rows = [{"state": "s", "budget_ms": 50, "config": c, "depth": d, "nodes": 10, "time_ms": 50.0,
                 "forced_result": False} for c, d in (("A", 2), ("A", 4), ("B", 3))]
        with tempfile.TemporaryDirectory() as folder:
            path = DepthBudgetExperiment.save(rows, Path(folder) / "depth.csv")
            with open(Path(folder) / "depth_summary.csv", newline="") as file:
                summary = list(csv.DictReader(file))
            self.assertTrue(path.exists())
        self.assertEqual([(r["config"], float(r["avg_depth"])) for r in summary], [("A", 3.0), ("B", 3.0)])


class BenchmarkTest(unittest.TestCase):
    def test_ablation_rows_and_value_check(self):
        benchmark = SearchBenchmark(depths=(1, 2), repeats=1,
                                    configs=["Heuristic Minimax", "Heuristic Alpha-Beta", "H-AB +table"])
        rows = benchmark.run(verbose=False)
        self.assertEqual(len(rows), 4 * 2 * 3)  # scenarios x depths x configurations
        self.assertTrue(all(r["nodes_per_sec"] > 0 for r in rows))


class CombineStandingsTest(unittest.TestCase):
    def test_combine_counts_points_from_match_files(self):
        matches = [("A", "B", "Player 1 wins"), ("B", "A", "Draw"), ("B", "A", "Player 1 wins")]
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for index, (p1, p2, outcome) in enumerate(matches):
                path = Path(folder) / f"m{index}.csv"
                with open(path, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["match", "player_1", "player_2", "outcome", "p1_ms_per_move", "p2_ms_per_move"])
                    writer.writerow([index, p1, p2, outcome, 10, 20])
                paths.append(path)
            table = combine_match_files(paths)
        by_name = {s.name: s for s in table}
        self.assertEqual((by_name["A"].wins, by_name["A"].draws, by_name["A"].losses), (1, 1, 1))
        self.assertEqual(by_name["A"].points, 4)
        self.assertEqual(by_name["B"].points, 4)
        self.assertEqual(by_name["A"].think_ms, [10.0, 20.0, 20.0])


if __name__ == "__main__":
    unittest.main()
