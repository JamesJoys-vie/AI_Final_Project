"""Tank Battle application: owns the agent registry and switches between the menu and the game screen."""
from __future__ import annotations

from typing import List, Optional

import pygame

from common.app_base import BaseApp
from task2_tank_battle.agents.agent_registry import AgentRegistry
from task2_tank_battle.ui.game_screen import GameScreen
from task2_tank_battle.ui.menu_screen import MenuScreen
from task2_tank_battle.ui.screen_base import MatchSettings, Screen


class TankBattleApp(BaseApp):
    TITLE = "Tank Battle - Adversarial Search"

    def __init__(self, screen: Optional[pygame.Surface] = None, extra_plugins: Optional[List[str]] = None):
        super().__init__(screen)
        self.extra_plugins = extra_plugins or []
        self.registry = AgentRegistry()
        self.registry.load_plugins(self.extra_plugins)
        self.settings = MatchSettings()
        self.current: Screen = MenuScreen(self)

    def _switch(self, screen: Screen) -> None:
        self.current.on_exit()
        self.current = screen

    def show_menu(self) -> None:
        if isinstance(self.current, GameScreen):
            self.settings = self.current.settings
        self._switch(MenuScreen(self))

    def start_game(self, settings: MatchSettings) -> None:
        self.settings = settings
        self._switch(GameScreen(self, settings))

    # Delegate the loop to the active screen.
    def handle_event(self, event: pygame.event.Event) -> None:
        self.current.handle_event(event)

    def update(self, dt: float) -> None:
        self.current.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.current.draw(surface)

    def on_escape(self) -> None:
        self.current.on_escape()

    def on_exit(self) -> None:
        self.current.on_exit()
