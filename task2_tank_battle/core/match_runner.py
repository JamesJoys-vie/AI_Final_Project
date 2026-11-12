"""Headless match between two agents (no window). Used by the tournament and by tests."""
from __future__ import annotations

import time
from typing import List, NamedTuple, Optional

from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.game_rules import Outcome, TankBattleRules
from task2_tank_battle.core.game_state import GameState


class MatchResult(NamedTuple):
    outcome: Outcome
    winner: Optional[int]
    turns: int
    think_time: List[float]
    moves: List[int]
    final_state: GameState

    def average_ms(self, player: int) -> float:
        return 1000 * self.think_time[player] / max(1, self.moves[player])


class MatchRunner:
    def __init__(self, rules: Optional[TankBattleRules] = None):
        self.rules = rules or TankBattleRules()

    def play(self, state: GameState, agents, on_turn=None) -> MatchResult:
        """Ask both agents for an action every cycle and apply them until a terminal state."""
        for player, agent in enumerate(agents):
            agent.reset(player)
        think_time, moves = [0.0, 0.0], [0, 0]
        while not self.rules.is_terminal(state):
            chosen: List[Action] = []
            for player, agent in enumerate(agents):
                start = time.perf_counter()
                chosen.append(agent.choose_action(state, player))
                think_time[player] += time.perf_counter() - start
                moves[player] += 1
            state = self.rules.step(state, (chosen[0], chosen[1]))
            if on_turn:
                on_turn(state)
        return MatchResult(self.rules.outcome(state), self.rules.winner(state), state.turn,
                           think_time, moves, state)
