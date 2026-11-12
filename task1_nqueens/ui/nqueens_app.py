"""
Interactive N-Queens board: click to place queens, see attacking pairs live, run SAT / Min-Conflicts
(with step-by-step animation) or let SAT complete the queens you placed.
"""
from __future__ import annotations

import random
from typing import Iterator, List, Optional

import pygame

from common.app_base import BaseApp
from common.theme import Theme
from common.widgets import Button, OptionSelector, Toast, draw_panel, draw_text
from task1_nqueens.core.board import QueenBoard
from task1_nqueens.solvers.min_conflicts import MinConflictsSolver, MinConflictsStep
from task1_nqueens.solvers.sat_solver import SatNQueensSolver
from task1_nqueens.solvers.variable_selectors import MaxConflictTabuSelector, RandomConflictedSelector

SIZE_OPTIONS = [str(n) for n in range(4, 21)]
LIGHT_SQUARE = (70, 78, 102)
DARK_SQUARE = (46, 52, 70)
QUEEN_COLOR = (255, 200, 80)
CONFLICT_COLOR = (255, 96, 96)


class NQueensApp(BaseApp):
    TITLE = "N-Queens - Propositional Logic & Local Search"

    def __init__(self, screen: Optional[pygame.Surface] = None):
        super().__init__(screen)
        self.board = QueenBoard(8)
        self.board_area = pygame.Rect(30, 70, 670, 670)
        self.toast = Toast()
        self.rng = random.Random()
        self.animate = True
        self.animation: Optional[Iterator[MinConflictsStep]] = None
        self.anim_solver: Optional[MinConflictsSolver] = None
        self.anim_timer = 0.0
        self.last_step: Optional[MinConflictsStep] = None
        self.result_lines: List[str] = ["Click squares to place queens,", "or run a solver."]

        self.size_selector = OptionSelector((750, 108, 180, 58), "Board size N", SIZE_OPTIONS,
                                            SIZE_OPTIONS.index("8"), self._on_size_change)
        x, w = 750, 400
        self.animate_button = Button((950, 120, 200, 44), "Animation: ON", self.toggle_animation, "ghost", None, 15)
        self.buttons = [
            Button((x, 312, w, 44), "Solve with SAT (Glucose3)", self.run_sat, "primary", pygame.K_1),
            Button((x, 362, w, 44), "Min-Conflicts - standard", lambda: self.run_min_conflicts(False),
                   "primary", pygame.K_2),
            Button((x, 412, w, 44), "Min-Conflicts - heuristic (max-conflict + tabu)",
                   lambda: self.run_min_conflicts(True), "primary", pygame.K_3, 15),
            Button((x, 462, w, 44), "Complete my board (SAT with assumptions)", self.complete_board,
                   "success", pygame.K_4, 15),
            Button((750, 696, 120, 44), "Random", self.random_board, "ghost", pygame.K_r),
            Button((880, 696, 120, 44), "Clear", self.clear_board, "ghost", pygame.K_c),
            Button((1010, 696, 140, 44), "Back (Esc)", self.close, "ghost"),
            self.animate_button,
        ]

    # ------------------------------------------------------------------ helpers
    @property
    def n(self) -> int:
        return self.board.n

    @property
    def cell(self) -> int:
        return self.board_area.width // self.n

    def _cell_rect(self, row: int, col: int) -> pygame.Rect:
        return pygame.Rect(self.board_area.x + col * self.cell, self.board_area.y + row * self.cell, self.cell, self.cell)

    def _cell_at(self, pos) -> Optional[tuple]:
        x, y = pos[0] - self.board_area.x, pos[1] - self.board_area.y
        if 0 <= x < self.cell * self.n and 0 <= y < self.cell * self.n:
            return y // self.cell, x // self.cell
        return None

    def _stop_animation(self) -> None:
        self.animation = None
        self.last_step = None

    # ------------------------------------------------------------------ actions
    def _on_size_change(self, index: int) -> None:
        self._stop_animation()
        self.board = QueenBoard(int(SIZE_OPTIONS[index]))
        self.result_lines = [f"New {self.n} x {self.n} board."]

    def toggle_animation(self) -> None:
        self.animate = not self.animate
        self.animate_button.label = f"Animation: {'ON' if self.animate else 'OFF'}"

    def clear_board(self) -> None:
        self._stop_animation()
        self.board.clear()

    def random_board(self) -> None:
        self._stop_animation()
        self.board = QueenBoard.from_columns([self.rng.randrange(self.n) for _ in range(self.n)])

    def run_sat(self) -> None:
        self._stop_animation()
        result = SatNQueensSolver().solve(self.n)
        self.board = QueenBoard.from_columns(result.columns)
        self.result_lines = [f"Glucose3: {'SAT' if result.solved else 'UNSAT'}",
                             f"{result.variables} variables, {result.clauses:,} clauses",
                             f"encode {result.extra['encode_time'] * 1000:.2f} ms, "
                             f"solve {result.elapsed * 1000:.2f} ms"]
        extra = result.extra
        self.result_lines += [f"ALO rows {extra['at-least-one (row)']} | AMO rows {extra['at-most-one (row)']}"
                              f" | AMO cols {extra['at-most-one (column)']}",
                              f"AMO diagonals {extra['at-most-one (diagonal)'] + extra['at-most-one (anti-diagonal)']}"]

    def complete_board(self) -> None:
        """
        Extra feature: keep the user's queens as assumptions and let SAT fill the rest (or prove it impossible).
        """
        self._stop_animation()
        fixed = sorted(self.board.queens)
        result = SatNQueensSolver().solve(self.n, fixed)
        if result.solved:
            self.board = QueenBoard.from_columns(result.columns)
            self.result_lines = [f"Completed from your {len(fixed)} queen(s).",
                                 f"solve {result.elapsed * 1000:.2f} ms"]
            self.toast.show("Board completed by SAT", Theme.SUCCESS)
        else:
            self.result_lines = ["UNSAT: no solution keeps", f"all your {len(fixed)} queen(s)."]
            self.toast.show("No solution contains your queens", Theme.DANGER)

    def run_min_conflicts(self, heuristic: bool) -> None:
        selector = MaxConflictTabuSelector() if heuristic else RandomConflictedSelector()
        solver = MinConflictsSolver(selector, seed=self.rng.randrange(10 ** 6))
        if not self.animate:
            self._stop_animation()
            result = solver.solve(self.n)
            self.board = QueenBoard.from_columns(result.columns)
            self.result_lines = [solver.name, f"{'solved' if result.solved else 'not solved'} in "
                                              f"{result.steps} steps, {result.elapsed * 1000:.2f} ms"]
            return
        self.anim_solver = solver
        self.animation = solver.iter_steps(self.n)
        self.anim_timer = 0.0
        self.last_step = None
        self.result_lines = [solver.name, "Starting from a random complete assignment..."]

    def _advance_animation(self) -> None:
        try:
            step = next(self.animation)
        except StopIteration:
            pairs = self.anim_solver.board.attacking_pairs()
            steps = self.last_step.step if self.last_step else 0
            self.result_lines = [self.anim_solver.name,
                                 f"{'Solved' if pairs == 0 else 'Stopped (max steps)'} after {steps} steps"]
            self.animation = None
            return
        self.last_step = step
        self.board = QueenBoard.from_columns(self.anim_solver.board.columns)
        self.result_lines = [self.anim_solver.name, f"step {step.step}: row {step.row} moved "
                                                    f"col {step.old_col} -> {step.new_col}",
                             f"attacking pairs left: {step.attacking_pairs}"]

    # ------------------------------------------------------------------ loop
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.size_selector.handle_event(event):
            return
        for button in self.buttons:
            if button.handle_event(event):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._cell_at(event.pos)
            if cell is not None:
                self._stop_animation()
                self.board.toggle(*cell)

    def update(self, dt: float) -> None:
        self.toast.update(dt)
        for button in self.buttons:
            button.update(dt)
        if self.animation is not None:
            self.anim_timer += dt
            interval = 0.18 if self.n <= 10 else 0.08
            while self.animation is not None and self.anim_timer >= interval:
                self.anim_timer -= interval
                self._advance_animation()

    def draw(self, surface: pygame.Surface) -> None:
        draw_text(surface, "N-QUEENS", (30, 18), 30, Theme.TEXT, bold=True)
        draw_text(surface, "Propositional logic (CNF + Glucose3)  &  Min-Conflicts local search",
                  (200, 30), 16, Theme.TEXT_MUTED)
        self._draw_board(surface)
        self._draw_side_panel(surface)
        self.toast.draw(surface)

    def _draw_board(self, surface: pygame.Surface) -> None:
        hover = self._cell_at(pygame.mouse.get_pos())
        conflicts = self.board.attacking_pairs()
        conflicted = {q for pair in conflicts for q in pair}
        for row in range(self.n):
            for col in range(self.n):
                rect = self._cell_rect(row, col)
                pygame.draw.rect(surface, LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE, rect)
                if hover and (row == hover[0] or col == hover[1] or abs(row - hover[0]) == abs(col - hover[1])):
                    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                    shade.fill((92, 166, 255, 38))
                    surface.blit(shade, rect)
        if self.last_step is not None:
            pygame.draw.rect(surface, Theme.ACCENT, self._cell_rect(self.last_step.row, self.last_step.new_col), 3)
        for a, b in conflicts:
            pygame.draw.line(surface, CONFLICT_COLOR, self._cell_rect(*a).center, self._cell_rect(*b).center, 2)
        for queen in self.board.queens:
            self._draw_queen(surface, self._cell_rect(*queen), CONFLICT_COLOR if queen in conflicted else QUEEN_COLOR)
        pygame.draw.rect(surface, Theme.BORDER, pygame.Rect(self.board_area.topleft, (self.cell * self.n,) * 2), 2)

    @staticmethod
    def _draw_queen(surface: pygame.Surface, rect: pygame.Rect, color) -> None:
        """Simple crown made of one polygon and a base bar."""
        w, h = rect.width, rect.height
        x0, y0 = rect.x + w * 0.2, rect.y + h * 0.25
        points = [(x0, y0 + h * 0.45), (x0, y0 + h * 0.05), (x0 + w * 0.15, y0 + h * 0.25),
                  (x0 + w * 0.3, y0), (x0 + w * 0.45, y0 + h * 0.25), (x0 + w * 0.6, y0 + h * 0.05),
                  (x0 + w * 0.6, y0 + h * 0.45)]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.rect(surface, color, pygame.Rect(x0, y0 + h * 0.48, w * 0.6, h * 0.1), border_radius=2)
        for px, py in (points[1], points[3], points[5]):
            pygame.draw.circle(surface, color, (px, py), max(2, w * 0.05))

    def _draw_side_panel(self, surface: pygame.Surface) -> None:
        inner = draw_panel(surface, pygame.Rect(730, 70, 440, 190), "BOARD")
        self.size_selector.draw(surface)
        pairs = len(self.board.attacking_pairs())
        draw_text(surface, f"Queens placed: {len(self.board.queens)} / {self.n}", (inner.x, inner.y + 88), 16)
        draw_text(surface, f"Attacking pairs: {pairs}", (inner.x, inner.y + 112), 16,
                  CONFLICT_COLOR if pairs else Theme.TEXT)
        if self.board.is_solution():
            draw_text(surface, "SOLVED", (inner.right, inner.y + 96), 26, Theme.SUCCESS, bold=True,
                      anchor="topright")

        draw_panel(surface, pygame.Rect(730, 272, 440, 244), "SOLVERS  (keys 1-4)")
        result_inner = draw_panel(surface, pygame.Rect(730, 528, 440, 156), "RESULT")
        for i, line in enumerate(self.result_lines[:6]):
            draw_text(surface, line, (result_inner.x, result_inner.y + i * 19), 14, Theme.TEXT_MUTED)
        for button in self.buttons:
            button.draw(surface)
