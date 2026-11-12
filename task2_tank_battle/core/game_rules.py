"""Game rules = the formal game model: ACTIONS(s), RESULT(s, a), TERMINAL-TEST(s), UTILITY(s, p)."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from task2_tank_battle.core.actions import ACTIONS_WITHOUT_FIRE, ALL_ACTIONS, Action, Direction
from task2_tank_battle.core.entities import (BULLET_SPEED, DAMAGE_PER_HIT, Base, Bullet, BulletTrail,
                                             GameEvent, Tank)
from task2_tank_battle.core.game_state import PLAYER_ONE, PLAYER_TWO, GameState

WIN_SCORE = 10_000

# tuple.__new__(Tank, fields) builds a NamedTuple without the Python-level __new__ / _replace wrappers.
_new = tuple.__new__


class Outcome(Enum):
    ONGOING = "ongoing"
    PLAYER_ONE_WINS = "Player 1 wins"
    PLAYER_TWO_WINS = "Player 2 wins"
    DRAW = "Draw"


def _move_target(tank: Tank, direction: Direction, other: Tank, width: int, height: int,
                 walls: Dict[Tuple[int, int], int], base1: Base, base2: Base) -> Optional[Tuple[int, int]]:
    """Cell the tank moves into, or None if it is blocked (edge, wall, base, or the other tank's cell)."""
    nx, ny = tank.x + direction.dx, tank.y + direction.dy
    if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in walls:
        return None
    if (nx == base1.x and ny == base1.y) or (nx == base2.x and ny == base2.y) or (nx == other.x and ny == other.y):
        return None
    return nx, ny


def _hit_tank_or_base(tanks: List[Tank], bases: List[Base], x: int, y: int, owner: int,
                      events: Optional[List[GameEvent]]) -> bool:
    """Damage the live tank or base on (x, y), tanks first. Updates the lists in place."""
    for k in (0, 1):
        tank = tanks[k]
        if tank.hp > 0 and tank.x == x and tank.y == y:
            hp = tank.hp - DAMAGE_PER_HIT
            tanks[k] = _new(Tank, (tank.player, x, y, tank.facing, hp))
            if events is not None:
                kind = "destroy_tank" if hp <= 0 else "hit_tank"
                events.append(GameEvent(kind, x, y, owner, f"P{k + 1} tank HP {hp}"))
            return True
    for k in (0, 1):
        base = bases[k]
        if base.hp > 0 and base.x == x and base.y == y:
            hp = base.hp - DAMAGE_PER_HIT
            bases[k] = _new(Base, (base.player, x, y, hp))
            if events is not None:
                kind = "destroy_base" if hp <= 0 else "hit_base"
                events.append(GameEvent(kind, x, y, owner, f"P{k + 1} base HP {hp}"))
            return True
    return False


class TankBattleRules:
    """
    One game cycle = both players choose an action, then the state is updated in 3 phases:
    (1) tanks turn/move, (2) tanks fire, (3) bullets fly 3 cells with a collision check after EVERY cell.
    """

    def __init__(self, bullet_speed: int = BULLET_SPEED, one_bullet_per_tank: bool = True):
        self.bullet_speed = bullet_speed
        self.one_bullet_per_tank = one_bullet_per_tank

    # ------------------------------------------------------------------ ACTIONS(s)
    def legal_actions(self, state: GameState, player: int) -> Tuple[Action, ...]:
        """FIRE is removed while the tank's previous bullet is still flying (one bullet at a time)."""
        if self.one_bullet_per_tank and state.has_active_bullet(player):
            return ACTIONS_WITHOUT_FIRE
        return ALL_ACTIONS

    # ------------------------------------------------------------------ RESULT(s, a)
    def step(self, state: GameState, actions: Tuple[Action, Action], record: bool = False) -> GameState:
        """
        Transition function. `actions[p]` is the action of player p. `record=True` stores events for the UI.

        This is the innermost operation of the search (one call per generated node), so it is written for
        speed: local variables instead of attribute lookups, no closures, tuples built directly instead of
        NamedTuple._replace, and a shortcut when no bullet is in the air. tests/reference_impl.py keeps the
        straightforward version, and the tests check that both produce exactly the same states.
        """
        events: Optional[List[GameEvent]] = [] if record else None
        width, height, walls = state.width, state.height, state.walls
        tank1, tank2 = state.tanks
        base1, base2 = state.bases
        action1, action2 = actions

        # (1) Movement. A move action always turns the tank; it only moves if the target cell is free
        # (not the map edge, a wall, a base, or the other tank's cell). If both want the same cell, neither moves.
        dir1 = action1.move_direction if tank1.hp > 0 else None
        dir2 = action2.move_direction if tank2.hp > 0 else None
        if dir1 is not None or dir2 is not None:
            target1 = None if dir1 is None else _move_target(tank1, dir1, tank2, width, height, walls, base1, base2)
            target2 = None if dir2 is None else _move_target(tank2, dir2, tank1, width, height, walls, base1, base2)
            if target1 is not None and target1 == target2:
                target1 = target2 = None
            if dir1 is not None:
                x, y = target1 if target1 is not None else (tank1.x, tank1.y)
                tank1 = _new(Tank, (tank1.player, x, y, dir1, tank1.hp))
            if dir2 is not None:
                x, y = target2 if target2 is not None else (tank2.x, tank2.y)
                tank2 = _new(Tank, (tank2.player, x, y, dir2, tank2.hp))

        # (2) Firing. The new bullet starts on the tank's cell (after it moved / turned).
        old_bullets = state.bullets
        fire1 = action1 is Action.FIRE
        fire2 = action2 is Action.FIRE
        if (fire1 or fire2) and self.one_bullet_per_tank:
            for bullet in old_bullets:
                if bullet.owner == PLAYER_ONE:
                    fire1 = False
                elif bullet.owner == PLAYER_TWO:
                    fire2 = False
        fire1 = fire1 and tank1.hp > 0
        fire2 = fire2 and tank2.hp > 0

        if not old_bullets and not fire1 and not fire2:
            # Nothing in the air: walls, bases and HP cannot change during this cycle.
            return GameState(width, height, walls, (tank1, tank2), state.bases, (),
                             state.turn + 1, state.max_turns, tuple(events) if events is not None else (), ())

        bullets = list(old_bullets)
        if fire1:
            bullets.append(_new(Bullet, (PLAYER_ONE, tank1.x, tank1.y, tank1.facing)))
            if events is not None:
                events.append(GameEvent("fire", tank1.x, tank1.y, PLAYER_ONE))
        if fire2:
            bullets.append(_new(Bullet, (PLAYER_TWO, tank2.x, tank2.y, tank2.facing)))
            if events is not None:
                events.append(GameEvent("fire", tank2.x, tank2.y, PLAYER_TWO))

        # (3) Bullets.
        tanks = [tank1, tank2]
        bases = [base1, base2]
        walls, remaining, trails = self._advance_bullets(width, height, walls, tanks, bases, bullets,
                                                         len(old_bullets), events)
        return GameState(width, height, walls, (tanks[0], tanks[1]), (bases[0], bases[1]), remaining,
                         state.turn + 1, state.max_turns,
                         tuple(events) if events is not None else (), trails)

    def _advance_bullets(self, width: int, height: int, walls: Dict[Tuple[int, int], int], tanks: List[Tank],
                         bases: List[Base], bullets: List[Bullet], first_new_bullet: int,
                         events: Optional[List[GameEvent]]):
        """
        Move every bullet cell by cell (bullet_speed times). After each cell we check, in order:
        map edge -> wall -> tank -> base. A bullet stops right after a hit. `tanks` and `bases` are
        updated in place; `walls` is copied before its first change (copy-on-write).
        Returns (walls, remaining bullets, trails).
        """
        count = len(bullets)
        alive = [True] * count
        xs = [b.x for b in bullets]
        ys = [b.y for b in bullets]
        trails = [[(b.x, b.y)] for b in bullets] if events is not None else None
        walls_copied = False
        flying = count

        # Old bullets that a tank drove into this cycle hit that tank before flying on.
        for i in range(first_new_bullet):
            if _hit_tank_or_base(tanks, bases, xs[i], ys[i], bullets[i].owner, events):
                alive[i] = False
                flying -= 1

        for _ in range(self.bullet_speed):
            if not flying:
                break
            for i in range(count):
                if not alive[i]:
                    continue
                direction = bullets[i].direction
                nx = xs[i] + direction.dx
                ny = ys[i] + direction.dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    alive[i] = False
                    flying -= 1
                    continue
                xs[i] = nx
                ys[i] = ny
                if trails is not None:
                    trails[i].append((nx, ny))

                wall_hp = walls.get((nx, ny))
                if wall_hp is not None:
                    if not walls_copied:
                        walls = dict(walls)
                        walls_copied = True
                    if wall_hp - DAMAGE_PER_HIT <= 0:
                        del walls[(nx, ny)]
                        if events is not None:
                            events.append(GameEvent("destroy_wall", nx, ny, bullets[i].owner))
                    else:
                        walls[(nx, ny)] = wall_hp - DAMAGE_PER_HIT
                        if events is not None:
                            events.append(GameEvent("hit_wall", nx, ny, bullets[i].owner))
                    alive[i] = False
                    flying -= 1
                    continue

                # As in the project description, bullets only collide with walls, tanks and bases
                # (two bullets pass through each other).
                if _hit_tank_or_base(tanks, bases, nx, ny, bullets[i].owner, events):
                    alive[i] = False
                    flying -= 1

        remaining = tuple(_new(Bullet, (b.owner, xs[i], ys[i], b.direction))
                          for i, b in enumerate(bullets) if alive[i])
        trail_tuple = tuple(BulletTrail(bullets[i].owner, tuple(trails[i])) for i in range(count)) \
            if trails is not None else ()
        return walls, remaining, trail_tuple

    # ------------------------------------------------------------------ TERMINAL-TEST(s)
    def outcome(self, state: GameState) -> Outcome:
        """A player is "alive" while BOTH its tank and its base survive. Turn limit -> draw."""
        p1_alive = state.tanks[PLAYER_ONE].hp > 0 and state.bases[PLAYER_ONE].hp > 0
        p2_alive = state.tanks[PLAYER_TWO].hp > 0 and state.bases[PLAYER_TWO].hp > 0
        if p1_alive and p2_alive:
            return Outcome.DRAW if state.turn >= state.max_turns else Outcome.ONGOING
        if p1_alive:
            return Outcome.PLAYER_ONE_WINS
        if p2_alive:
            return Outcome.PLAYER_TWO_WINS
        return Outcome.DRAW

    def is_terminal(self, state: GameState) -> bool:
        """Same answer as outcome() is not ONGOING, without building an Outcome (called at every search node)."""
        tank1, tank2 = state.tanks
        base1, base2 = state.bases
        if tank1.hp > 0 and base1.hp > 0 and tank2.hp > 0 and base2.hp > 0:
            return state.turn >= state.max_turns
        return True

    def winner(self, state: GameState) -> Optional[int]:
        tank1, tank2 = state.tanks
        base1, base2 = state.bases
        p1_alive = tank1.hp > 0 and base1.hp > 0
        p2_alive = tank2.hp > 0 and base2.hp > 0
        if p1_alive == p2_alive:
            return None  # both alive (ongoing or turn-limit draw) or both destroyed (draw)
        return PLAYER_ONE if p1_alive else PLAYER_TWO

    # ------------------------------------------------------------------ UTILITY(s, p)
    def utility(self, state: GameState, player: int) -> float:
        """Zero-sum: utility(s, P1) = -utility(s, P2). Faster wins score slightly higher."""
        winner = self.winner(state)
        if winner is None:
            return 0.0
        score = WIN_SCORE - state.turn
        return float(score if winner == player else -score)

    def apply_for_player(self, state: GameState, player: int, own_action: Action,
                         opponent_action: Action) -> GameState:
        """Helper for search: build the joint action in player order then call step()."""
        if player == PLAYER_ONE:
            return self.step(state, (own_action, opponent_action))
        return self.step(state, (opponent_action, own_action))
