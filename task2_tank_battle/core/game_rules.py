"""Game rules = the formal game model: ACTIONS(s), RESULT(s, a), TERMINAL-TEST(s), UTILITY(s, p)."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from task2_tank_battle.core.actions import ACTIONS_WITHOUT_FIRE, ALL_ACTIONS, MOVE_DIRECTIONS, Action
from task2_tank_battle.core.entities import (BULLET_SPEED, DAMAGE_PER_HIT, Base, Bullet, BulletTrail,
                                             GameEvent, Tank)
from task2_tank_battle.core.game_state import PLAYER_ONE, PLAYER_TWO, GameState

WIN_SCORE = 10_000


class Outcome(Enum):
    ONGOING = "ongoing"
    PLAYER_ONE_WINS = "Player 1 wins"
    PLAYER_TWO_WINS = "Player 2 wins"
    DRAW = "Draw"


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
        """Transition function. `actions[p]` is the action of player p. `record=True` stores events for the UI."""
        events: Optional[List[GameEvent]] = [] if record else None
        tanks = self._move_tanks(state, actions)
        bullets = list(state.bullets)
        first_new_bullet = len(bullets)
        for player in (PLAYER_ONE, PLAYER_TWO):
            tank = tanks[player]
            can_fire = not (self.one_bullet_per_tank and state.has_active_bullet(player))
            if actions[player] is Action.FIRE and tank.hp > 0 and can_fire:
                bullets.append(Bullet(player, tank.x, tank.y, tank.facing))
                if events is not None:
                    events.append(GameEvent("fire", tank.x, tank.y, player))

        walls, tanks, bases, bullets, trails = self._advance_bullets(
            state, tanks, list(state.bases), bullets, first_new_bullet, events)

        return GameState(state.width, state.height, walls, tuple(tanks), tuple(bases), tuple(bullets),
                         state.turn + 1, state.max_turns,
                         tuple(events) if events is not None else (), tuple(trails))

    def _move_tanks(self, state: GameState, actions: Tuple[Action, Action]) -> List[Tank]:
        """
        A move action always turns the tank; it only moves if the target cell is free.
        If both tanks want the same cell, neither moves.
        """
        tanks = list(state.tanks)
        targets: List[Optional[Tuple[int, int]]] = [None, None]
        for player in (PLAYER_ONE, PLAYER_TWO):
            tank = tanks[player]
            direction = MOVE_DIRECTIONS.get(actions[player])
            if direction is None or tank.hp <= 0:
                continue
            tanks[player] = tank._replace(facing=direction)
            nx, ny = tank.x + direction.dx, tank.y + direction.dy
            other = state.tanks[1 - player]
            if state.is_blocked_for_tank(nx, ny) or (other.x == nx and other.y == ny):
                continue
            targets[player] = (nx, ny)

        if targets[0] is not None and targets[0] == targets[1]:
            targets = [None, None]
        for player in (PLAYER_ONE, PLAYER_TWO):
            if targets[player] is not None:
                tanks[player] = tanks[player]._replace(x=targets[player][0], y=targets[player][1])
        return tanks

    def _advance_bullets(self, state: GameState, tanks: List[Tank], bases: List[Base],
                         bullets: List[Bullet], first_new_bullet: int,
                         events: Optional[List[GameEvent]]):
        """
        Move every bullet cell by cell (bullet_speed times). After each cell we check, in order:
        map edge -> wall -> tank -> base. A bullet stops right after a hit.
        """
        walls = state.walls
        walls_copied = False
        alive = [True] * len(bullets)
        positions = [(b.x, b.y) for b in bullets]
        trails = [[(b.x, b.y)] for b in bullets] if events is not None else None

        def hit_tank_or_base(index: int, x: int, y: int) -> bool:
            owner = bullets[index].owner
            for k, tank in enumerate(tanks):
                if tank.hp > 0 and tank.x == x and tank.y == y:
                    tanks[k] = tank._replace(hp=tank.hp - DAMAGE_PER_HIT)
                    if events is not None:
                        kind = "destroy_tank" if tanks[k].hp <= 0 else "hit_tank"
                        events.append(GameEvent(kind, x, y, owner, f"P{k + 1} tank HP {tanks[k].hp}"))
                    return True
            for k, base in enumerate(bases):
                if base.hp > 0 and base.x == x and base.y == y:
                    bases[k] = base._replace(hp=base.hp - DAMAGE_PER_HIT)
                    if events is not None:
                        kind = "destroy_base" if bases[k].hp <= 0 else "hit_base"
                        events.append(GameEvent(kind, x, y, owner, f"P{k + 1} base HP {bases[k].hp}"))
                    return True
            return False

        # Old bullets that a tank drove into this cycle hit that tank before flying on.
        for i in range(first_new_bullet):
            if hit_tank_or_base(i, positions[i][0], positions[i][1]):
                alive[i] = False

        for _ in range(self.bullet_speed):
            for i, bullet in enumerate(bullets):
                if not alive[i]:
                    continue
                nx = positions[i][0] + bullet.direction.dx
                ny = positions[i][1] + bullet.direction.dy
                if not (0 <= nx < state.width and 0 <= ny < state.height):
                    alive[i] = False
                    continue
                positions[i] = (nx, ny)
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
                            events.append(GameEvent("destroy_wall", nx, ny, bullet.owner))
                    else:
                        walls[(nx, ny)] = wall_hp - DAMAGE_PER_HIT
                        if events is not None:
                            events.append(GameEvent("hit_wall", nx, ny, bullet.owner))
                    alive[i] = False
                    continue

                # As in the project description, bullets only collide with walls, tanks and bases
                # (two bullets pass through each other).
                if hit_tank_or_base(i, nx, ny):
                    alive[i] = False

        remaining = [bullets[i]._replace(x=positions[i][0], y=positions[i][1])
                     for i in range(len(bullets)) if alive[i]]
        trail_list = [BulletTrail(bullets[i].owner, tuple(trails[i])) for i in range(len(bullets))] \
            if trails is not None else []
        return walls, tanks, bases, remaining, trail_list

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
        return self.outcome(state) is not Outcome.ONGOING

    def winner(self, state: GameState) -> Optional[int]:
        result = self.outcome(state)
        if result is Outcome.PLAYER_ONE_WINS:
            return PLAYER_ONE
        if result is Outcome.PLAYER_TWO_WINS:
            return PLAYER_TWO
        return None

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
