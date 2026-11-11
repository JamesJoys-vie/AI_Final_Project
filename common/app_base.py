"""Base class for every PyGame screen: owns the main loop (events -> update -> draw)."""
from __future__ import annotations

from typing import Optional

import pygame

from common.theme import FPS, WINDOW_SIZE, Theme


class BaseApp:
    """Template Method pattern: subclasses override handle_event / update / draw only."""

    TITLE = "AI Final Project"

    def __init__(self, screen: Optional[pygame.Surface] = None):
        if screen is None:
            pygame.init()
            screen = pygame.display.set_mode(WINDOW_SIZE)
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = False
        self.quit_requested = False

    def run(self) -> bool:
        """Run until the screen closes. Returns False if the user closed the whole window."""
        pygame.display.set_caption(self.TITLE)
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_requested = True
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.on_escape()
                else:
                    self.handle_event(event)
            self.update(dt)
            self.screen.fill(Theme.BACKGROUND)
            self.draw(self.screen)
            pygame.display.flip()
        self.on_exit()
        return not self.quit_requested

    def close(self) -> None:
        self.running = False

    def on_escape(self) -> None:
        self.close()

    def on_exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass
