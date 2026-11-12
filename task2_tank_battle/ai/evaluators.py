"""
Evaluation functions used at cut-off nodes of the search tree.
- TerminalOnlyEvaluator: no domain knowledge (plain Minimax / Alpha-Beta configurations).
- HeuristicEvaluator: EVAL(s) built from weighted features (Heuristic Minimax configurations).
"""
from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Tuple

from task2_tank_battle.core.actions import MOVE_DIRECTIONS, Action, Direction
from task2_tank_battle.core.entities import BASE_MAX_HP, TANK_MAX_HP, Tank
from task2_tank_battle.core.game_rules import TankBattleRules
from task2_tank_battle.core.game_state import GameState

INF_DISTANCE = 10 ** 6


class Evaluator(ABC):
    name = "Evaluator"

    def __init__(self, rules: TankBattleRules):
        self.rules = rules

    def prepare(self, state: GameState, player: int) -> None:
        """Called once at the root before each search (cache expensive data here)."""

    @abstractmethod
    def evaluate(self, state: GameState, player: int) -> float:
        """Score of `state` from the point of view of `player` (MAX). Higher is better for MAX."""

    def order_actions(self, state: GameState, player: int, actions: Sequence[Action]) -> List[Action]:
        return list(actions)


class TerminalOnlyEvaluator(Evaluator):
    """Returns UTILITY at terminal states and 0 ("unknown") elsewhere: pure Minimax without a heuristic."""

    name = "Terminal utility"

    def evaluate(self, state: GameState, player: int) -> float:
        if self.rules.is_terminal(state):
            return self.rules.utility(state, player)
        return 0.0


class DistanceField:
    """
    Dijkstra distance from every cell to a target base. Entering a wall costs 1 + its HP
    (shots needed to break it), so the field also tells how "far" a base is behind bricks.
    """

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


class HeuristicEvaluator(Evaluator):
    """
    EVAL(s) = progress + damage + distance + aim + bullet threats (all from MAX's point of view).
    Each feature is "mine minus the opponent's", so EVAL stays zero-sum like UTILITY.
    """

    name = "Heuristic EVAL"

    W_PROGRESS = 500.0
    W_DAMAGE = 200.0
    W_DISTANCE = 4.0
    MAX_DISTANCE = 150
    AIM_BASE = 60.0
    AIM_TANK = 45.0
    ALIGNED_FACTOR = 0.35
    W_BULLET = 50.0

    def __init__(self, rules: TankBattleRules):
        super().__init__(rules)
        self._fields: Optional[Tuple[DistanceField, DistanceField]] = None
        self._fields_key = None

    def prepare(self, state: GameState, player: int) -> None:
        key = (state.width, state.height, tuple(sorted(state.walls.items())))
        if key != self._fields_key:
            self._fields = (DistanceField(state, state.bases[0].position),
                            DistanceField(state, state.bases[1].position))
            self._fields_key = key

    def _ensure_fields(self, state: GameState) -> Tuple[DistanceField, DistanceField]:
        if self._fields is None or self._fields[0].width != state.width:
            self.prepare(state, 0)
        return self._fields

    # ------------------------------------------------------------------ EVAL(s)
    def evaluate(self, state: GameState, player: int) -> float:
        if self.rules.is_terminal(state):
            return self.rules.utility(state, player)
        fields = self._ensure_fields(state)
        opponent = 1 - player
        me, enemy = state.tanks[player], state.tanks[opponent]
        my_base, enemy_base = state.bases[player], state.bases[opponent]

        # 1) Progress: the game ends when EITHER the tank OR the base dies, so only the closer target counts.
        enemy_tank_damage = 1 - enemy.hp / TANK_MAX_HP
        enemy_base_damage = 1 - enemy_base.hp / BASE_MAX_HP
        my_tank_damage = 1 - me.hp / TANK_MAX_HP
        my_base_damage = 1 - my_base.hp / BASE_MAX_HP
        score = self.W_PROGRESS * (max(enemy_tank_damage, enemy_base_damage) - max(my_tank_damage, my_base_damage))

        # 2) Total damage dealt vs received (tie-breaker between equal progress).
        score += self.W_DAMAGE * (enemy_tank_damage + enemy_base_damage - my_tank_damage - my_base_damage)

        # 3) Distance: getting closer to the enemy base is good, the enemy getting closer to mine is bad.
        my_attack = min(fields[opponent].at(me.x, me.y), self.MAX_DISTANCE)
        enemy_attack = min(fields[player].at(enemy.x, enemy.y), self.MAX_DISTANCE)
        score += self.W_DISTANCE * (enemy_attack - my_attack)

        # 4) Aim: being lined up with a target (and facing it) is worth points.
        score += self.aim_value(state, me, enemy_base.x, enemy_base.y, self.AIM_BASE)
        score += self.aim_value(state, me, enemy.x, enemy.y, self.AIM_TANK)
        score -= self.aim_value(state, enemy, my_base.x, my_base.y, self.AIM_BASE)
        score -= self.aim_value(state, enemy, me.x, me.y, self.AIM_TANK)

        # 5) Bullets already flying toward a target.
        score += self.bullet_threat(state, player)
        return score

    def aim_value(self, state: GameState, tank: Tank, tx: int, ty: int, weight: float) -> float:
        """Value of tank -> target line of fire. Walls in between reduce it (1 / (1 + wall HP))."""
        if tank.hp <= 0 or (tank.x != tx and tank.y != ty):
            return 0.0
        dx = (tx > tank.x) - (tx < tank.x)
        dy = (ty > tank.y) - (ty < tank.y)
        x, y = tank.x + dx, tank.y + dy
        wall_hp = 0
        while (x, y) != (tx, ty):
            wall_hp += state.walls.get((x, y), 0)
            if state.base_at(x, y) is not None:
                return 0.0
            x += dx
            y += dy
        facing = tank.facing.dx == dx and tank.facing.dy == dy
        factor = 1.0 if facing else self.ALIGNED_FACTOR
        return weight * factor / (1 + wall_hp)

    def bullet_threat(self, state: GameState, player: int) -> float:
        """Trace each bullet's straight path: + if it will hit the enemy, - if it will hit us."""
        score = 0.0
        for bullet in state.bullets:
            x, y = bullet.x, bullet.y
            for _ in range(3 * self.rules.bullet_speed):
                x += bullet.direction.dx
                y += bullet.direction.dy
                if not state.is_inside(x, y) or (x, y) in state.walls:
                    break
                victim = None
                for tank in state.tanks:
                    if tank.x == x and tank.y == y:
                        victim = tank.player
                base = state.base_at(x, y)
                if base is not None:
                    victim = base.player
                if victim is not None:
                    score += self.W_BULLET if victim != player else -self.W_BULLET
                    break
        return score

    # ------------------------------------------------------------------ move ordering
    def order_actions(self, state: GameState, player: int, actions: Sequence[Action]) -> List[Action]:
        """
        Cheap guess of the best actions first (helps Alpha-Beta prune earlier). Sort is stable,
        so equal actions keep the (random) order given by the agent.
        """
        fields = self._ensure_fields(state)
        me = state.tanks[player]
        enemy = state.tanks[1 - player]
        enemy_base = state.bases[1 - player]
        here = fields[1 - player].at(me.x, me.y)

        def priority(action: Action) -> float:
            if action is Action.FIRE:
                if me.facing in self._directions_to(me, enemy, enemy_base):
                    return 4.0
                ahead = (me.x + me.facing.dx, me.y + me.facing.dy)
                return 1.5 if ahead in state.walls else 0.2
            direction = MOVE_DIRECTIONS.get(action)
            if direction is None:
                return 0.0
            nx, ny = me.x + direction.dx, me.y + direction.dy
            if state.is_blocked_for_tank(nx, ny):
                return 0.5
            return 2.0 + 0.5 * (here - fields[1 - player].at(nx, ny))

        return sorted(actions, key=priority, reverse=True)

    @staticmethod
    def _directions_to(me: Tank, *targets) -> set:
        result = set()
        for target in targets:
            if target.x == me.x:
                result.add(Direction.DOWN if target.y > me.y else Direction.UP)
            elif target.y == me.y:
                result.add(Direction.RIGHT if target.x > me.x else Direction.LEFT)
        return result
