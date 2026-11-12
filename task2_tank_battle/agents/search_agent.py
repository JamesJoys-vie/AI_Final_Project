"""
SearchAgent = search algorithm + evaluator + depth (+ optional time budget with iterative deepening).
The 4 configurations required by the project are created by create_search_agent().
"""
from __future__ import annotations

import random
import time
from typing import Optional

from task2_tank_battle.agents.base_agent import BaseAgent
from task2_tank_battle.ai.evaluators import HeuristicEvaluator, TerminalOnlyEvaluator
from task2_tank_battle.ai.search import AdversarialSearch, AlphaBetaSearch, MinimaxSearch, SearchTimeout
from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.game_rules import WIN_SCORE, TankBattleRules
from task2_tank_battle.core.game_state import GameState

# name -> (search class, evaluator class, move ordering)
SEARCH_CONFIGS = {
    "Minimax": (MinimaxSearch, TerminalOnlyEvaluator, False),
    "Alpha-Beta": (AlphaBetaSearch, TerminalOnlyEvaluator, False),
    "Heuristic Minimax": (MinimaxSearch, HeuristicEvaluator, False),
    "Heuristic Alpha-Beta": (AlphaBetaSearch, HeuristicEvaluator, True),
}


class SearchAgent(BaseAgent):
    """
    Root actions are shuffled with a seeded RNG, so equally good moves are picked fairly and
    every match plays differently, while results stay reproducible with the same seed.
    """

    def __init__(self, name: str, search: AdversarialSearch, max_depth: int = 2,
                 time_limit: Optional[float] = None, seed: Optional[int] = None):
        super().__init__(name)
        self.search = search
        self.max_depth = max(1, max_depth)
        self.time_limit = time_limit
        self.seed = seed
        self.rng = random.Random(seed)

    def reset(self, player: int) -> None:
        super().reset(player)
        self.rng = random.Random(self.seed)

    def choose_action(self, state: GameState, player: int) -> Action:
        actions = list(self.search.rules.legal_actions(state, player))
        self.rng.shuffle(actions)
        if self.time_limit is None:
            action, _, stats = self.search.search(state, player, self.max_depth, None, actions)
            self.last_stats = stats
            return action
        return self._iterative_deepening(state, player, actions)

    def _iterative_deepening(self, state: GameState, player: int, actions: list) -> Action:
        """
        Search depth 1, 2, 3... until the time budget ends; keep the last COMPLETED result.
        The previous best action is tried first in the next iteration (better pruning).
        """
        deadline = time.perf_counter() + self.time_limit
        best_action, best_stats = actions[0], None
        total_nodes = 0
        for depth in range(1, self.max_depth + 1):
            try:
                action, value, stats = self.search.search(state, player, depth, deadline, actions)
            except SearchTimeout:
                total_nodes += self.search.stats.nodes_generated
                break
            total_nodes += stats.nodes_generated
            best_action, best_stats = action, stats
            actions.remove(action)
            actions.insert(0, action)
            if abs(value) >= WIN_SCORE / 2:
                break
        if best_stats is not None:
            best_stats.nodes_generated = total_nodes
        self.last_stats = best_stats
        return best_action


def create_search_agent(config_name: str, max_depth: int = 2, time_limit: Optional[float] = None,
                        seed: Optional[int] = None, rules: Optional[TankBattleRules] = None) -> SearchAgent:
    search_cls, evaluator_cls, ordering = SEARCH_CONFIGS[config_name]
    rules = rules or TankBattleRules()
    search = search_cls(rules, evaluator_cls(rules), use_move_ordering=ordering)
    return SearchAgent(config_name, search, max_depth, time_limit, seed)
