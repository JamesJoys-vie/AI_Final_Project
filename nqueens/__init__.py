"""N-Queens: SAT (Glucose3) and Min-Conflicts solvers."""
from .board import Board
from .cnf_encoder import AttackConstraintDiscoverer, CNFFormula, NQueensCNFEncoder, VariableMapper
from .min_conflicts import (ConflictState, MaxConflictSelector, MinConflictsResult, MinConflictsSolver,
                            RandomConflictedSelector, VariableSelector)

try:  # PySAT is optional for the Min-Conflicts part
    from .sat_solver import GlucoseQueenSolver, SATResult
except ImportError:  # pragma: no cover
    pass
