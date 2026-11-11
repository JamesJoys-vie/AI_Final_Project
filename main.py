"""Launcher hub: one window with a card per task. Run from the `source` folder:  python main.py"""
from __future__ import annotations

from typing import Callable, List, NamedTuple

import pygame

from common.app_base import BaseApp
from common.theme import Theme
from common.widgets import Toast, draw_text, lerp_color, wrap_text


class TaskCard(NamedTuple):
    title: str
    subtitle: str
    description: str
    owner: str
    accent: tuple
    launch: Callable[[pygame.Surface], BaseApp]


def _nqueens(screen):
    from task1_nqueens.ui.nqueens_app import NQueensApp
    return NQueensApp(screen)


def _tank_battle(screen):
    from task2_tank_battle.ui.tank_battle_app import TankBattleApp
    return TankBattleApp(screen)


def _kakuro(screen):
    from task3_kakuro.ui.kakuro_app import KakuroApp
    return KakuroApp(screen)


CARDS = [
    TaskCard("N-Queens", "Task 1 - Local Search & Propositional Logic",
             "CNF encoding solved by Glucose3, Min-Conflicts with a max-conflict + tabu heuristic. "
             "Place queens yourself and let SAT complete the board.",
             "Trinh Hai Huy", Theme.GOLD, _nqueens),
    TaskCard("Tank Battle", "Task 2 - Adversarial Search",
             "Minimax, Alpha-Beta, Heuristic Minimax and Heuristic Alpha-Beta. Play against the AI "
             "with the keyboard or load agents written by other groups.",
             "Phan Huy Binh", Theme.SUCCESS, _tank_battle),
    TaskCard("Kakuro", "Task 3 - Constraint Satisfaction",
             "GAC-3 propagation + backtracking with MRV, Degree and LCV. Replay every domain change "
             "step by step or solve the puzzle yourself.",
             "Tran Hong Nhat Duy", Theme.ACCENT, _kakuro),
]


class LauncherApp(BaseApp):
    TITLE = "AI Final Project - Group N04"

    def __init__(self):
        super().__init__()
        self.rects: List[pygame.Rect] = [pygame.Rect(60 + i * 370, 200, 340, 420) for i in range(len(CARDS))]
        self.hover = [0.0] * len(CARDS)
        self.toast = Toast()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, card in zip(self.rects, CARDS):
                if rect.collidepoint(event.pos):
                    self._open(card)
        elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_3:
            self._open(CARDS[event.key - pygame.K_1])

    def _open(self, card: TaskCard) -> None:
        """Run the task app inside the same window; come back here when it closes."""
        try:
            app = card.launch(self.screen)
        except ImportError:
            # This checkout does not contain that task's folder yet (e.g. a member-only package).
            self.toast.show(f"{card.title} is not in this checkout yet", Theme.WARNING)
            return
        keep_running = app.run()
        pygame.display.set_caption(self.TITLE)
        if not keep_running:
            self.close()

    def update(self, dt: float) -> None:
        self.toast.update(dt)
        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(self.rects):
            target = 1.0 if rect.collidepoint(mouse) else 0.0
            self.hover[i] += (target - self.hover[i]) * min(1.0, dt * 10)

    def draw(self, surface: pygame.Surface) -> None:
        draw_text(surface, "INTRODUCTION TO AI - FINAL PROJECT", (60, 60), 36, Theme.TEXT, bold=True)
        draw_text(surface, "Group N04  |  choose a task (click or press 1-3)  |  Esc to quit", (62, 112), 17,
                  Theme.TEXT_MUTED)
        for i, (rect, card) in enumerate(zip(self.rects, CARDS)):
            lifted = rect.move(0, -int(8 * self.hover[i]))
            pygame.draw.rect(surface, lerp_color(Theme.SURFACE, Theme.SURFACE_LIGHT, self.hover[i]), lifted,
                             border_radius=16)
            pygame.draw.rect(surface, card.accent, (lifted.x, lifted.y, lifted.width, 8), border_radius=16)
            draw_text(surface, f"{i + 1}", (lifted.right - 28, lifted.y + 26), 18, Theme.TEXT_DIM, True, "topright")
            draw_text(surface, card.title, (lifted.x + 28, lifted.y + 40), 32, card.accent, bold=True)
            draw_text(surface, card.subtitle, (lifted.x + 28, lifted.y + 88), 15, Theme.TEXT_MUTED, bold=True)
            for j, line in enumerate(wrap_text(card.description, 16, lifted.width - 56)):
                draw_text(surface, line, (lifted.x + 28, lifted.y + 130 + j * 24), 16, Theme.TEXT)
            draw_text(surface, f"Owner: {card.owner}", (lifted.x + 28, lifted.bottom - 76), 14, Theme.TEXT_MUTED)
            button = pygame.Rect(lifted.x + 28, lifted.bottom - 52, lifted.width - 56, 36)
            pygame.draw.rect(surface, lerp_color(Theme.SURFACE_HOVER, card.accent, self.hover[i]), button,
                             border_radius=10)
            draw_text(surface, "Open", button.center, 16, Theme.BACKGROUND if self.hover[i] > 0.5 else Theme.TEXT,
                      True, "center")
        self.toast.draw(surface)


if __name__ == "__main__":
    LauncherApp().run()
    pygame.quit()
