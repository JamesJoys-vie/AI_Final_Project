"""Directions and the 6 tank actions defined by the project description."""
from __future__ import annotations

from enum import Enum


class Direction(Enum):
    """Grid direction as (dx, dy); y grows downward like screen coordinates."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]


class Action(Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    FIRE = "FIRE"
    STAY = "STAY"


# Lookup table instead of if/else chains: faster inside the search tree.
MOVE_DIRECTIONS = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
    Action.MOVE_RIGHT: Direction.RIGHT,
}

ALL_ACTIONS = (Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT, Action.FIRE, Action.STAY)
ACTIONS_WITHOUT_FIRE = tuple(a for a in ALL_ACTIONS if a is not Action.FIRE)


def parse_action(value) -> Action:
    """Accept an Action or its name ("FIRE", "move_up"); unknown values become STAY."""
    if isinstance(value, Action):
        return value
    try:
        return Action[str(value).strip().upper()]
    except KeyError:
        return Action.STAY
