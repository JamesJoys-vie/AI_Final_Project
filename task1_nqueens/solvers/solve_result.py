"""Common result object returned by every N-Queens solver."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SolveResult:
    solver: str
    n: int
    solved: bool
    columns: Optional[List[int]] = None
    elapsed: float = 0.0
    steps: int = 0
    clauses: int = 0
    variables: int = 0
    extra: Dict[str, float] = field(default_factory=dict)
    restarts: int = 0

    def summary(self) -> str:
        status = "solved" if self.solved else "FAILED"
        parts = [f"{self.solver}: N={self.n} {status} in {self.elapsed * 1000:.2f} ms"]
        if self.clauses:
            parts.append(f"{self.clauses:,} clauses / {self.variables:,} vars")
        if self.steps:
            parts.append(f"{self.steps:,} steps")
        if self.restarts:
            parts.append(f"{self.restarts} restart(s)")
        return ", ".join(parts)
