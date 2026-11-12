"""The agent interface. Every controller (AI, human, other groups' plugins) implements choose_action()."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.game_state import GameState


class BaseAgent(ABC):
    """Subclass this in a plugin file to plug a new algorithm into the arena."""

    name = "Agent"
    is_human = False

    def __init__(self, name: Optional[str] = None):
        if name:
            self.name = name
        self.player = 0
        self.last_stats = None

    def reset(self, player: int) -> None:
        """Called once before a match starts."""
        self.player = player
        self.last_stats = None

    @abstractmethod
    def choose_action(self, state: GameState, player: int) -> Action:
        """Return one of the 6 actions for `player` in `state`. Must not modify `state`."""
