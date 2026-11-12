"""
Example plugin (template for other groups). Copy this file into plugins/, rename the class,
and implement choose_action(). It appears in the GUI menu after "Reload plugins".
"""
from task2_tank_battle.agents.base_agent import BaseAgent
from task2_tank_battle.core.actions import MOVE_DIRECTIONS, Action
from task2_tank_battle.core.game_rules import TankBattleRules


class GreedyHunterAgent(BaseAgent):
    """One-step greedy agent: fire when lined up with a target, otherwise step toward the enemy base."""

    name = "Greedy Hunter"

    def __init__(self):
        super().__init__()
        self.rules = TankBattleRules()

    def choose_action(self, state, player):
        me = state.tank(player)
        enemy_tank, enemy_base = state.tank(1 - player), state.base(1 - player)
        can_fire = Action.FIRE in self.rules.legal_actions(state, player)
        for target in (enemy_tank, enemy_base):
            if can_fire and self._facing_target(me, target):
                return Action.FIRE

        best_action, best_distance = None, abs(me.x - enemy_base.x) + abs(me.y - enemy_base.y)
        for action, direction in MOVE_DIRECTIONS.items():
            nx, ny = me.x + direction.dx, me.y + direction.dy
            if state.is_blocked_for_tank(nx, ny):
                continue
            distance = abs(nx - enemy_base.x) + abs(ny - enemy_base.y)
            if distance < best_distance:
                best_action, best_distance = action, distance
        if best_action is not None:
            return best_action

        # Blocked by walls: turn toward the base and shoot through.
        dx, dy = enemy_base.x - me.x, enemy_base.y - me.y
        if abs(dx) >= abs(dy):
            wanted = Action.MOVE_RIGHT if dx > 0 else Action.MOVE_LEFT
        else:
            wanted = Action.MOVE_DOWN if dy > 0 else Action.MOVE_UP
        if MOVE_DIRECTIONS[wanted] is me.facing:
            return Action.FIRE if can_fire else Action.STAY
        return wanted

    @staticmethod
    def _facing_target(me, target) -> bool:
        if me.x != target.x and me.y != target.y:
            return False
        dx = (target.x > me.x) - (target.x < me.x)
        dy = (target.y > me.y) - (target.y < me.y)
        return (me.facing.dx, me.facing.dy) == (dx, dy)
