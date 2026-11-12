"""Non-search controllers: a random baseline and the keyboard-driven human player."""
from __future__ import annotations

import random
import threading
from typing import Optional

from task2_tank_battle.agents.base_agent import BaseAgent
from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.game_state import GameState


class RandomAgent(BaseAgent):
    name = "Random"

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
        self.seed = seed
        self.rng = random.Random(seed)

    def reset(self, player: int) -> None:
        super().reset(player)
        self.rng = random.Random(self.seed)

    def choose_action(self, state: GameState, player: int) -> Action:
        return self.rng.choice(list(Action))


class HumanAgent(BaseAgent):
    """The UI writes the key the player pressed with submit(); the game loop reads it with choose_action()."""

    name = "Human"
    is_human = True

    def __init__(self):
        super().__init__()
        self._pending: Optional[Action] = None
        self._lock = threading.Lock()

    def submit(self, action: Action) -> None:
        with self._lock:
            self._pending = action

    @property
    def has_action(self) -> bool:
        return self._pending is not None

    def choose_action(self, state: GameState, player: int) -> Action:
        with self._lock:
            action = self._pending or Action.STAY
            self._pending = None
        return action
