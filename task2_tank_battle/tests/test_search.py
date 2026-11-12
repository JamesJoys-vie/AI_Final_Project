"""
Tests for the adversarial search: Alpha-Beta must back up exactly the Minimax value, the agents must find
forced wins and avoid forced losses, and iterative deepening must respect its time budget.
Run from the repository root:  python -m unittest discover -s task2_tank_battle/tests -t .
"""
from __future__ import annotations

import random
import time
import unittest

from task2_tank_battle.agents.search_agent import (ABLATION_CONFIGS, DEEPENING, SEARCH_CONFIGS, TABLE,
                                                   create_search_agent)
from task2_tank_battle.ai.evaluators import HeuristicEvaluator, TerminalOnlyEvaluator
from task2_tank_battle.ai.search import EXACT, AlphaBetaSearch, MinimaxSearch
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

    def _compare(self, evaluator_cls, depth: int, states, **options) -> None:
        rng = random.Random(depth)
        for index, state in enumerate(states):
            player = rng.randrange(2)
            actions = list(self.rules.legal_actions(state, player))
            rng.shuffle(actions)
            minimax = MinimaxSearch(self.rules, evaluator_cls(self.rules))
            alphabeta = AlphaBetaSearch(self.rules, evaluator_cls(self.rules), **options)
            _, mm_value, mm_stats = minimax.search(state, player, depth, None, actions)
            ab_action, ab_value, ab_stats = alphabeta.search(state, player, depth, None, actions)
            with self.subTest(state=index, player=player, depth=depth, options=options):
                self.assertAlmostEqual(ab_value, mm_value, places=9)
                if not options.get("internal_deepening"):  # deepening also counts the shallower iterations
                    self.assertLessEqual(ab_stats.nodes_generated, mm_stats.nodes_generated)
                self.assertIn(ab_action, actions)

    def test_terminal_only_depth_1_and_2(self):
        for depth in (1, 2):
            self._compare(TerminalOnlyEvaluator, depth, self.states)

    def test_heuristic_depth_1_and_2(self):
        for depth in (1, 2):
            self._compare(HeuristicEvaluator, depth, self.states)

    def test_every_enhancement_depth_1_and_2(self):
        for _, evaluator_cls, options in ABLATION_CONFIGS.values():
            for depth in (1, 2):
                self._compare(evaluator_cls, depth, self.states, **options)

    def test_every_enhancement_depth_3(self):
        for _, evaluator_cls, options in ABLATION_CONFIGS.values():
            self._compare(evaluator_cls, 3, self.states[:4], **options)

    def test_enhancements_with_terminal_utility_only(self):
        """Many equal values (0) and immediate wins stress the table's bound flags."""
        self._compare(TerminalOnlyEvaluator, 2, self.states, **DEEPENING)

    def test_minimax_generates_the_full_tree(self):
        state = make_state()
        _, _, stats = MinimaxSearch(self.rules, TerminalOnlyEvaluator(self.rules)).search(state, PLAYER_ONE, 1)
        self.assertEqual(stats.nodes_generated, 6 * 6)
        self.assertEqual(stats.leaves_evaluated, 6 * 6)
        self.assertEqual(stats.prunings, 0)


class EnhancedAlphaBetaTest(unittest.TestCase):
    """Transposition table, killers and iterative deepening (Heuristic Alpha-Beta configuration)."""

    @classmethod
    def setUpClass(cls):
        cls.rules = TankBattleRules()
        cls.states = sample_states(12, seed=99, include_terminal=False)

    def test_tables_kept_between_depths_still_give_the_minimax_value(self):
        """Iterative deepening keeps the table and killers between depths of one decision."""
        for index, state in enumerate(self.states[:5]):
            search = AlphaBetaSearch(self.rules, HeuristicEvaluator(self.rules), **TABLE)
            best = None
            for depth in (1, 2, 3):
                best, value, _ = search.search(state, PLAYER_ONE, depth, first_action=best, keep_tables=depth > 1)
                _, expected, _ = MinimaxSearch(self.rules, HeuristicEvaluator(self.rules)).search(
                    state, PLAYER_ONE, depth)
                with self.subTest(state=index, depth=depth):
                    self.assertAlmostEqual(value, expected, places=9)

    def test_bound_entries_are_not_used_as_exact_values(self):
        """
        A search that fails low (or high) only stores an upper (lower) bound. Re-searching the same state with
        a full window must still return the exact value, not the bound.
        """
        inf = float("inf")
        bound_entries = 0
        for index, state in enumerate(self.states):
            search = AlphaBetaSearch(self.rules, HeuristicEvaluator(self.rules), **TABLE)
            search.search(state, PLAYER_ONE, 3)  # sets player, stats and the evaluator's distance fields
            search.reset_tables()
            exact = search._max_value(state, 3, -inf, inf, 0)
            for window in ((exact + 50, inf), (-inf, exact - 50)):  # fail low, fail high
                search.reset_tables()
                search._max_value(state, 3, window[0], window[1], 0)
                bound_entries += sum(entry[2] != EXACT for entry in search.table.values())
                with self.subTest(state=index, window=window):
                    self.assertAlmostEqual(search._max_value(state, 3, -inf, inf, 0), exact, places=9)
        self.assertGreater(bound_entries, 0, "the narrow windows must store bound entries")

    def test_first_action_is_searched_first_even_with_move_ordering(self):
        searched_first = []

        class Recording(AlphaBetaSearch):
            def _root_search(self, state, depth, actions):
                searched_first.append(actions[0])
                return super()._root_search(state, depth, actions)

        search = Recording(self.rules, HeuristicEvaluator(self.rules), **TABLE)
        for state in self.states:
            for action in self.rules.legal_actions(state, PLAYER_TWO):
                searched_first.clear()
                search.search(state, PLAYER_TWO, 1, first_action=action)
                self.assertEqual(searched_first, [action])

    def test_table_is_used_and_reset_between_decisions(self):
        search = AlphaBetaSearch(self.rules, HeuristicEvaluator(self.rules), **DEEPENING)
        state = self.states[0]
        _, value, stats = search.search(state, PLAYER_ONE, 3)
        first = (value, stats.nodes_generated, stats.table_hits)
        self.assertGreater(stats.table_hits, 0)
        _, value, stats = search.search(state, PLAYER_ONE, 3)
        self.assertEqual((value, stats.nodes_generated, stats.table_hits), first)

    def test_enhancements_reduce_the_search(self):
        nodes = {}
        for name in ("H-AB +ordering", "Heuristic Alpha-Beta"):
            total = 0
            for state in self.states:
                agent = create_search_agent(name, 3, seed=1)
                total += agent.search.search(state, PLAYER_ONE, 3)[2].nodes_generated
            nodes[name] = total
        self.assertLess(nodes["Heuristic Alpha-Beta"], nodes["H-AB +ordering"])


class DecisionTest(unittest.TestCase):
    """Every configuration must take a win in one and dodge a loss in one."""

    def test_takes_the_winning_shot(self):
        state = set_hp(make_state(base2=(4, 5)), bases=(None, 1))
        for config in list(SEARCH_CONFIGS) + list(ABLATION_CONFIGS):
            with self.subTest(config):
                agent = create_search_agent(config, max_depth=1, seed=1)
                action, value, _ = agent.search.search(state, PLAYER_ONE, 1)
                self.assertIs(action, Action.FIRE)
                self.assertEqual(value, WIN_SCORE - 1)

    def test_dodges_a_lethal_shot(self):
        # Tank 1 has 1 HP and tank 2 is two cells above it, facing down: only a side step survives.
        state = set_hp(make_state(tank2=(4, 6)), tanks=(1, None))
        for config in list(SEARCH_CONFIGS) + list(ABLATION_CONFIGS):
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
