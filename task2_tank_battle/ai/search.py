"""
Adversarial search algorithms (Lecture 07): Minimax and Alpha-Beta pruning.
Whether they are "heuristic" depends only on the Evaluator plugged in at cut-off nodes.

Game tree model of one cycle: MAX picks its action, then MIN answers knowing it, then RESULT applies both.
So depth d (cycles) = 2d plies. Assuming MIN sees MAX's move is pessimistic, hence safe for MAX.
"""
from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Tuple

from task2_tank_battle.ai.evaluators import Evaluator
from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.game_rules import TankBattleRules
from task2_tank_battle.core.game_state import GameState


class SearchTimeout(Exception):
    """Raised when the time budget runs out (used by iterative deepening)."""


class SearchStats:
    """Metrics reported in the experiments and shown live in the GUI."""

    def __init__(self, algorithm: str = ""):
        self.algorithm = algorithm
        self.nodes_generated = 0
        self.leaves_evaluated = 0
        self.prunings = 0
        self.max_ply = 0
        self.depth = 0
        self.value = 0.0
        self.elapsed = 0.0
        self.timed_out = False

    def effective_branching_factor(self) -> float:
        """b* such that b*^plies = generated nodes (smaller means more pruning)."""
        plies = max(1, 2 * self.depth)
        return self.nodes_generated ** (1.0 / plies) if self.nodes_generated else 0.0

    def as_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "depth_cycles": self.depth,
            "depth_plies": 2 * self.depth,
            "nodes_generated": self.nodes_generated,
            "leaves_evaluated": self.leaves_evaluated,
            "prunings": self.prunings,
            "time_ms": round(self.elapsed * 1000, 3),
            "ebf": round(self.effective_branching_factor(), 3),
            "value": round(self.value, 2),
        }


class AdversarialSearch(ABC):
    """Common skeleton shared by Minimax and Alpha-Beta (node counting, time check, evaluation)."""

    name = "Adversarial search"
    TIME_CHECK_INTERVAL = 256

    def __init__(self, rules: TankBattleRules, evaluator: Evaluator, use_move_ordering: bool = False):
        self.rules = rules
        self.evaluator = evaluator
        self.use_move_ordering = use_move_ordering
        self.stats = SearchStats(self.name)
        self.player = 0
        self.opponent = 1
        self.deadline: Optional[float] = None

    def search(self, state: GameState, player: int, depth: int, deadline: Optional[float] = None,
               root_actions: Optional[Sequence[Action]] = None) -> Tuple[Action, float, SearchStats]:
        """Return (best action, its backed-up value, statistics) for `player` at `state`."""
        self.stats = SearchStats(self.name)
        self.stats.depth = depth
        self.player, self.opponent = player, 1 - player
        self.deadline = deadline
        self.evaluator.prepare(state, player)
        actions = list(root_actions) if root_actions else list(self.rules.legal_actions(state, player))
        if self.use_move_ordering:
            actions = self.evaluator.order_actions(state, player, actions)

        start = time.perf_counter()
        best_action, best_value = self._root(state, depth, actions)
        self.stats.elapsed = time.perf_counter() - start
        self.stats.value = best_value
        return best_action, best_value, self.stats

    @abstractmethod
    def _root(self, state: GameState, depth: int, actions: List[Action]) -> Tuple[Action, float]:
        pass

    def _actions(self, state: GameState, player: int) -> Sequence[Action]:
        actions = self.rules.legal_actions(state, player)
        if self.use_move_ordering:
            return self.evaluator.order_actions(state, player, actions)
        return actions

    def _result(self, state: GameState, my_action: Action, opponent_action: Action) -> GameState:
        """RESULT(s, a) + node counter + periodic deadline check."""
        stats = self.stats
        stats.nodes_generated += 1
        if self.deadline is not None and stats.nodes_generated % self.TIME_CHECK_INTERVAL == 0:
            if time.perf_counter() > self.deadline:
                stats.timed_out = True
                raise SearchTimeout()
        if self.player == 0:
            return self.rules.step(state, (my_action, opponent_action))
        return self.rules.step(state, (opponent_action, my_action))

    def _leaf_value(self, state: GameState, depth: int, ply: int) -> Optional[float]:
        """
        CUTOFF-TEST + EVAL in one call: the value of `state` if the search stops here, else None.
        Terminal states get the exact UTILITY; depth-limit states get the evaluator's estimate.
        The terminal test runs once per node (the evaluator does not repeat it).
        """
        if self.rules.is_terminal(state):
            value = self.rules.utility(state, self.player)
        elif depth == 0:
            value = self.evaluator.evaluate_nonterminal(state, self.player)
        else:
            return None
        stats = self.stats
        stats.leaves_evaluated += 1
        if ply > stats.max_ply:
            stats.max_ply = ply
        return value


class MinimaxSearch(AdversarialSearch):
    """MINIMAX-DECISION: explores every branch down to the depth limit, O(b^m) time."""

    name = "Minimax"

    def _root(self, state: GameState, depth: int, actions: List[Action]) -> Tuple[Action, float]:
        best_action, best_value = actions[0], -math.inf
        replies = self._actions(state, self.opponent)
        for action in actions:
            value = self._min_value(state, action, replies, depth, 1)
            if value > best_value:
                best_action, best_value = action, value
        return best_action, best_value

    def _max_value(self, state: GameState, depth: int, ply: int) -> float:
        leaf = self._leaf_value(state, depth, ply)
        if leaf is not None:
            return leaf
        value = -math.inf
        replies = self._actions(state, self.opponent)
        for action in self._actions(state, self.player):
            value = max(value, self._min_value(state, action, replies, depth, ply + 1))
        return value

    def _min_value(self, state: GameState, my_action: Action, replies: Sequence[Action], depth: int,
                   ply: int) -> float:
        """MIN's replies to `my_action` in `state`. `replies` is computed once per state by the caller."""
        value = math.inf
        for reply in replies:
            child = self._result(state, my_action, reply)
            value = min(value, self._max_value(child, depth - 1, ply + 1))
        return value


class AlphaBetaSearch(AdversarialSearch):
    """
    ALPHA-BETA-SEARCH: same decision as Minimax, but skips branches that cannot change it.
    alpha = best value MAX can guarantee so far, beta = best value MIN can guarantee so far.
    """

    name = "Alpha-Beta"

    def _root(self, state: GameState, depth: int, actions: List[Action]) -> Tuple[Action, float]:
        best_action, best_value = actions[0], -math.inf
        alpha, beta = -math.inf, math.inf
        replies = self._actions(state, self.opponent)
        for action in actions:
            value = self._min_value(state, action, replies, depth, alpha, beta, 1)
            if value > best_value:
                best_action, best_value = action, value
            alpha = max(alpha, best_value)
        return best_action, best_value

    def _max_value(self, state: GameState, depth: int, alpha: float, beta: float, ply: int) -> float:
        leaf = self._leaf_value(state, depth, ply)
        if leaf is not None:
            return leaf
        value = -math.inf
        replies = self._actions(state, self.opponent)
        for action in self._actions(state, self.player):
            value = max(value, self._min_value(state, action, replies, depth, alpha, beta, ply + 1))
            if value >= beta:
                # MIN already has a better option elsewhere -> prune remaining actions.
                self.stats.prunings += 1
                return value
            alpha = max(alpha, value)
        return value

    def _min_value(self, state: GameState, my_action: Action, replies: Sequence[Action], depth: int,
                   alpha: float, beta: float, ply: int) -> float:
        """MIN's replies to `my_action` in `state`. `replies` is computed once per state by the caller."""
        value = math.inf
        for reply in replies:
            child = self._result(state, my_action, reply)
            value = min(value, self._max_value(child, depth - 1, alpha, beta, ply + 1))
            if value <= alpha:
                # MAX already has a better option elsewhere -> prune remaining replies.
                self.stats.prunings += 1
                return value
            beta = min(beta, value)
        return value
