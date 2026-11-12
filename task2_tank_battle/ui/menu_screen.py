"""
Menu screen: pick the controller of each player (human, 4 search configs, random, plugins) and the match settings.
"""
from __future__ import annotations

from dataclasses import replace

import pygame

from common.theme import Theme
from common.widgets import Button, OptionSelector, Toast, draw_panel, draw_text
from task2_tank_battle.core.map_loader import RANDOM_MAP_SIZES, MapLoader, build_initial_state
from task2_tank_battle.ui.renderer import PLAYER_COLORS, BattlefieldRenderer
from task2_tank_battle.ui.screen_base import SPEED_PRESETS, THINK_PRESETS, MatchSettings, Screen

DEPTH_OPTIONS = [str(d) for d in range(1, 7)]
SEED_OPTIONS = ["Random"] + [str(s) for s in range(1, 51)]
TURN_OPTIONS = ["100", "150", "200", "300", "400"]
PREVIEW_SEED = 2024


class MenuScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.toast = Toast()
        self.preview = BattlefieldRenderer()
        settings: MatchSettings = app.settings
        keys = app.registry.keys

        self.controller_selectors, self.depth_selectors = [], []
        for player in range(2):
            top = 140 + player * 220
            self.controller_selectors.append(OptionSelector(
                (80, top + 46, 300, 58), "Controller", keys,
                keys.index(settings.player_keys[player]) if settings.player_keys[player] in keys else 0))
            self.depth_selectors.append(OptionSelector(
                (80, top + 116, 300, 58), "Max search depth (cycles)", DEPTH_OPTIONS,
                DEPTH_OPTIONS.index(str(settings.depths[player]))))

        maps = MapLoader.available_maps() + list(RANDOM_MAP_SIZES)
        seed_label = "Random" if settings.seed is None else str(settings.seed)
        self.map_selector = OptionSelector((450, 186, 300, 58), "Map", maps,
                                           maps.index(settings.map_name) if settings.map_name in maps else 0)
        self.seed_selector = OptionSelector((450, 256, 300, 58), "Random seed", SEED_OPTIONS,
                                            SEED_OPTIONS.index(seed_label) if seed_label in SEED_OPTIONS else 0)
        self.turns_selector = OptionSelector((450, 326, 300, 58), "Max turns (then draw)", TURN_OPTIONS,
                                             TURN_OPTIONS.index(str(settings.max_turns)))
        self.think_selector = OptionSelector((450, 396, 300, 58), "AI think time (iterative deepening)",
                                             list(THINK_PRESETS), list(THINK_PRESETS).index(settings.think_label))
        self.speed_selector = OptionSelector((450, 466, 300, 58), "Animation speed", list(SPEED_PRESETS),
                                             list(SPEED_PRESETS).index(settings.speed_label))
        self.selectors = self.controller_selectors + self.depth_selectors + [
            self.map_selector, self.seed_selector, self.turns_selector, self.think_selector, self.speed_selector]

        self.buttons = [
            Button((450, 640, 300, 56), "START MATCH  (Enter)", self.start, "primary", pygame.K_RETURN, 19),
            Button((790, 640, 180, 56), "Reload plugins", self.reload_plugins, "ghost"),
            Button((990, 640, 150, 56), "Back (Esc)", self.app.close, "ghost"),
            Button((80, 640, 300, 56), "Swap players", self.swap_players, "ghost"),
        ]
        self._preview_key = None
        self._preview_state = None

    # ------------------------------------------------------------------ actions
    def collect_settings(self) -> MatchSettings:
        seed = None if self.seed_selector.value == "Random" else int(self.seed_selector.value)
        return replace(self.app.settings,
                       player_keys=tuple(s.value for s in self.controller_selectors),
                       depths=tuple(int(s.value) for s in self.depth_selectors),
                       map_name=self.map_selector.value, seed=seed,
                       max_turns=int(self.turns_selector.value),
                       think_label=self.think_selector.value, speed_label=self.speed_selector.value)

    def start(self) -> None:
        self.app.start_game(self.collect_settings())

    def swap_players(self) -> None:
        a, b = self.controller_selectors
        a.index, b.index = b.index, a.index
        c, d = self.depth_selectors
        c.index, d.index = d.index, c.index

    def reload_plugins(self) -> None:
        loaded = self.app.registry.load_plugins(self.app.extra_plugins)
        for selector in self.controller_selectors:
            selector.set_options(self.app.registry.keys)
        if self.app.registry.load_errors:
            self.toast.show("Plugin error: " + self.app.registry.load_errors[0], Theme.DANGER, 4)
        else:
            self.toast.show(f"{len(loaded)} plugin agent(s) loaded", Theme.SUCCESS)

    # ------------------------------------------------------------------ loop
    def handle_event(self, event: pygame.event.Event) -> None:
        for selector in self.selectors:
            if selector.handle_event(event):
                return
        for button in self.buttons:
            if button.handle_event(event):
                return

    def update(self, dt: float) -> None:
        self.toast.update(dt)
        for button in self.buttons:
            button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        draw_text(surface, "TANK BATTLE", (80, 34), 44, Theme.TEXT, bold=True)
        draw_text(surface, "Adversarial search arena  -  Minimax / Alpha-Beta / Heuristic Minimax",
                  (82, 92), 17, Theme.TEXT_MUTED)

        for player in range(2):
            rect = pygame.Rect(60, 130 + player * 220, 340, 205)
            draw_panel(surface, rect)
            pygame.draw.circle(surface, PLAYER_COLORS[player], (86, rect.y + 26), 8)
            side = "bottom, faces UP" if player == 0 else "top, faces DOWN"
            draw_text(surface, f"PLAYER {player + 1}", (102, rect.y + 15), 18, PLAYER_COLORS[player], bold=True)
            draw_text(surface, side, (210, rect.y + 18), 14, Theme.TEXT_MUTED)
            self.controller_selectors[player].draw(surface)
            spec = self.app.registry.spec(self.controller_selectors[player].value)
            if spec.uses_search:
                self.depth_selectors[player].draw(surface)
            else:
                note = "Keyboard controlled" if spec.key == "Human" else f"Source: {spec.source}"
                draw_text(surface, note, (80, rect.y + 150), 15, Theme.TEXT_DIM)

        draw_panel(surface, pygame.Rect(430, 130, 340, 410), "MATCH SETTINGS")
        for selector in self.selectors[4:]:
            selector.draw(surface)

        preview_rect = pygame.Rect(800, 130, 340, 410)
        inner = draw_panel(surface, preview_rect, "MAP PREVIEW")
        self._draw_preview(surface, inner)

        help_rect = pygame.Rect(60, 562, 1080, 62)
        draw_panel(surface, help_rect, color=Theme.SURFACE)
        draw_text(surface, "P1 keys:  W A S D move  |  SPACE fire  |  X stay", (84, 574), 15, PLAYER_COLORS[0])
        draw_text(surface, "P2 keys:  Arrows move  |  ENTER fire  |  Right SHIFT stay", (84, 598), 15, PLAYER_COLORS[1])
        plugins = sum(1 for key in self.app.registry.keys if self.app.registry.spec(key).source != "built-in")
        draw_text(surface, f"Plugins: put .py files in task2_tank_battle/plugins  ({plugins} loaded)",
                  (600, 586), 14, Theme.TEXT_MUTED)

        for button in self.buttons:
            button.draw(surface)
        self.toast.draw(surface)

    def _draw_preview(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        seed = PREVIEW_SEED if self.seed_selector.value == "Random" else int(self.seed_selector.value)
        key = (self.map_selector.value, seed)
        if key != self._preview_key:
            self._preview_state = build_initial_state(self.map_selector.value, seed)
            self._preview_key = key
        self.preview.fit(self._preview_state, area.inflate(0, -30))
        self.preview.draw(surface, self._preview_state)
        if self.map_selector.value in RANDOM_MAP_SIZES and self.seed_selector.value == "Random":
            draw_text(surface, "A new symmetric map is generated each match", (area.centerx, area.bottom - 8),
                      13, Theme.TEXT_MUTED, anchor="midbottom")
