"""
The game engine and the heuristic must behave exactly like the frozen pre-optimization version
(tests/reference_impl.py) on a large sample of reachable states and every joint action.
Run from the repository root:  python -m unittest discover -s task2_tank_battle/tests -t .
"""
from __future__ import annotations

import itertools
import unittest

from task2_tank_battle.ai.evaluators import HeuristicEvaluator, TerminalOnlyEvaluator
from task2_tank_battle.core.actions import ALL_ACTIONS
from task2_tank_battle.core.game_rules import TankBattleRules
from task2_tank_battle.core.game_state import GameState
from task2_tank_battle.tests.reference_impl import ReferenceHeuristicEvaluator, ReferenceRules
from task2_tank_battle.tests.state_samples import sample_states

JOINT_ACTIONS = list(itertools.product(ALL_ACTIONS, repeat=2))


def full_key(state: GameState) -> tuple:
    return (state.width, state.height, state.signature(), state.max_turns, state.events, state.trails)


class EngineMatchesReferenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = sample_states(300)
        cls.rules = TankBattleRules()
        cls.reference = ReferenceRules()

    def test_sample_covers_interesting_states(self):
        self.assertTrue(any(s.bullets for s in self.states))
        self.assertTrue(any(len(s.bullets) == 2 for s in self.states))
        self.assertTrue(any(self.reference.is_terminal(s) for s in self.states))
        self.assertTrue(any(min(t.hp for t in s.tanks) < 3 for s in self.states))

    def test_step_matches_reference_for_every_joint_action(self):
        for index, state in enumerate(self.states):
            for actions in JOINT_ACTIONS:
                for record in (False, True):
                    expected = self.reference.step(state, actions, record)
                    actual = self.rules.step(state, actions, record)
                    if full_key(actual) != full_key(expected):
                        self.fail(f"state #{index}, actions {actions}, record={record}:\n"
                                  f"expected {full_key(expected)}\nactual   {full_key(actual)}")

    def test_actions_terminal_test_and_utility_match_reference(self):
        for index, state in enumerate(self.states):
            with self.subTest(state=index):
                self.assertEqual(self.rules.outcome(state), self.reference.outcome(state))
                self.assertEqual(self.rules.is_terminal(state), self.reference.is_terminal(state))
                self.assertEqual(self.rules.winner(state), self.reference.winner(state))
                for player in (0, 1):
                    self.assertEqual(self.rules.legal_actions(state, player),
                                     self.reference.legal_actions(state, player))
                    self.assertEqual(self.rules.utility(state, player), self.reference.utility(state, player))

    def test_apply_for_player_orders_the_joint_action(self):
        state = self.states[0]
        for own, other in JOINT_ACTIONS:
            self.assertEqual(self.rules.apply_for_player(state, 0, own, other).signature(),
                             self.reference.step(state, (own, other)).signature())
            self.assertEqual(self.rules.apply_for_player(state, 1, own, other).signature(),
                             self.reference.step(state, (other, own)).signature())


class EvaluatorMatchesReferenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = sample_states(300)
        cls.rules = TankBattleRules()
        cls.reference_rules = ReferenceRules()

    def test_heuristic_eval_matches_reference(self):
        """The root state prepares the distance fields; its children are evaluated with the same fields."""
        for index, root in enumerate(self.states):
            for player in (0, 1):
                evaluator = HeuristicEvaluator(self.rules)
                reference = ReferenceHeuristicEvaluator(self.reference_rules)
                evaluator.prepare(root, player)
                reference.prepare(root, player)
                for actions in JOINT_ACTIONS[::5] + [None]:
                    state = root if actions is None else self.reference_rules.step(root, actions)
                    expected = reference.evaluate(state, player)
                    actual = evaluator.evaluate(state, player)
                    self.assertAlmostEqual(actual, expected, places=9,
                                           msg=f"state #{index}, player {player}, actions {actions}")

    def test_heuristic_eval_is_zero_sum(self):
        evaluator = HeuristicEvaluator(self.rules)
        for state in self.states:
            evaluator.prepare(state, 0)
            self.assertAlmostEqual(evaluator.evaluate(state, 0), -evaluator.evaluate(state, 1), places=9)

    def test_terminal_only_eval(self):
        evaluator = TerminalOnlyEvaluator(self.rules)
        for state in self.states:
            for player in (0, 1):
                expected = self.reference_rules.utility(state, player) if self.reference_rules.is_terminal(state) else 0.0
                self.assertEqual(evaluator.evaluate(state, player), expected)


if __name__ == "__main__":
    unittest.main()
