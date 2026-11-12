"""GameState = one node of the game tree (a snapshot of the whole battlefield)."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from task2_tank_battle.core.entities import Base, Bullet, BulletTrail, GameEvent, Tank

PLAYER_ONE = 0
PLAYER_TWO = 1
PLAYER_NAMES = ("Player 1", "Player 2")


def opponent_of(player: int) -> int:
    return 1 - player


class GameState:
    """
    Treated as immutable: the rules always return a NEW state, so search can share old ones safely.
    `walls` is shared between states and only copied when a wall is damaged (copy-on-write).
    """

    __slots__ = ("width", "height", "walls", "tanks", "bases", "bullets", "turn", "max_turns", "events", "trails")

    def __init__(self, width: int, height: int, walls: Dict[Tuple[int, int], int],
                 tanks: Tuple[Tank, Tank], bases: Tuple[Base, Base], bullets: Tuple[Bullet, ...] = (),
                 turn: int = 0, max_turns: int = 200,
                 events: Tuple[GameEvent, ...] = (), trails: Tuple[BulletTrail, ...] = ()):
        self.width = width
        self.height = height
        self.walls = walls
        self.tanks = tanks
        self.bases = bases
        self.bullets = bullets
        self.turn = turn
        self.max_turns = max_turns
        self.events = events
        self.trails = trails

    def tank(self, player: int) -> Tank:
        return self.tanks[player]

    def base(self, player: int) -> Base:
        return self.bases[player]

    def is_inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def base_at(self, x: int, y: int) -> Optional[Base]:
        first, second = self.bases
        if first.x == x and first.y == y:
            return first
        if second.x == x and second.y == y:
            return second
        return None

    def is_blocked_for_tank(self, x: int, y: int) -> bool:
        """Tanks cannot enter walls, bases or cells outside the map."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True
        if (x, y) in self.walls:
            return True
        return self.base_at(x, y) is not None

    def has_active_bullet(self, player: int) -> bool:
        for bullet in self.bullets:
            if bullet.owner == player:
                return True
        return False

    def signature(self) -> tuple:
        """Hashable key of the state (used by tests and to compare scenarios)."""
        return (self.tanks, self.bases, self.bullets, tuple(sorted(self.walls.items())), self.turn)
