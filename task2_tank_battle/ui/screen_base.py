"""Screen interface (State pattern: the app switches between Menu and Game screens) and match settings."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

import pygame

SPEED_PRESETS = {"Slow": 0.55, "Normal": 0.30, "Fast": 0.12, "Turbo": 0.03}
THINK_PRESETS = {"0.2 s": 0.2, "0.5 s": 0.5, "1.0 s": 1.0, "No limit": None}


@dataclass
class MatchSettings:
    player_keys: tuple = ("Human", "Heuristic Alpha-Beta")
    depths: tuple = (3, 3)
    map_name: str = "classic"
    seed: Optional[int] = None
    max_turns: int = 200
    think_label: str = "0.5 s"
    speed_label: str = "Normal"

    @property
    def think_time(self) -> Optional[float]:
        return THINK_PRESETS[self.think_label]

    @property
    def turn_duration(self) -> float:
        return SPEED_PRESETS[self.speed_label]

    def swapped(self) -> "MatchSettings":
        return replace(self, player_keys=self.player_keys[::-1], depths=self.depths[::-1])


class Screen:
    def __init__(self, app):
        self.app = app

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass

    def on_escape(self) -> None:
        self.app.close()

    def on_exit(self) -> None:
        pass
