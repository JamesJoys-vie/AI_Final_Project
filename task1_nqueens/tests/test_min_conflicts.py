"""
Tests for the incremental Min-Conflicts engine.
Run from the repository root:  python -m unittest discover -s task1_nqueens/tests -t .
"""
from __future__ import annotations

import random
import unittest
from collections import deque
from typing import List, Optional, Tuple

from task1_nqueens.core.board import is_valid_solution
from task1_nqueens.solvers.min_conflicts import ConflictBoard, MinConflictsSolver, greedy_columns, random_columns
from task1_nqueens.solvers.variable_selectors import MaxConflictTabuSelector, RandomConflictedSelector


# --------------------------------------------------------------------------- reference (pre-optimization)
def _ref_conflicts(columns: List[int], row: int, col: int) -> int:
    return sum(1 for r, c in enumerate(columns)
               if r != row and (c == col or abs(r - row) == abs(c - col)))


def reference_min_conflicts(n: int, seed: int, heuristic: bool,
                            max_steps_factor: int = 50) -> Tuple[List[int], int, bool]:
    """Straightforward O(N^2)-per-step copy of the original algorithm, consuming the RNG in the same order."""
    rng = random.Random(seed)
    columns = [rng.randrange(n) for _ in range(n)]
    tabu: deque = deque(maxlen=max(1, min(10, n // 10)))
    steps = 0
    for _ in range(max_steps_factor * n):
        conflicted = [(r, k) for r in range(n) if (k := _ref_conflicts(columns, r, columns[r])) > 0]
        if not conflicted:
            break
        if heuristic:
            candidates = [item for item in conflicted if item[0] not in tabu] or conflicted
            best = max(k for _, k in candidates)
            row = rng.choice([r for r, k in candidates if k == best])
        else:
            row = rng.choice(conflicted)[0]
        costs = [_ref_conflicts(columns, row, c) for c in range(n)]
        best = min(costs)
        columns[row] = rng.choice([c for c, cost in enumerate(costs) if cost == best])
        tabu.append(row)
        steps += 1
    solved = all(_ref_conflicts(columns, r, columns[r]) == 0 for r in range(n))
    return columns, steps, solved


def _fresh_state(columns: List[int]):
    board = ConflictBoard(columns)
    return (board.pairs, board.row_conflicts, board.conflicted,
            {k: set(v) for k, v in board.buckets.items()})


def _brute_pairs(columns: List[int]) -> int:
    n = len(columns)
    return sum(1 for a in range(n) for b in range(a + 1, n)
               if columns[a] == columns[b] or abs(a - b) == abs(columns[a] - columns[b]))


# --------------------------------------------------------------------------- tests
class ConflictBoardInvariantTest(unittest.TestCase):
    def assert_consistent(self, board: ConflictBoard) -> None:
        pairs, row_conflicts, conflicted, buckets = _fresh_state(board.columns)
        self.assertEqual(board.pairs, pairs)
        self.assertEqual(board.pairs, _brute_pairs(board.columns))
        self.assertEqual(board.row_conflicts, row_conflicts)
        self.assertEqual(board.conflicted, conflicted)
        self.assertEqual(board.buckets, buckets)
        for row in range(board.n):
            self.assertEqual(board.column_costs(row), [board.conflicts(row, c) for c in range(board.n)])

    def test_random_move_sequences(self) -> None:
        rng = random.Random(1234)
        for n in (1, 2, 4, 5, 8, 13, 30):
            board = ConflictBoard([rng.randrange(n) for _ in range(n)])
            self.assert_consistent(board)
            for _ in range(200):
                board.move(rng.randrange(n), rng.randrange(n))
                self.assert_consistent(board)


class EquivalenceWithReferenceTest(unittest.TestCase):
    """With the same seed, the optimized solver makes exactly the same repairs as the original algorithm."""

    def test_same_trajectory(self) -> None:
        for n in (4, 8, 16, 32, 50):
            for seed in range(15):
                for heuristic in (False, True):
                    ref_columns, ref_steps, ref_solved = reference_min_conflicts(n, seed, heuristic)
                    selector = MaxConflictTabuSelector() if heuristic else RandomConflictedSelector()
                    result = MinConflictsSolver(selector, seed=seed, max_restarts=0).solve(n)
                    with self.subTest(n=n, seed=seed, heuristic=heuristic):
                        self.assertEqual(result.columns, ref_columns)
                        self.assertEqual(result.steps, ref_steps)
                        self.assertEqual(result.solved, ref_solved)


class RestartTest(unittest.TestCase):
    def test_restarts_fix_small_board_failures(self) -> None:
        for selector_cls in (RandomConflictedSelector, MaxConflictTabuSelector):
            for seed in range(50):
                result = MinConflictsSolver(selector_cls(), seed=seed).solve(8)
                with self.subTest(selector=selector_cls.name, seed=seed):
                    self.assertTrue(result.solved)
                    self.assertTrue(is_valid_solution(result.columns))

    def test_unsolvable_board_stops(self) -> None:
        result = MinConflictsSolver(seed=0, max_steps_factor=5, max_restarts=2).solve(3)
        self.assertFalse(result.solved)
        self.assertEqual(result.restarts, 2)
        self.assertEqual(result.steps, 3 * 5 * 3)

    def test_large_board_solved(self) -> None:
        for selector_cls in (RandomConflictedSelector, MaxConflictTabuSelector):
            result = MinConflictsSolver(selector_cls(), seed=7).solve(500)
            self.assertTrue(result.solved)
            self.assertTrue(is_valid_solution(result.columns))


class GreedyInitTest(unittest.TestCase):
    def test_greedy_columns_is_permutation(self) -> None:
        rng = random.Random(42)
        for n in (1, 2, 3, 8, 50, 1000):
            columns = greedy_columns(n, rng)
            self.assertEqual(sorted(columns), list(range(n)))

    def test_greedy_starts_closer_than_random(self) -> None:
        n = 500
        greedy = [ConflictBoard(greedy_columns(n, random.Random(s))).pairs for s in range(10)]
        rand = [ConflictBoard(random_columns(n, random.Random(s))).pairs for s in range(10)]
        self.assertLess(max(greedy), min(rand))

    def test_same_start_board_for_both_strategies(self) -> None:
        a = MinConflictsSolver(RandomConflictedSelector(), seed=3, init="greedy")
        b = MinConflictsSolver(MaxConflictTabuSelector(), seed=3, init="greedy")
        next(a.iter_steps(200), None)
        next(b.iter_steps(200), None)
        self.assertEqual(a.initial_pairs, b.initial_pairs)

    def test_greedy_solves(self) -> None:
        for selector_cls in (RandomConflictedSelector, MaxConflictTabuSelector):
            for n in (4, 8, 16, 100, 2000):
                for seed in range(5):
                    result = MinConflictsSolver(selector_cls(), seed=seed, init="greedy").solve(n)
                    with self.subTest(selector=selector_cls.name, n=n, seed=seed):
                        self.assertTrue(result.solved)
                        self.assertTrue(is_valid_solution(result.columns))
                        self.assertIn("initial_pairs", result.extra)

    def test_unknown_init_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MinConflictsSolver(init="smart")


if __name__ == "__main__":
    unittest.main()
