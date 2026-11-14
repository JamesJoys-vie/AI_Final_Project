import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nqueens import (Board, MaxConflictSelector, MinConflictsSolver, NQueensCNFEncoder,
                     RandomConflictedSelector)


@pytest.mark.parametrize("n", [1, 4, 5, 8, 13, 30])
def test_clause_count_matches_closed_form(n):
    enc = NQueensCNFEncoder(n)
    assert enc.encode().num_clauses == enc.theoretical_clause_count()


def test_clause_count_with_column_alo():
    enc = NQueensCNFEncoder(8, add_column_alo=True)
    assert enc.encode().num_clauses == 736 + 8
    assert enc.encode().num_clauses == enc.theoretical_clause_count()


def test_n8_has_736_clauses():
    assert NQueensCNFEncoder(8).encode().num_clauses == 736


def test_n1_has_1_clause():
    assert NQueensCNFEncoder(1).encode().num_clauses == 1


def test_no_duplicate_clauses():
    clauses = NQueensCNFEncoder(10).encode().clauses
    assert len({tuple(sorted(c)) for c in clauses}) == len(clauses)


def test_board_validation():
    assert Board.from_columns([1, 3, 0, 2]).is_valid_solution()
    assert not Board.from_columns([0, 1, 2, 3]).is_valid_solution()
    assert Board.from_columns([0]).is_valid_solution()  # N=1


@pytest.mark.parametrize("n", [1, 4, 5, 6, 7, 8, 10, 12])
def test_glucose_solves(n):
    pytest.importorskip("pysat")
    from nqueens.sat_solver import GlucoseQueenSolver
    res = GlucoseQueenSolver().solve(n)
    assert res.satisfiable and res.board.is_valid_solution()


@pytest.mark.parametrize("n", [2, 3])
def test_glucose_unsat_for_2_3(n):
    pytest.importorskip("pysat")
    from nqueens.sat_solver import GlucoseQueenSolver
    assert not GlucoseQueenSolver().solve(n).satisfiable


@pytest.mark.parametrize("selector", [RandomConflictedSelector(), MaxConflictSelector()])
@pytest.mark.parametrize("n", [4, 8, 10, 50, 200])
def test_min_conflicts_valid(selector, n):
    res = MinConflictsSolver(selector, max_steps=100_000).solve(n, seed=42)
    assert res.solved and res.board.is_valid_solution()