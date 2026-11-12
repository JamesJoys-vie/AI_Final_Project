"""
Frozen copy of the game rules and the heuristic EVAL(s) as they were BEFORE the optimization phases.

Later phases rewrite TankBattleRules / HeuristicEvaluator for speed; the tests compare them against this
straightforward version on many states, so any optimization must give exactly the same game.
Do not optimize or "fix" this file: it is the specification the fast code is checked against.
"""
from __future__ import annotations

import heapq
from typing import List, Optional, Tuple

from task2_tank_battle.core.actions import ACTIONS_WITHOUT_FIRE, ALL_ACTIONS, MOVE_DIRECTIONS, Action, Direction
from task2_tank_battle.core.entities import (BASE_MAX_HP, BULLET_SPEED, DAMAGE_PER_HIT, TANK_MAX_HP, Base, Bullet,
                                             BulletTrail, GameEvent, Tank)
from task2_tank_battle.core.game_rules import WIN_SCORE, Outcome
from task2_tank_battle.core.game_state import PLAYER_ONE, PLAYER_TWO, GameState

INF_DISTANCE = 10 ** 6


# --------------------------------------------------------------------------- state helpers (old GameState methods)
def _base_at(state: GameState, x: int, y: int) -> Optional[Base]:
    for base in state.bases:
        if base.x == x and base.y == y:
            return base
    return None


def _is_blocked_for_tank(state: GameState, x: int, y: int) -> bool:
    if not (0 <= x < state.width and 0 <= y < state.height):
        return True
    if (x, y) in state.walls:
        return True
    return _base_at(state, x, y) is not None


def _has_active_bullet(state: GameState, player: int) -> bool:
    for bullet in state.bullets:
        if bullet.owner == player:
            return True
    return False


# --------------------------------------------------------------------------- rules
class ReferenceRules:
    def __init__(self, bullet_speed: int = BULLET_SPEED, one_bullet_per_tank: bool = True):
        self.bullet_speed = bullet_speed
        self.one_bullet_per_tank = one_bullet_per_tank

    def legal_actions(self, state: GameState, player: int) -> Tuple[Action, ...]:
        if self.one_bullet_per_tank and _has_active_bullet(state, player):
            return ACTIONS_WITHOUT_FIRE
        return ALL_ACTIONS

    def step(self, state: GameState, actions: Tuple[Action, Action], record: bool = False) -> GameState:
        events: Optional[List[GameEvent]] = [] if record else None
        tanks = self._move_tanks(state, actions)
        bullets = list(state.bullets)
        first_new_bullet = len(bullets)
        for player in (PLAYER_ONE, PLAYER_TWO):
            tank = tanks[player]
            can_fire = not (self.one_bullet_per_tank and _has_active_bullet(state, player))
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
            if _is_blocked_for_tank(state, nx, ny) or (other.x == nx and other.y == ny):
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

                if hit_tank_or_base(i, nx, ny):
                    alive[i] = False

        remaining = [bullets[i]._replace(x=positions[i][0], y=positions[i][1])
                     for i in range(len(bullets)) if alive[i]]
        trail_list = [BulletTrail(bullets[i].owner, tuple(trails[i])) for i in range(len(bullets))] \
            if trails is not None else []
        return walls, tanks, bases, remaining, trail_list

    def outcome(self, state: GameState) -> Outcome:
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

    def utility(self, state: GameState, player: int) -> float:
        winner = self.winner(state)
        if winner is None:
            return 0.0
        score = WIN_SCORE - state.turn
        return float(score if winner == player else -score)


# --------------------------------------------------------------------------- heuristic EVAL(s)
class ReferenceDistanceField:
    def __init__(self, state: GameState, target: Tuple[int, int]):
        self.width, self.height = state.width, state.height
        self.dist = [[INF_DISTANCE] * state.width for _ in range(state.height)]
        other_bases = {b.position for b in state.bases if b.position != target}
        tx, ty = target
        self.dist[ty][tx] = 0
        heap = [(0, tx, ty)]
        while heap:
            d, x, y = heapq.heappop(heap)
            if d > self.dist[y][x]:
                continue
            step = 1 + state.walls.get((x, y), 0) if (x, y) != target else 1
            for direction in Direction:
                nx, ny = x + direction.dx, y + direction.dy
                if not (0 <= nx < self.width and 0 <= ny < self.height) or (nx, ny) in other_bases:
                    continue
                nd = d + step
                if nd < self.dist[ny][nx]:
                    self.dist[ny][nx] = nd
                    heapq.heappush(heap, (nd, nx, ny))

    def at(self, x: int, y: int) -> int:
        return self.dist[y][x]


class ReferenceHeuristicEvaluator:
    W_PROGRESS = 500.0
    W_DAMAGE = 200.0
    W_DISTANCE = 4.0
    MAX_DISTANCE = 150
    AIM_BASE = 60.0
    AIM_TANK = 45.0
    ALIGNED_FACTOR = 0.35
    W_BULLET = 50.0

    def __init__(self, rules: ReferenceRules):
        self.rules = rules
        self._fields: Optional[Tuple[ReferenceDistanceField, ReferenceDistanceField]] = None

    def prepare(self, state: GameState, player: int) -> None:
        """Distance fields are built from the ROOT state's walls and reused for the whole search."""
        self._fields = (ReferenceDistanceField(state, state.bases[0].position),
                        ReferenceDistanceField(state, state.bases[1].position))

    def evaluate(self, state: GameState, player: int) -> float:
        if self.rules.is_terminal(state):
            return self.rules.utility(state, player)
        fields = self._fields
        opponent = 1 - player
        me, enemy = state.tanks[player], state.tanks[opponent]
        my_base, enemy_base = state.bases[player], state.bases[opponent]

        enemy_tank_damage = 1 - enemy.hp / TANK_MAX_HP
        enemy_base_damage = 1 - enemy_base.hp / BASE_MAX_HP
        my_tank_damage = 1 - me.hp / TANK_MAX_HP
        my_base_damage = 1 - my_base.hp / BASE_MAX_HP
        score = self.W_PROGRESS * (max(enemy_tank_damage, enemy_base_damage) - max(my_tank_damage, my_base_damage))
        score += self.W_DAMAGE * (enemy_tank_damage + enemy_base_damage - my_tank_damage - my_base_damage)

        my_attack = min(fields[opponent].at(me.x, me.y), self.MAX_DISTANCE)
        enemy_attack = min(fields[player].at(enemy.x, enemy.y), self.MAX_DISTANCE)
        score += self.W_DISTANCE * (enemy_attack - my_attack)

        score += self.aim_value(state, me, enemy_base.x, enemy_base.y, self.AIM_BASE)
        score += self.aim_value(state, me, enemy.x, enemy.y, self.AIM_TANK)
        score -= self.aim_value(state, enemy, my_base.x, my_base.y, self.AIM_BASE)
        score -= self.aim_value(state, enemy, me.x, me.y, self.AIM_TANK)

        score += self.bullet_threat(state, player)
        return score

    def aim_value(self, state: GameState, tank: Tank, tx: int, ty: int, weight: float) -> float:
        if tank.hp <= 0 or (tank.x != tx and tank.y != ty):
            return 0.0
        dx = (tx > tank.x) - (tx < tank.x)
        dy = (ty > tank.y) - (ty < tank.y)
        x, y = tank.x + dx, tank.y + dy
        wall_hp = 0
        while (x, y) != (tx, ty):
            wall_hp += state.walls.get((x, y), 0)
            if _base_at(state, x, y) is not None:
                return 0.0
            x += dx
            y += dy
        facing = tank.facing.dx == dx and tank.facing.dy == dy
        factor = 1.0 if facing else self.ALIGNED_FACTOR
        return weight * factor / (1 + wall_hp)

    def bullet_threat(self, state: GameState, player: int) -> float:
        score = 0.0
        for bullet in state.bullets:
            x, y = bullet.x, bullet.y
            for _ in range(3 * self.rules.bullet_speed):
                x += bullet.direction.dx
                y += bullet.direction.dy
                if not (0 <= x < state.width and 0 <= y < state.height) or (x, y) in state.walls:
                    break
                victim = None
                for tank in state.tanks:
                    if tank.x == x and tank.y == y:
                        victim = tank.player
                base = _base_at(state, x, y)
                if base is not None:
                    victim = base.player
                if victim is not None:
                    score += self.W_BULLET if victim != player else -self.W_BULLET
                    break
        return score
