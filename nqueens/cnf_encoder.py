"""Propositional-logic formulation of N-Queens and its conversion to CNF.

Propositional symbol:
    X(r, c) is TRUE  <=>  square (r, c) holds a queen.
DIMACS variable id:
    var(r, c) = r * N + c + 1     (1-based indexing, range [1, N^2])

Relevant Components (Requirement 1):
1. Propositional Symbols / Variables:
   N^2 boolean variables X(r, c) representing whether square (r, c) has a queen.
2. Semantics / Interpretation:
   Truth assignment tau: {X(r, c)} -> {True, False}.
3. Knowledge Base (KB) Constraints:
   (C1) Row Coverage (Row ALO):
        For each row r in 0..N-1: OR_{c=0..N-1} X(r, c)
   (C2) Non-attacking Constraint (AMO for row, column, diagonals):
        For any pair of attacking squares a and b:
        X(a) => NOT X(b)  ===  (NOT X(a) OR NOT X(b))  [CNF clause]
   (C3) Optional Column Coverage (Column ALO):
        For each column c in 0..N-1: OR_{r=0..N-1} X(r, c)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import comb
from typing import Dict, Iterator, List, Tuple

Cell = Tuple[int, int]
Clause = List[int]


class VariableMapper:
    """Bijective mapping between board cells (r, c) and DIMACS variable ids."""

    def __init__(self, n: int):
        if n < 1:
            raise ValueError("Board size N must be >= 1")
        self.n = n

    @property
    def num_vars(self) -> int:
        return self.n * self.n

    def var(self, r: int, c: int) -> int:
        """Map cell (r, c) to DIMACS variable id in [1, N^2]."""
        if not (0 <= r < self.n and 0 <= c < self.n):
            raise IndexError(f"Cell {(r, c)} out of bounds for N={self.n}")
        return r * self.n + c + 1

    def cell(self, var_id: int) -> Cell:
        """Map DIMACS variable id back to cell (r, c)."""
        if not (1 <= var_id <= self.num_vars):
            raise ValueError(f"Variable id {var_id} out of range [1, {self.num_vars}]")
        return divmod(var_id - 1, self.n)


class AttackConstraintDiscoverer:
    """Discovers every distinct pair of mutually attacking board squares.

    Algorithm:
      Iterate through every cell (r, c). From that cell, radiate in 4 strictly
      forward directions:
        - (0, 1)  : row (right)
        - (1, 0)  : column (down)
        - (1, 1)  : main diagonal (down-right)
        - (1, -1) : anti diagonal (down-left)
      Every square encountered in these directions is attacked by (r, c).
      Using forward-only vectors ensures each unordered pair {a, b} is
      visited exactly once, producing zero duplicate clauses in O(N^3) time.
    """

    DIRECTIONS: Dict[str, Tuple[int, int]] = {
        "row": (0, 1),
        "column": (1, 0),
        "diag_main": (1, 1),
        "diag_anti": (1, -1),
    }

    def __init__(self, n: int):
        self.n = n

    def discover(self) -> Iterator[Tuple[str, Cell, Cell]]:
        n = self.n
        for r in range(n):
            for c in range(n):
                for kind, (dr, dc) in self.DIRECTIONS.items():
                    rr, cc = r + dr, c + dc
                    while 0 <= rr < n and 0 <= cc < n:
                        yield kind, (r, c), (rr, cc)
                        rr, cc = rr + dr, cc + dc


@dataclass
class CNFFormula:
    n: int
    num_vars: int
    clauses: List[Clause] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def num_clauses(self) -> int:
        return len(self.clauses)


class NQueensCNFEncoder:
    """Encodes N-Queens problem into Conjunctive Normal Form (CNF).

    Procedure for converting constraints into CNF:
    1. At-Least-One (ALO) per row:
       OR_{c=0}^{N-1} X(r, c) is directly a disjunction of positive literals:
       (X(r, 0) v X(r, 1) v ... v X(r, N-1)) -> 1 clause per row.
    2. At-Most-One (AMO) for attacking pairs (a, b):
       X(a) => NOT X(b)
       Eliminate implication: NOT X(a) v NOT X(b)
       This is directly a 2-literal negative clause -> 1 clause per pair.
    3. Optional redundant Column ALO:
       OR_{r=0}^{N-1} X(r, c) -> 1 clause per column.
    """

    def __init__(self, n: int, add_column_alo: bool = False):
        if n < 1:
            raise ValueError("N must be >= 1")
        self.n = n
        self.add_column_alo = add_column_alo
        self.mapper = VariableMapper(n)
        self.discoverer = AttackConstraintDiscoverer(n)

    def encode(self) -> CNFFormula:
        n, v = self.n, self.mapper.var
        cnf = CNFFormula(n=n, num_vars=self.mapper.num_vars)
        stats = {
            "row_alo": 0,
            "col_alo": 0,
            "row_amo": 0,
            "column_amo": 0,
            "diag_main_amo": 0,
            "diag_anti_amo": 0,
        }

        # (C1) Row ALO: at least one queen per row
        for r in range(n):
            cnf.clauses.append([v(r, c) for c in range(n)])
            stats["row_alo"] += 1

        # Optional Column ALO: at least one queen per column
        if self.add_column_alo:
            for c in range(n):
                cnf.clauses.append([v(r, c) for r in range(n)])
                stats["col_alo"] += 1

        # (C2) Mutual exclusion (AMO) for all attacking pairs
        kind_map = {
            "row": "row_amo",
            "column": "column_amo",
            "diag_main": "diag_main_amo",
            "diag_anti": "diag_anti_amo",
        }
        for kind, (r1, c1), (r2, c2) in self.discoverer.discover():
            cnf.clauses.append([-v(r1, c1), -v(r2, c2)])
            stats[kind_map[kind]] += 1

        cnf.stats = stats
        return cnf

    def theoretical_clause_count(self) -> int:
        """Closed form for the exact clause count:
        - Row ALO: N
        - Row AMO: N * C(N, 2)
        - Col AMO: N * C(N, 2)
        - Diagonals AMO: 4 * C(N, 3) + 2 * C(N, 2)
        - Optional Col ALO: +N
        """
        n = self.n
        total = n + 2 * n * comb(n, 2) + 4 * comb(n, 3) + 2 * comb(n, 2)
        if self.add_column_alo:
            total += n
        return total