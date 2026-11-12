"""
Tests for the game model: RESULT(s, a) (movement, bullets, collisions), ACTIONS(s), TERMINAL-TEST and UTILITY.
Run from the repository root:  python -m unittest discover -s task2_tank_battle/tests -t .
"""
from __future__ import annotations

import unittest
from typing import Iterable, Optional, Tuple

from task2_tank_battle.core.actions import ACTIONS_WITHOUT_FIRE, ALL_ACTIONS, MOVE_DIRECTIONS, Action, Direction
from task2_tank_battle.core.entities import BASE_MAX_HP, TANK_MAX_HP, WALL_MAX_HP, Bullet
from task2_tank_battle.core.game_rules import WIN_SCORE, Outcome, TankBattleRules
from task2_tank_battle.core.game_state import PLAYER_ONE, PLAYER_TWO, GameState
from task2_tank_battle.core.map_loader import MapFormatError, MapLoader, RandomMapGenerator

S, F = Action.STAY, Action.FIRE
UP, DOWN, LEFT, RIGHT = Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT
Cell = Tuple[int, int]


def make_state(walls: Iterable[Cell] = (), tank1: Cell = (4, 8), tank2: Cell = (8, 0),
               base1: Cell = (0, 8), base2: Cell = (0, 0), size: int = 9) -> GameState:
    """Open size x size map. Tank 1 faces UP, tank 2 faces DOWN (as on a loaded map)."""
    grid = [["."] * size for _ in range(size)]
    for x, y in walls:
        grid[y][x] = "#"
    for symbol, (x, y) in (("1", tank1), ("2", tank2), ("A", base1), ("B", base2)):
        grid[y][x] = symbol
    return MapLoader.parse("\n".join("".join(row) for row in grid))


def modified(state: GameState, tanks=None, bases=None, bullets=None, turn: Optional[int] = None) -> GameState:
    return GameState(state.width, state.height, state.walls,
                     tanks if tanks is not None else state.tanks,
                     bases if bases is not None else state.bases,
                     bullets if bullets is not None else state.bullets,
                     state.turn if turn is None else turn, state.max_turns)


def set_hp(state: GameState, tanks=(None, None), bases=(None, None)) -> GameState:
    new_tanks = tuple(t if hp is None else t._replace(hp=hp) for t, hp in zip(state.tanks, tanks))
    new_bases = tuple(b if hp is None else b._replace(hp=hp) for b, hp in zip(state.bases, bases))
    return modified(state, tanks=new_tanks, bases=new_bases)


class BulletTest(unittest.TestCase):
    def setUp(self):
        self.rules = TankBattleRules()

    def test_bullet_flies_three_cells_per_cycle_then_leaves_the_map(self):
        state = self.rules.step(make_state(), (F, S))
        self.assertEqual(state.bullets, (Bullet(PLAYER_ONE, 4, 5, Direction.UP),))
        state = self.rules.step(state, (S, S))
        self.assertEqual(state.bullets, (Bullet(PLAYER_ONE, 4, 2, Direction.UP),))
        state = self.rules.step(state, (S, S))
        self.assertEqual(state.bullets, ())

    def test_only_one_bullet_per_tank(self):
        state = self.rules.step(make_state(), (F, S))
        self.assertEqual(self.rules.legal_actions(state, PLAYER_ONE), ACTIONS_WITHOUT_FIRE)
        self.assertEqual(self.rules.legal_actions(state, PLAYER_TWO), ALL_ACTIONS)
        state = self.rules.step(state, (F, S))  # FIRE is ignored while the bullet flies
        self.assertEqual(len(state.bullets), 1)
        state = self.rules.step(state, (S, S))  # bullet leaves the map
        self.assertEqual(self.rules.legal_actions(state, PLAYER_ONE), ALL_ACTIONS)

    def test_rule_variant_without_bullet_limit(self):
        rules = TankBattleRules(one_bullet_per_tank=False)
        state = rules.step(make_state(), (F, S))
        self.assertEqual(rules.legal_actions(state, PLAYER_ONE), ALL_ACTIONS)
        self.assertEqual(len(rules.step(state, (F, S)).bullets), 2)

    def test_wall_stops_bullet_and_loses_one_hp_per_hit(self):
        start = make_state(walls=[(4, 6)])
        state = self.rules.step(start, (F, S))
        self.assertEqual(state.walls[(4, 6)], WALL_MAX_HP - 1)
        self.assertEqual(state.bullets, ())
        self.assertEqual(start.walls[(4, 6)], WALL_MAX_HP, "walls are copy-on-write")
        for _ in range(WALL_MAX_HP - 1):
            state = self.rules.step(state, (F, S))
        self.assertNotIn((4, 6), state.walls)
        state = self.rules.step(state, (F, S))  # the next shot flies through the gap
        self.assertEqual(state.bullets, (Bullet(PLAYER_ONE, 4, 5, Direction.UP),))

    def test_collision_is_checked_after_every_cell(self):
        # Wall 1 cell ahead and a tank 2 cells ahead: only the wall is hit.
        state = make_state(walls=[(4, 7)], tank2=(4, 6))
        state = self.rules.step(state, (F, S))
        self.assertEqual(state.walls[(4, 7)], WALL_MAX_HP - 1)
        self.assertEqual(state.tanks[PLAYER_TWO].hp, TANK_MAX_HP)

    def test_bullet_stops_at_first_entity(self):
        state = make_state(tank2=(4, 6), base2=(4, 5))
        state = self.rules.step(state, (F, S))
        self.assertEqual(state.tanks[PLAYER_TWO].hp, TANK_MAX_HP - 1)
        self.assertEqual(state.bases[PLAYER_TWO].hp, BASE_MAX_HP)
        self.assertEqual(state.bullets, ())

    def test_bullet_hits_base(self):
        state = self.rules.step(make_state(base2=(4, 5)), (F, S))
        self.assertEqual(state.bases[PLAYER_TWO].hp, BASE_MAX_HP - 1)

    def test_tanks_facing_each_other_hit_each_other(self):
        # Bullets pass through each other; both reach their target in the same cycle.
        state = self.rules.step(make_state(tank2=(4, 5)), (F, F))
        self.assertEqual([t.hp for t in state.tanks], [TANK_MAX_HP - 1] * 2)
        self.assertEqual(state.bullets, ())

    def test_tank_driving_into_a_bullet_is_hit(self):
        bullet = Bullet(PLAYER_TWO, 4, 7, Direction.LEFT)
        state = modified(make_state(), bullets=(bullet,))
        moved = self.rules.step(state, (UP, S))
        self.assertEqual(moved.tanks[PLAYER_ONE].hp, TANK_MAX_HP - 1)
        self.assertEqual(moved.bullets, ())
        stayed = self.rules.step(state, (S, S))
        self.assertEqual(stayed.tanks[PLAYER_ONE].hp, TANK_MAX_HP)
        self.assertEqual(stayed.bullets, (Bullet(PLAYER_TWO, 1, 7, Direction.LEFT),))

    def test_new_bullet_starts_after_the_tank_moved_and_turned(self):
        state = self.rules.step(make_state(), (RIGHT, S))
        state = self.rules.step(state, (F, S))
        self.assertEqual(state.bullets, (Bullet(PLAYER_ONE, 8, 8, Direction.RIGHT),))

    def test_events_and_trails_only_when_recording(self):
        start = make_state(walls=[(4, 6)])
        self.assertEqual(self.rules.step(start, (F, S)).events, ())
        state = self.rules.step(start, (F, S), record=True)
        self.assertEqual([e.kind for e in state.events], ["fire", "hit_wall"])
        self.assertEqual(state.trails[0].cells, ((4, 8), (4, 7), (4, 6)))


class MovementTest(unittest.TestCase):
    def setUp(self):
        self.rules = TankBattleRules()

    def test_move_to_free_cell(self):
        state = self.rules.step(make_state(), (LEFT, S))
        self.assertEqual(state.tanks[PLAYER_ONE].position, (3, 8))
        self.assertIs(state.tanks[PLAYER_ONE].facing, Direction.LEFT)
        self.assertEqual(state.turn, 1)

    def test_blocked_move_still_turns_the_tank(self):
        cases = {"wall": (make_state(walls=[(4, 7)]), UP),
                 "base": (make_state(base2=(4, 7)), UP),
                 "map edge": (make_state(), DOWN),
                 "other tank": (make_state(tank2=(4, 7)), UP)}
        for name, (state, action) in cases.items():
            with self.subTest(name):
                after = self.rules.step(state, (action, S))
                self.assertEqual(after.tanks[PLAYER_ONE].position, (4, 8))
                self.assertIs(after.tanks[PLAYER_ONE].facing, MOVE_DIRECTIONS[action])

    def test_both_tanks_into_same_cell_neither_moves(self):
        state = self.rules.step(make_state(tank1=(3, 4), tank2=(5, 4)), (RIGHT, LEFT))
        self.assertEqual([t.position for t in state.tanks], [(3, 4), (5, 4)])
        self.assertEqual([t.facing for t in state.tanks], [Direction.RIGHT, Direction.LEFT])

    def test_cannot_enter_cell_occupied_at_start_of_cycle(self):
        state = self.rules.step(make_state(tank2=(4, 7)), (UP, LEFT))
        self.assertEqual(state.tanks[PLAYER_ONE].position, (4, 8))
        self.assertEqual(state.tanks[PLAYER_TWO].position, (3, 7))

    def test_step_does_not_modify_the_input_state(self):
        state = modified(make_state(walls=[(4, 6)], tank2=(3, 7)),
                         bullets=(Bullet(PLAYER_TWO, 0, 3, Direction.RIGHT),))
        before = state.signature()
        for actions in ((F, F), (UP, RIGHT), (LEFT, DOWN)):
            self.rules.step(state, actions)
        self.assertEqual(state.signature(), before)


class TerminalAndUtilityTest(unittest.TestCase):
    def setUp(self):
        self.rules = TankBattleRules()

    def test_destroying_the_enemy_base_wins(self):
        state = set_hp(make_state(base2=(4, 5)), bases=(None, 1))
        self.assertEqual(self.rules.outcome(state), Outcome.ONGOING)
        state = self.rules.step(state, (F, S))
        self.assertEqual(self.rules.outcome(state), Outcome.PLAYER_ONE_WINS)
        self.assertTrue(self.rules.is_terminal(state))
        self.assertEqual(self.rules.winner(state), PLAYER_ONE)
        self.assertEqual(self.rules.utility(state, PLAYER_ONE), WIN_SCORE - 1)
        self.assertEqual(self.rules.utility(state, PLAYER_TWO), -(WIN_SCORE - 1))

    def test_destroying_the_enemy_tank_wins(self):
        state = set_hp(make_state(tank2=(4, 6)), tanks=(1, None))
        state = self.rules.step(state, (S, F))
        self.assertEqual(self.rules.winner(state), PLAYER_TWO)

    def test_both_destroyed_in_same_cycle_is_a_draw(self):
        state = set_hp(make_state(tank2=(4, 5)), tanks=(1, 1))
        state = self.rules.step(state, (F, F))
        self.assertEqual(self.rules.outcome(state), Outcome.DRAW)
        self.assertIsNone(self.rules.winner(state))
        self.assertEqual(self.rules.utility(state, PLAYER_ONE), 0.0)

    def test_turn_limit_is_a_draw(self):
        state = make_state()
        self.assertEqual(self.rules.outcome(modified(state, turn=state.max_turns - 1)), Outcome.ONGOING)
        self.assertEqual(self.rules.outcome(modified(state, turn=state.max_turns)), Outcome.DRAW)

    def test_faster_win_scores_higher(self):
        state = set_hp(make_state(), bases=(None, 0))
        early, late = modified(state, turn=5), modified(state, turn=50)
        self.assertGreater(self.rules.utility(early, PLAYER_ONE), self.rules.utility(late, PLAYER_ONE))


class MapLoaderTest(unittest.TestCase):
    def test_every_bundled_map_loads(self):
        for name in MapLoader.available_maps():
            with self.subTest(name):
                state = MapLoader.load(name)
                for entity in state.tanks + state.bases:
                    self.assertNotIn(entity.position, state.walls)
                self.assertEqual(MapLoader.parse(MapLoader.to_text(state)).signature(), state.signature())

    def test_invalid_maps_are_rejected(self):
        for text in ("", "1.A\n2.", "1.A\n2.B\n..?", "1..A\n...."):
            with self.subTest(text=text), self.assertRaises(MapFormatError):
                MapLoader.parse(text)

    def test_random_map_is_point_symmetric_and_reproducible(self):
        generator = RandomMapGenerator(13, 13)
        state = generator.generate(seed=5)
        self.assertEqual(generator.generate(seed=5).signature(), state.signature())
        for (x, y) in state.walls:
            self.assertIn((12 - x, 12 - y), state.walls)
        p1, p2 = state.tanks
        self.assertEqual((p2.x, p2.y), (12 - p1.x, 12 - p1.y))


if __name__ == "__main__":
    unittest.main()
