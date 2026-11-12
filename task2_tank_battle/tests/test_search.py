"""
Tests for the adversarial search: Alpha-Beta must back up exactly the Minimax value, the agents must find
forced wins and avoid forced losses, and iterative deepening must respect its time budget.
Run from the repository root:  python -m unittest discover -s task2_tank_battle/tests -t .
"""
from __future__ import annotations

import random
import time
import unittest

from task2_tank_battle.agents.search_agent import SEARCH_CONFIGS, create_search_agent
from task2_tank_battle.ai.evaluators import HeuristicEvaluator, TerminalOnlyEvaluator
from task2_tank_battle.ai.search import AlphaBetaSearch, MinimaxSearch
from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.game_rules import WIN_SCORE, TankBattleRules
from task2_tank_battle.core.game_state import PLAYER_ONE, PLAYER_TWO
from task2_tank_battle.core.map_loader import build_initial_state
from task2_tank_battle.core.match_runner import MatchRunner
from task2_tank_battle.tests.state_samples import sample_states
from task2_tank_battle.tests.test_rules import make_state, set_hp


class AlphaBetaEqualsMinimaxTest(unittest.TestCase):
    """Pruning (and move ordering) may skip nodes but never change the backed-up root value."""

    @classmethod
    def setUpClass(cls):
        cls.rules = TankBattleRules()
        cls.states = sample_states(40, seed=777, include_terminal=False)

    def _compare(self, evaluator_cls, depth: int, states, ordering: bool) -> None:
        rng = random.Random(depth)
        for index, state in enumerate(states):
            player = rng.randrange(2)
            actions = list(self.rules.legal_actions(state, player))
            rng.shuffle(actions)
            minimax = MinimaxSearch(self.rules, evaluator_cls(self.rules))
            alphabeta = AlphaBetaSearch(self.rules, evaluator_cls(self.rules), use_move_ordering=ordering)
            _, mm_value, mm_stats = minimax.search(state, player, depth, None, actions)
            ab_action, ab_value, ab_stats = alphabeta.search(state, player, depth, None, actions)
            with self.subTest(state=index, player=player, depth=depth):
                self.assertAlmostEqual(ab_value, mm_value, places=9)
                self.assertLessEqual(ab_stats.nodes_generated, mm_stats.nodes_generated)
                self.assertIn(ab_action, actions)

    def test_terminal_only_depth_1_and_2(self):
        for depth in (1, 2):
            self._compare(TerminalOnlyEvaluator, depth, self.states, ordering=False)

    def test_heuristic_depth_1_and_2(self):
        for depth in (1, 2):
            self._compare(HeuristicEvaluator, depth, self.states, ordering=False)

    def test_heuristic_with_move_ordering_depth_1_and_2(self):
        for depth in (1, 2):
            self._compare(HeuristicEvaluator, depth, self.states, ordering=True)

    def test_heuristic_with_move_ordering_depth_3(self):
        self._compare(HeuristicEvaluator, 3, self.states[:3], ordering=True)

    def test_minimax_generates_the_full_tree(self):
        state = make_state()
        _, _, stats = MinimaxSearch(self.rules, TerminalOnlyEvaluator(self.rules)).search(state, PLAYER_ONE, 1)
        self.assertEqual(stats.nodes_generated, 6 * 6)
        self.assertEqual(stats.leaves_evaluated, 6 * 6)
        self.assertEqual(stats.prunings, 0)


class DecisionTest(unittest.TestCase):
    """Every configuration must take a win in one and dodge a loss in one."""

    def test_takes_the_winning_shot(self):
        state = set_hp(make_state(base2=(4, 5)), bases=(None, 1))
        for config in SEARCH_CONFIGS:
            with self.subTest(config):
                agent = create_search_agent(config, max_depth=1, seed=1)
                action, value, _ = agent.search.search(state, PLAYER_ONE, 1)
                self.assertIs(action, Action.FIRE)
                self.assertEqual(value, WIN_SCORE - 1)

    def test_dodges_a_lethal_shot(self):
        # Tank 1 has 1 HP and tank 2 is two cells above it, facing down: only a side step survives.
        state = set_hp(make_state(tank2=(4, 6)), tanks=(1, None))
        for config in SEARCH_CONFIGS:
            with self.subTest(config):
                agent = create_search_agent(config, max_depth=1, seed=1)
                action, value, _ = agent.search.search(state, PLAYER_ONE, 1)
                self.assertIn(action, (Action.MOVE_LEFT, Action.MOVE_RIGHT))
                self.assertGreater(value, -WIN_SCORE / 2)

    def test_player_two_takes_the_winning_shot(self):
        state = set_hp(make_state(tank2=(4, 2), base1=(4, 5)), bases=(1, None))
        agent = create_search_agent("Heuristic Alpha-Beta", max_depth=2, seed=1)
        action, value, _ = agent.search.search(state, PLAYER_TWO, 2)
        self.assertIs(action, Action.FIRE)
        self.assertGreater(value, WIN_SCORE / 2)


class AgentTest(unittest.TestCase):
    def test_iterative_deepening_respects_the_time_budget(self):
        state = build_initial_state("classic")
        for config in SEARCH_CONFIGS:
            with self.subTest(config):
                agent = create_search_agent(config, max_depth=8, time_limit=0.1, seed=3)
                start = time.perf_counter()
                action = agent.choose_action(state, PLAYER_ONE)
                elapsed = time.perf_counter() - start
                self.assertIn(action, agent.search.rules.legal_actions(state, PLAYER_ONE))
                self.assertLess(elapsed, 0.1 + 0.25)
                self.assertIsNotNone(agent.last_stats)
                self.assertGreaterEqual(agent.last_stats.depth, 1)

    def test_matches_are_reproducible_with_the_same_seeds(self):
        def play():
            state = build_initial_state("Random symmetric", seed=11, max_turns=30)
            agents = [create_search_agent("Heuristic Alpha-Beta", 2, None, seed=5),
                      create_search_agent("Heuristic Minimax", 1, None, seed=6)]
            return MatchRunner().play(state, agents).final_state.signature()

        self.assertEqual(play(), play())


if __name__ == "__main__":
    unittest.main()
