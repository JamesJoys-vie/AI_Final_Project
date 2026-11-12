"""Immutable game entities (NamedTuple) and the HP table from the project description."""
from __future__ import annotations

from typing import NamedTuple, Tuple

from task2_tank_battle.core.actions import Direction

TANK_MAX_HP = 6
BASE_MAX_HP = 9
WALL_MAX_HP = 3
DAMAGE_PER_HIT = 1
BULLET_SPEED = 3


class Tank(NamedTuple):
    """Immutable tank. Use _replace(...) to build the next version instead of mutating."""

    player: int
    x: int
    y: int
    facing: Direction
    hp: int = TANK_MAX_HP

    @property
    def position(self) -> Tuple[int, int]:
        return self.x, self.y

    @property
    def alive(self) -> bool:
        return self.hp > 0


class Base(NamedTuple):
    player: int
    x: int
    y: int
    hp: int = BASE_MAX_HP

    @property
    def position(self) -> Tuple[int, int]:
        return self.x, self.y

    @property
    def alive(self) -> bool:
        return self.hp > 0


class Bullet(NamedTuple):
    owner: int
    x: int
    y: int
    direction: Direction


class GameEvent(NamedTuple):
    """Something that happened during one cycle (used by the UI and the log only)."""

    kind: str
    x: int
    y: int
    owner: int
    detail: str = ""


class BulletTrail(NamedTuple):
    """Cells a bullet passed through during one cycle, for smooth animation."""

    owner: int
    cells: Tuple[Tuple[int, int], ...]
