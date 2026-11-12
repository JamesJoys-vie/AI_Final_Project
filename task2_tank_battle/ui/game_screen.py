"""
Game screen: runs the turn-based loop, reads keyboard input for humans and runs AI agents in background threads.
Turn flow:  THINKING (collect both actions)  ->  ANIMATING (slide tanks, fly bullets)  ->  THINKING ... -> OVER
"""
from __future__ import annotations

import math
import random
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from typing import List, Optional

import pygame

from common.theme import Theme
from common.widgets import Button, Toast, draw_bar, draw_panel, draw_text
from task2_tank_battle.agents.base_agent import BaseAgent
from task2_tank_battle.core.actions import Action
from task2_tank_battle.core.entities import BASE_MAX_HP, TANK_MAX_HP
from task2_tank_battle.core.game_rules import Outcome, TankBattleRules
from task2_tank_battle.core.map_loader import build_initial_state
from task2_tank_battle.ui.renderer import PLAYER_COLORS, BattlefieldRenderer
from task2_tank_battle.ui.screen_base import SPEED_PRESETS, MatchSettings, Screen

THINKING, ANIMATING, OVER = "thinking", "animating", "over"

KEYS_PLAYER_ONE = {pygame.K_w: Action.MOVE_UP, pygame.K_s: Action.MOVE_DOWN, pygame.K_a: Action.MOVE_LEFT,
                   pygame.K_d: Action.MOVE_RIGHT, pygame.K_SPACE: Action.FIRE, pygame.K_x: Action.STAY}
KEYS_PLAYER_TWO = {pygame.K_UP: Action.MOVE_UP, pygame.K_DOWN: Action.MOVE_DOWN, pygame.K_LEFT: Action.MOVE_LEFT,
                   pygame.K_RIGHT: Action.MOVE_RIGHT, pygame.K_RETURN: Action.FIRE, pygame.K_RSHIFT: Action.STAY}

EXPLOSION_STYLE = {
    "hit_wall": (False, (230, 140, 70)), "destroy_wall": (True, (200, 110, 60)),
    "hit_tank": (False, (255, 90, 80)), "destroy_tank": (True, (255, 120, 60)),
    "hit_base": (False, (255, 220, 90)), "destroy_base": (True, (255, 200, 80)),
}


class GameScreen(Screen):
    def __init__(self, app, settings: MatchSettings):
        super().__init__(app)
        self.settings = settings
        self.rules = TankBattleRules()
        self.renderer = BattlefieldRenderer()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.board_area = pygame.Rect(20, 70, 690, 672)
        self.toast = Toast()
        self.speed_labels = list(SPEED_PRESETS)
        self.speed_index = self.speed_labels.index(settings.speed_label)
        x, y = 730, 700
        self.pause_button = Button((x, y, 84, 44), "Pause", self.toggle_pause, "ghost", pygame.K_p, 15)
        self.control_buttons = [
            self.pause_button,
            Button((x + 92, y, 84, 44), "Step", self.request_step, "ghost", pygame.K_n, 15),
            Button((x + 184, y, 84, 44), "Speed", self.cycle_speed, "ghost", pygame.K_f, 15),
            Button((x + 276, y, 84, 44), "Restart", self.start_match, "ghost", pygame.K_r, 15),
            Button((x + 368, y, 82, 44), "Menu", self.app.show_menu, "ghost", None, 15),
        ]
        self.over_buttons = [
            Button((0, 0, 120, 48), "Rematch", self.start_match, "primary"),
            Button((0, 0, 140, 48), "Swap sides", self.swap_sides, "ghost"),
            Button((0, 0, 100, 48), "Menu", self.app.show_menu, "ghost"),
        ]
        self.start_match()

    # ------------------------------------------------------------------ match lifecycle
    def start_match(self) -> None:
        self.map_seed = self.settings.seed if self.settings.seed is not None else random.randrange(1, 10 ** 6)
        self.state = build_initial_state(self.settings.map_name, self.map_seed, self.settings.max_turns)
        self.previous = None
        self.agents: List[BaseAgent] = [
            self.app.registry.create(key, depth, self.settings.think_time, self.map_seed + player)
            for player, (key, depth) in enumerate(zip(self.settings.player_keys, self.settings.depths))]
        for player, agent in enumerate(self.agents):
            agent.reset(player)
        self.humans = [agent.is_human for agent in self.agents]
        self.renderer.fit(self.state, self.board_area)
        self.renderer.particles.clear()
        self._layout_over_buttons()
        self.log = deque(maxlen=7)
        self.last_actions: List[Optional[Action]] = [None, None]
        self.futures: List[Optional[Future]] = [None, None]
        self.paused = False
        self.step_requested = False
        self.wait_timer = 0.0
        self.anim = 0.0
        self.phase = THINKING
        self._request_actions()

    def swap_sides(self) -> None:
        self.settings = self.settings.swapped()
        self.start_match()

    def _request_actions(self) -> None:
        """
        Start AI agents in worker threads so the window stays smooth while they search.
        GameState is immutable, so sharing it with a thread is safe.
        """
        self.wait_timer = 0.0
        for player, agent in enumerate(self.agents):
            self.futures[player] = None if agent.is_human else \
                self.executor.submit(self._safe_think, agent, self.state, player)

    @staticmethod
    def _safe_think(agent: BaseAgent, state, player: int) -> Action:
        try:
            return agent.choose_action(state, player)
        except Exception:
            return Action.STAY

    def _player_ready(self, player: int) -> bool:
        if self.humans[player]:
            return self.agents[player].has_action
        return self.futures[player] is not None and self.futures[player].done()

    def _apply_turn(self) -> None:
        actions = []
        for player, agent in enumerate(self.agents):
            actions.append(agent.choose_action(self.state, player) if self.humans[player]
                           else self.futures[player].result())
        self.last_actions = actions
        self.previous = self.state
        self.state = self.rules.step(self.state, (actions[0], actions[1]), record=True)
        self.anim = 0.0
        self.phase = ANIMATING

    def _finish_animation(self) -> None:
        for event in self.state.events:
            if event.kind in EXPLOSION_STYLE:
                big, color = EXPLOSION_STYLE[event.kind]
                self.renderer.spawn_explosion(event.x, event.y, big, color)
            if event.kind in ("hit_tank", "destroy_tank", "hit_base", "destroy_base"):
                self.log.appendleft((f"T{self.state.turn:03d}  P{event.owner + 1} hit -> {event.detail}",
                                     PLAYER_COLORS[event.owner]))
        self.previous = None
        if self.rules.is_terminal(self.state):
            self.phase = OVER
        else:
            self.phase = THINKING
            self._request_actions()

    # ------------------------------------------------------------------ controls
    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.toast.show("Paused  (N = one step)" if self.paused else "Resumed", Theme.TEXT, 1.5)

    def request_step(self) -> None:
        self.step_requested = True

    def cycle_speed(self) -> None:
        self.speed_index = (self.speed_index + 1) % len(self.speed_labels)
        self.toast.show(f"Speed: {self.speed_labels[self.speed_index]}", Theme.TEXT, 1.2)

    @property
    def turn_duration(self) -> float:
        return SPEED_PRESETS[self.speed_labels[self.speed_index]]

    def on_escape(self) -> None:
        self.app.show_menu()

    def on_exit(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        buttons = self.over_buttons if self.phase == OVER else []
        for button in buttons + self.control_buttons:
            if button.handle_event(event):
                return
        if event.type == pygame.KEYDOWN and self.phase != OVER:
            self._handle_human_key(event.key)

    def _handle_human_key(self, key: int) -> None:
        """With one human, both key sets control that human; with two humans each has its own keys."""
        human_players = [p for p in range(2) if self.humans[p]]
        if not human_players:
            return
        for player, keymap in enumerate((KEYS_PLAYER_ONE, KEYS_PLAYER_TWO)):
            if key not in keymap:
                continue
            target = player if len(human_players) == 2 else human_players[0]
            action = keymap[key]
            if action is Action.FIRE and Action.FIRE not in self.rules.legal_actions(self.state, target):
                self.toast.show("Your bullet is still flying", Theme.WARNING, 1.0)
            self.agents[target].submit(action)

    # ------------------------------------------------------------------ update / draw
    def update(self, dt: float) -> None:
        self.renderer.update(dt)
        self.toast.update(dt)
        for button in self.control_buttons + (self.over_buttons if self.phase == OVER else []):
            button.update(dt)

        if self.phase == THINKING:
            self.wait_timer += dt
            if self.paused and not self.step_requested:
                return
            if not all(self._player_ready(p) for p in range(2)):
                return
            # AI-only matches wait a little between turns so humans can follow the action.
            if not any(self.humans) and self.wait_timer < self.turn_duration * 0.5 and not self.step_requested:
                return
            self.step_requested = False
            self._apply_turn()
        elif self.phase == ANIMATING:
            duration = min(self.turn_duration, 0.22) if any(self.humans) else self.turn_duration
            self.anim += dt / max(0.01, duration)
            if self.anim >= 1.0:
                self._finish_animation()

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_header(surface)
        progress = self.anim if self.phase == ANIMATING else 1.0
        self.renderer.draw(surface, self.state, self.previous, progress)
        for player in range(2):
            self._draw_player_card(surface, player, pygame.Rect(730, 70 + player * 236, 450, 222))
        self._draw_log(surface, pygame.Rect(730, 546, 450, 142))
        self.pause_button.label = "Resume" if self.paused else "Pause"
        for button in self.control_buttons:
            button.draw(surface)
        if self.phase == OVER:
            self._draw_game_over(surface)
        self.toast.draw(surface)

    def _draw_header(self, surface: pygame.Surface) -> None:
        draw_text(surface, "TANK BATTLE", (24, 20), 28, Theme.TEXT, bold=True)
        draw_text(surface, f"{self.settings.map_name}  |  seed {self.map_seed}", (220, 30), 15, Theme.TEXT_MUTED)
        status = {THINKING: "Waiting for actions", ANIMATING: "Resolving turn", OVER: "Game over"}[self.phase]
        if self.paused:
            status = "Paused"
        draw_text(surface, f"Turn {self.state.turn} / {self.state.max_turns}   -   {status}",
                  (710, 30), 16, Theme.TEXT, bold=True, anchor="topright")
        draw_text(surface, f"Speed: {self.speed_labels[self.speed_index]}", (1180, 30), 15, Theme.TEXT_MUTED,
                  anchor="topright")

    def _draw_player_card(self, surface: pygame.Surface, player: int, rect: pygame.Rect) -> None:
        draw_panel(surface, rect)
        color = PLAYER_COLORS[player]
        agent = self.agents[player]
        tank, base = self.state.tanks[player], self.state.bases[player]
        pygame.draw.circle(surface, color, (rect.x + 24, rect.y + 26), 8)
        draw_text(surface, f"PLAYER {player + 1}", (rect.x + 40, rect.y + 14), 18, color, bold=True)
        draw_text(surface, agent.name, (rect.right - 20, rect.y + 16), 16, Theme.TEXT, bold=True, anchor="topright")

        for row, (label, hp, max_hp) in enumerate((("Tank", tank.hp, TANK_MAX_HP), ("Base", base.hp, BASE_MAX_HP))):
            y = rect.y + 52 + row * 30
            draw_text(surface, label, (rect.x + 20, y - 2), 15, Theme.TEXT_MUTED)
            draw_bar(surface, pygame.Rect(rect.x + 70, y + 4, 280, 10), hp / max_hp,
                     Theme.DANGER if hp <= max_hp // 3 else color)
            draw_text(surface, f"{max(hp, 0)} / {max_hp}", (rect.right - 20, y - 2), 15, Theme.TEXT, anchor="topright")

        last = self.last_actions[player].name if self.last_actions[player] else "-"
        draw_text(surface, f"Last action: {last}", (rect.x + 20, rect.y + 118), 15, Theme.TEXT)

        stats = agent.last_stats
        if self.humans[player]:
            waiting = self.phase == THINKING and not agent.has_action
            keys = "W A S D + SPACE" if player == 0 or sum(self.humans) == 1 else "Arrows + ENTER"
            message = f"Your move!  ({keys})" if waiting else "Move locked in"
            draw_text(surface, message, (rect.x + 20, rect.y + 150), 16,
                      Theme.GOLD if waiting else Theme.SUCCESS, bold=True)
        elif stats is not None:
            draw_text(surface, f"Depth {stats.depth} cycles ({2 * stats.depth} plies)   value {stats.value:.1f}",
                      (rect.x + 20, rect.y + 146), 14, Theme.TEXT_MUTED)
            draw_text(surface, f"Nodes {stats.nodes_generated:,}   pruned {stats.prunings:,}   "
                               f"{stats.elapsed * 1000:.1f} ms", (rect.x + 20, rect.y + 170), 14, Theme.TEXT_MUTED)
        if not self.humans[player] and self.phase == THINKING and not self._player_ready(player):
            self._draw_spinner(surface, (rect.right - 34, rect.bottom - 30), color)
            draw_text(surface, "thinking", (rect.right - 54, rect.bottom - 38), 14, color, anchor="topright")

    @staticmethod
    def _draw_spinner(surface: pygame.Surface, center, color) -> None:
        angle = pygame.time.get_ticks() / 150.0
        rect = pygame.Rect(0, 0, 22, 22)
        rect.center = center
        pygame.draw.arc(surface, color, rect, angle, angle + math.pi * 1.4, 3)

    def _draw_log(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        inner = draw_panel(surface, rect, "BATTLE LOG")
        if not self.log:
            draw_text(surface, "No hits yet", (inner.x, inner.y), 14, Theme.TEXT_DIM)
        for i, (line, color) in enumerate(list(self.log)[:5]):
            draw_text(surface, line, (inner.x, inner.y + i * 19), 14, color, mono=True)

    def _draw_game_over(self, surface: pygame.Surface) -> None:
        board = self.renderer.board_rect(self.state)
        shade = pygame.Surface(board.size, pygame.SRCALPHA)
        shade.fill((10, 12, 18, 190))
        surface.blit(shade, board.topleft)
        outcome = self.rules.outcome(self.state)
        winner = self.rules.winner(self.state)
        color = PLAYER_COLORS[winner] if winner is not None else Theme.TEXT
        title = "DRAW" if outcome is Outcome.DRAW else f"PLAYER {winner + 1} WINS"
        draw_text(surface, title, (board.centerx, board.centery - 70), 46, color, bold=True, anchor="center")
        if winner is not None:
            draw_text(surface, self.agents[winner].name, (board.centerx, board.centery - 22), 20, Theme.TEXT,
                      anchor="center")
        reason = "turn limit reached" if self.state.turn >= self.state.max_turns and outcome is Outcome.DRAW \
            else f"after {self.state.turn} turns"
        draw_text(surface, reason, (board.centerx, board.centery + 10), 16, Theme.TEXT_MUTED, anchor="center")
        for button in self.over_buttons:
            button.draw(surface)

    def _layout_over_buttons(self) -> None:
        board = self.renderer.board_rect(self.state)
        x = board.centerx - sum(b.rect.width for b in self.over_buttons) // 2 - 10
        for button in self.over_buttons:
            button.rect.topleft = (x, board.centery + 50)
            x += button.rect.width + 10
