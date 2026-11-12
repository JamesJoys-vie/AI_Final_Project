"""
Tests for QueenBoard and the solution checker, against brute-force definitions.
Run from the repository root:  python -m unittest discover -s task1_nqueens/tests -t .
"""
from __future__ import annotations

import random
import unittest
from itertools import combinations, permutations

from task1_nqueens.core.board import QueenBoard, attacks, is_valid_solution


def brute_pairs(queens):
    return [(a, b) for a, b in combinations(sorted(queens), 2) if attacks(a, b)]


def brute_attacked(n, queens):
    return {(r, c) for r in range(n) for c in range(n)
            if any(attacks((r, c), q) for q in queens if q != (r, c))}


def brute_valid(columns):
    n = len(columns)
    if any(c is None or not 0 <= c < n for c in columns):
        return False
    return not brute_pairs(set(enumerate(columns)))


class QueenBoardTest(unittest.TestCase):
    def assert_matches_brute_force(self, board: QueenBoard, queens: set) -> None:
        self.assertEqual(board.queens, queens)
        pairs = brute_pairs(queens)
        self.assertEqual(board.attacking_pairs(), pairs)
        self.assertEqual(board.attacking_pair_count(), len(pairs))
        self.assertEqual(board.attacked_cells(), brute_attacked(board.n, queens))
        self.assertEqual(board.is_solution(), len(queens) == board.n and not pairs)

    def test_random_toggles(self) -> None:
        rng = random.Random(7)
        for n in (1, 2, 4, 6, 9):
            board, queens = QueenBoard(n), set()
            self.assert_matches_brute_force(board, queens)
            for step in range(150):
                cell = (rng.randrange(n), rng.randrange(n))
                board.toggle(*cell)
                queens ^= {cell}
                self.assert_matches_brute_force(board, queens)
                if step == 100:
                    board.clear()
                    queens = set()

    def test_from_columns_and_as_columns(self) -> None:
        board = QueenBoard.from_columns([1, 3, 0, 2])
        self.assertTrue(board.is_solution())
        self.assertEqual(board.as_columns(), [1, 3, 0, 2])
        partial = QueenBoard.from_columns([1, -1, None, 2])
        self.assertEqual(partial.queens, {(0, 1), (3, 2)})
        self.assertFalse(partial.is_solution())

    def test_queens_cannot_be_mutated_from_outside(self) -> None:
        board = QueenBoard(4)
        board.toggle(0, 0)
        with self.assertRaises(AttributeError):
            board.queens.add((1, 1))

    def test_pairs_cache_invalidated(self) -> None:
        board = QueenBoard(5)
        board.toggle(0, 0)
        board.toggle(1, 1)
        self.assertEqual(len(board.attacking_pairs()), 1)
        board.toggle(1, 1)
        self.assertEqual(board.attacking_pairs(), [])


class CheckerTest(unittest.TestCase):
    def test_every_permutation_small_n(self) -> None:
        for n in range(1, 8):
            for columns in permutations(range(n)):
                self.assertEqual(is_valid_solution(columns), brute_valid(list(columns)), columns)

    def test_known_solution_counts(self) -> None:
        expected = {4: 2, 5: 10, 6: 4, 7: 40, 8: 92}
        for n, count in expected.items():
            self.assertEqual(sum(is_valid_solution(p) for p in permutations(range(n))), count)

    def test_invalid_inputs(self) -> None:
        self.assertFalse(is_valid_solution(None))
        self.assertFalse(is_valid_solution([1, 3, 0, None]))
        self.assertFalse(is_valid_solution([1, 3, 0, -1]))
        self.assertFalse(is_valid_solution([1, 3, 0, 4]))   # column outside the board
        self.assertFalse(is_valid_solution([0, 0, 0, 0]))
        self.assertTrue(is_valid_solution([0]))

    def test_large_board(self) -> None:
        from task1_nqueens.solvers.min_conflicts import MinConflictsSolver
        result = MinConflictsSolver(seed=1, init="greedy").solve(20000)
        self.assertTrue(is_valid_solution(result.columns))
        same_column = list(result.columns)
        same_column[1] = same_column[0]
        self.assertFalse(is_valid_solution(same_column))
        same_diagonal = list(result.columns)
        first = same_diagonal[0]
        same_diagonal[1] = first + 1 if first + 1 < len(same_diagonal) else first - 1  # rows 0 and 1 now attack
        self.assertFalse(is_valid_solution(same_diagonal))


if __name__ == "__main__":
    unittest.main()
