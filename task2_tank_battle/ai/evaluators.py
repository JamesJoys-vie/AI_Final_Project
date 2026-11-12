"""
Evaluation functions used at cut-off nodes of the search tree.
- TerminalOnlyEvaluator: no domain knowledge (plain Minimax / Alpha-Beta configurations).
- HeuristicEvaluator: EVAL(s) built from weighted features (Heuristic Minimax configurations).
"""
from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Tuple

from task2_tank_battle.core.actions import Action, Direction
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

    def evaluate_nonterminal(self, state: GameState, player: int) -> float:
        """
        evaluate() for a state the caller already knows is NOT terminal. The search tests terminal states
        itself (they always get the exact UTILITY), so evaluators can skip that second check.
        """
        return self.evaluate(state, player)

    def order_actions(self, state: GameState, player: int, actions: Sequence[Action]) -> List[Action]:
        return list(actions)


class TerminalOnlyEvaluator(Evaluator):
    """Returns UTILITY at terminal states and 0 ("unknown") elsewhere: pure Minimax without a heuristic."""

    name = "Terminal utility"

    def evaluate(self, state: GameState, player: int) -> float:
        if self.rules.is_terminal(state):
            return self.rules.utility(state, player)
        return 0.0

    def evaluate_nonterminal(self, state: GameState, player: int) -> float:
        return 0.0


class DistanceField:
    """
    Dijkstra distance from every cell to a target base. Entering a wall costs 1 + its HP
    (shots needed to break it), so the field also tells how "far" a base is behind bricks.
    `dist[y][x]` is read directly in the evaluator's inner loop.
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
        return self.evaluate_nonterminal(state, player)

    def evaluate_nonterminal(self, state: GameState, player: int) -> float:
        fields = self._fields
        if fields is None or fields[0].width != state.width:
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
        my_attack = min(fields[opponent].dist[me.y][me.x], self.MAX_DISTANCE)
        enemy_attack = min(fields[player].dist[enemy.y][enemy.x], self.MAX_DISTANCE)
        score += self.W_DISTANCE * (enemy_attack - my_attack)

        # 4) Aim: being lined up with a target (and facing it) is worth points.
        score += self.aim_value(state, me, enemy_base.x, enemy_base.y, self.AIM_BASE)
        score += self.aim_value(state, me, enemy.x, enemy.y, self.AIM_TANK)
        score -= self.aim_value(state, enemy, my_base.x, my_base.y, self.AIM_BASE)
        score -= self.aim_value(state, enemy, me.x, me.y, self.AIM_TANK)

        # 5) Bullets already flying toward a target.
        if state.bullets:
            score += self.bullet_threat(state, player)
        return score

    def aim_value(self, state: GameState, tank: Tank, tx: int, ty: int, weight: float) -> float:
        """Value of tank -> target line of fire. Walls in between reduce it (1 / (1 + wall HP))."""
        x, y = tank.x, tank.y
        if tank.hp <= 0 or (x != tx and y != ty):
            return 0.0
        dx = (tx > x) - (tx < x)
        dy = (ty > y) - (ty < y)
        x += dx
        y += dy
        if x != tx or y != ty:
            walls = state.walls
            base1, base2 = state.bases
            b1x, b1y, b2x, b2y = base1.x, base1.y, base2.x, base2.y
            wall_hp = 0
            while x != tx or y != ty:
                if (x == b1x and y == b1y) or (x == b2x and y == b2y):
                    return 0.0  # a base blocks the line of fire
                wall_hp += walls.get((x, y), 0)
                x += dx
                y += dy
        else:
            wall_hp = 0
        facing = tank.facing
        factor = 1.0 if (facing.dx == dx and facing.dy == dy) else self.ALIGNED_FACTOR
        return weight * factor / (1 + wall_hp)

    def bullet_threat(self, state: GameState, player: int) -> float:
        """Trace each bullet's straight path: + if it will hit the enemy, - if it will hit us."""
        score = 0.0
        width, height, walls = state.width, state.height, state.walls
        tank1, tank2 = state.tanks
        base1, base2 = state.bases
        cells = 3 * self.rules.bullet_speed
        for bullet in state.bullets:
            x, y = bullet.x, bullet.y
            dx, dy = bullet.direction.dx, bullet.direction.dy
            for _ in range(cells):
                x += dx
                y += dy
                if x < 0 or y < 0 or x >= width or y >= height or (x, y) in walls:
                    break
                # A base on the cell decides the victim; otherwise the (last) tank on it does.
                if base1.x == x and base1.y == y:
                    victim = base1.player
                elif base2.x == x and base2.y == y:
                    victim = base2.player
                elif tank2.x == x and tank2.y == y:
                    victim = tank2.player
                elif tank1.x == x and tank1.y == y:
                    victim = tank1.player
                else:
                    continue
                score += self.W_BULLET if victim != player else -self.W_BULLET
                break
        return score

    # ------------------------------------------------------------------ move ordering
    def order_actions(self, state: GameState, player: int, actions: Sequence[Action]) -> List[Action]:
        """
        Cheap guess of the best actions first (helps Alpha-Beta prune earlier). Sort is stable,
        so equal actions keep the (random) order given by the agent.
        Priorities: FIRE at a target 4 > moves 2 + 0.5 * (distance gained) > FIRE at a wall 1.5
        > blocked move 0.5 > FIRE elsewhere 0.2 > STAY 0.
        """
        field = self._ensure_fields(state)[1 - player].dist
        me = state.tanks[player]
        mx, my, facing = me.x, me.y, me.facing
        here = field[my][mx]
        width, height, walls = state.width, state.height, state.walls
        base1, base2 = state.bases

        priorities = []
        for action in actions:
            direction = action.move_direction
            if direction is not None:
                nx, ny = mx + direction.dx, my + direction.dy
                if (nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in walls
                        or (nx == base1.x and ny == base1.y) or (nx == base2.x and ny == base2.y)):
                    priority = 0.5
                else:
                    priority = 2.0 + 0.5 * (here - field[ny][nx])
            elif action is Action.FIRE:
                if self._facing_a_target(me, state.tanks[1 - player], state.bases[1 - player]):
                    priority = 4.0
                else:
                    priority = 1.5 if (mx + facing.dx, my + facing.dy) in walls else 0.2
            else:
                priority = 0.0
            priorities.append(priority)
        order = sorted(range(len(priorities)), key=priorities.__getitem__, reverse=True)
        return [actions[i] for i in order]

    @staticmethod
    def _facing_a_target(me: Tank, *targets) -> bool:
        """True if `me` faces a target in the same row or column (walls in between are ignored)."""
        facing = me.facing
        for target in targets:
            if target.x == me.x:
                if facing is (Direction.DOWN if target.y > me.y else Direction.UP):
                    return True
            elif target.y == me.y:
                if facing is (Direction.RIGHT if target.x > me.x else Direction.LEFT):
                    return True
        return False
