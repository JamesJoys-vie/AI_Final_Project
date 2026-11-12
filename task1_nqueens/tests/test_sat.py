"""
Tests for the CNF encodings and the Glucose3 solver.
Run from the repository root:  python -m unittest discover -s task1_nqueens/tests -t .
"""
from __future__ import annotations

import unittest

from task1_nqueens.core.board import is_valid_solution
from task1_nqueens.logic.cnf_encoder import NQueensCnfEncoder
from task1_nqueens.solvers.sat_solver import SatNQueensSolver

CONFIGS = [("pairwise", False), ("pairwise", True), ("seqcounter", False), ("seqcounter", True)]
SOLUTION_COUNTS = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}  # OEIS A000170


def count_solutions(n: int, amo: str, column_alo: bool) -> int:
    """Enumerate every model, blocking each one on the N^2 square variables only (auxiliaries are free)."""
    from pysat.solvers import Glucose3

    formula = NQueensCnfEncoder(n, amo, column_alo).encode()
    count = 0
    with Glucose3(bootstrap_with=formula.clauses) as solver:
        while solver.solve():
            model = solver.get_model()
            queens = [lit for lit in model if 0 < lit <= n * n]
            columns = [-1] * n
            for lit in queens:
                columns[(lit - 1) // n] = (lit - 1) % n
            assert is_valid_solution(columns), (n, amo, column_alo, columns)
            count += 1
            solver.add_clause([-lit for lit in queens])
    return count


class EncoderTest(unittest.TestCase):
    def test_clause_count_prediction(self) -> None:
        for n in range(1, 16):
            for amo, column_alo in CONFIGS:
                encoder = NQueensCnfEncoder(n, amo, column_alo)
                with self.subTest(n=n, amo=amo, column_alo=column_alo):
                    self.assertEqual(len(encoder.encode().clauses), encoder.clause_count())
            self.assertEqual(NQueensCnfEncoder(n).clause_count(), NQueensCnfEncoder.expected_clause_count(n))

    def test_seqcounter_is_smaller(self) -> None:
        for n in (16, 64):
            pairwise = NQueensCnfEncoder(n, "pairwise").encode()
            seq = NQueensCnfEncoder(n, "seqcounter").encode()
            self.assertLess(len(seq.clauses), len(pairwise.clauses))
            self.assertGreater(seq.variable_count, n * n)
            self.assertEqual(pairwise.variable_count, n * n)

    def test_clause_kinds_sum_to_total(self) -> None:
        for amo, column_alo in CONFIGS:
            formula = NQueensCnfEncoder(10, amo, column_alo).encode()
            self.assertEqual(sum(formula.clauses_by_kind.values()), len(formula.clauses))

    def test_unknown_encoding_rejected(self) -> None:
        with self.assertRaises(ValueError):
            NQueensCnfEncoder(8, "ladder")
        with self.assertRaises(ValueError):
            SatNQueensSolver("ladder")


class SolutionCountTest(unittest.TestCase):
    """Every encoding has exactly the known number of N-Queens solutions: no solution lost, none added."""

    def test_all_solutions(self) -> None:
        for n, expected in SOLUTION_COUNTS.items():
            for amo, column_alo in CONFIGS:
                with self.subTest(n=n, amo=amo, column_alo=column_alo):
                    self.assertEqual(count_solutions(n, amo, column_alo), expected)


class SolverTest(unittest.TestCase):
    def test_valid_solutions(self) -> None:
        for amo, column_alo in CONFIGS:
            solver = SatNQueensSolver(amo, column_alo)
            for n in (4, 8, 13, 20):
                result = solver.solve(n)
                with self.subTest(n=n, amo=amo, column_alo=column_alo):
                    self.assertTrue(result.solved)
                    self.assertTrue(is_valid_solution(result.columns))
                    self.assertAlmostEqual(result.elapsed,
                                           result.extra["load_time"] + result.extra["search_time"])

    def test_assumptions_are_kept(self) -> None:
        for amo, column_alo in CONFIGS:
            result = SatNQueensSolver(amo, column_alo).solve(10, [(0, 3), (5, 1)])  # not attacking each other
            with self.subTest(amo=amo, column_alo=column_alo):
                self.assertTrue(result.solved)
                self.assertEqual(result.columns[0], 3)
                self.assertEqual(result.columns[5], 1)

    def test_conflicting_assumptions_unsat(self) -> None:
        for amo, column_alo in CONFIGS:
            result = SatNQueensSolver(amo, column_alo).solve(8, [(0, 0), (1, 1)])  # same diagonal
            with self.subTest(amo=amo, column_alo=column_alo):
                self.assertFalse(result.solved)
                self.assertIsNone(result.columns)

    def test_unsat_board(self) -> None:
        for amo, column_alo in CONFIGS:
            self.assertFalse(SatNQueensSolver(amo, column_alo).solve(3).solved)


if __name__ == "__main__":
    unittest.main()
