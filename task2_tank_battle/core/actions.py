"""Directions and the 6 tank actions defined by the project description."""
from __future__ import annotations

from enum import Enum


class Direction(Enum):
    """Grid direction as (dx, dy); y grows downward like screen coordinates."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    def __init__(self, dx: int, dy: int):
        # Plain attributes instead of properties: read millions of times per search,
        # and Enum's `.value` descriptor costs a Python-level call on every access.
        self.dx = dx
        self.dy = dy

    # Members are singletons compared by identity, so identity hashing is equivalent to Enum's default
    # (which hashes the name in Python code). States containing directions are hashed as
    # transposition-table keys, so this matters.
    __hash__ = object.__hash__


class Action(Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    FIRE = "FIRE"
    STAY = "STAY"

    __hash__ = object.__hash__  # see Direction.__hash__


MOVE_DIRECTIONS = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
    Action.MOVE_RIGHT: Direction.RIGHT,
}

# `action.move_direction` (a Direction, or None for FIRE / STAY) is the attribute form of MOVE_DIRECTIONS.
# The rules use it in the search tree: Enum members hash in Python code, so dict lookups keyed by an
# Action are several times slower than reading an attribute.
for _action in Action:
    _action.move_direction = MOVE_DIRECTIONS.get(_action)
del _action

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
