"""
Kakuro UI with two modes.
- Visualize: run the solver, then replay every step: domains (small candidate digits), the run being
  propagated (blue outline), removed values (red), assignments (green) and backtracks (red cell).
- Play yourself: type digits into cells, check your board or ask for a hint.
"""
from __future__ import annotations

from typing import Dict, Optional, Set

import pygame

from common.app_base import BaseApp
from common.theme import Theme
from common.widgets import Button, OptionSelector, Toast, draw_panel, draw_text, wrap_text
from task3_kakuro.core.csp_model import KakuroCSP, Variable
from task3_kakuro.core.puzzle import CellKind, PuzzleLoader
from task3_kakuro.solvers.backtracking import BacktrackingSolver, SolverConfig
from task3_kakuro.solvers.trace import SolverTrace, TraceEvent

INFERENCE_OPTIONS = {"MAC (GAC-3)": "mac", "Forward checking": "fc", "None": "none"}
ORDER_OPTIONS = {"MRV + Degree": (True, True), "MRV": (True, False), "Static": (False, False)}
SPEEDS = {"1x": 0.45, "2x": 0.22, "4x": 0.1, "10x": 0.04, "Max": 0.005}
EVENT_COLORS = {"start": Theme.TEXT_MUTED, "preprocess": Theme.PURPLE, "revise": Theme.ACCENT,
                "assign": Theme.SUCCESS, "backtrack": Theme.DANGER, "wipeout": Theme.WARNING,
                "solution": Theme.GOLD, "fail": Theme.DANGER}
WHITE_CELL = (222, 227, 238)
BLOCK_CELL = (42, 47, 62)
UI_NODE_LIMIT = 20_000


class KakuroApp(BaseApp):
    TITLE = "Kakuro - Constraint Satisfaction"

    def __init__(self, screen: Optional[pygame.Surface] = None):
        super().__init__(screen)
        self.toast = Toast()
        self.board_area = pygame.Rect(30, 70, 670, 670)
        names = PuzzleLoader.available()
        self.puzzle_selector = OptionSelector((750, 108, 190, 58), "Puzzle", names,
                                              names.index("basic_5x5") if "basic_5x5" in names else 0,
                                              lambda _: self.load_puzzle())
        self.mode_selector = OptionSelector((960, 108, 190, 58), "Mode", ["Visualize", "Play yourself"], 0,
                                            lambda _: self._on_mode_change())
        self.inference_selector = OptionSelector((750, 176, 190, 58), "Inference", list(INFERENCE_OPTIONS))
        self.order_selector = OptionSelector((960, 176, 190, 58), "Variable order", list(ORDER_OPTIONS))
        self.value_selector = OptionSelector((750, 244, 190, 58), "Value order", ["LCV", "Ascending"])
        self.preprocess_selector = OptionSelector((960, 244, 190, 58), "Initial GAC", ["ON", "OFF"])
        self.speed_selector = OptionSelector((750, 476, 190, 58), "Playback speed", list(SPEEDS), 1)
        self.selectors = [self.puzzle_selector, self.mode_selector, self.inference_selector, self.order_selector,
                          self.value_selector, self.preprocess_selector, self.speed_selector]

        self.solve_button = Button((750, 316, 400, 44), "Solve & visualize  (S)", self.run_solver, "primary",
                                   pygame.K_s)
        self.play_button = Button((860, 420, 70, 40), "Play", self.toggle_play, "primary", pygame.K_SPACE, 15)
        self.visual_buttons = [
            self.solve_button,
            Button((750, 420, 50, 40), "|<", lambda: self.seek(0), "ghost", pygame.K_HOME, 15),
            Button((805, 420, 50, 40), "<", lambda: self.seek(self.index - 1), "ghost", pygame.K_LEFT, 15),
            self.play_button,
            Button((935, 420, 50, 40), ">", lambda: self.seek(self.index + 1), "ghost", pygame.K_RIGHT, 15),
            Button((990, 420, 50, 40), ">|", lambda: self.seek(len(self.events) - 1), "ghost", pygame.K_END, 15),
        ]
        self.play_buttons = [
            Button((750, 316, 128, 44), "Check (C)", self.check_board, "primary", pygame.K_c, 15),
            Button((886, 316, 128, 44), "Hint (H)", self.give_hint, "success", pygame.K_h, 15),
            Button((1022, 316, 128, 44), "Clear", self.clear_entries, "ghost", None, 15),
        ]
        self.back_button = Button((1010, 696, 140, 44), "Back (Esc)", self.close, "ghost")
        self.timeline = pygame.Rect(960, 510, 190, 10)
        self.load_puzzle()

    # ------------------------------------------------------------------ setup
    def load_puzzle(self) -> None:
        self.puzzle = PuzzleLoader.load(self.puzzle_selector.value)
        self.csp = KakuroCSP(self.puzzle)
        self.cell = min(self.board_area.width // self.puzzle.cols, self.board_area.height // self.puzzle.rows, 110)
        self.events = [TraceEvent("start", "Press 'Solve & visualize' to run the solver.", 0,
                                  dict(self.csp.domains), {})]
        self.index = 0
        self.playing = False
        self.play_timer = 0.0
        self.stats = None
        self.entries: Dict[Variable, int] = {}
        self.wrong: Set[Variable] = set()
        self.selected: Optional[Variable] = None
        self._solution: Optional[Dict[Variable, int]] = None

    def _on_mode_change(self) -> None:
        self.playing = False
        self.wrong.clear()

    @property
    def play_mode(self) -> bool:
        return self.mode_selector.index == 1

    def current_config(self) -> SolverConfig:
        mrv, degree = ORDER_OPTIONS[self.order_selector.value]
        return SolverConfig(INFERENCE_OPTIONS[self.inference_selector.value], mrv, degree,
                            self.value_selector.value == "LCV", self.preprocess_selector.value == "ON")

    # ------------------------------------------------------------------ visualize mode
    def run_solver(self) -> None:
        trace = SolverTrace()
        self.stats = BacktrackingSolver(self.current_config(), UI_NODE_LIMIT).solve(self.csp, trace)
        self.events = trace.events
        self.index = 0
        self.playing = True
        verdict = "solved" if self.stats.solved else "not solved"
        self.toast.show(f"{verdict}: {len(self.events)} steps recorded", Theme.SUCCESS if self.stats.solved
                        else Theme.DANGER)

    def toggle_play(self) -> None:
        if self.index >= len(self.events) - 1:
            self.index = 0
        self.playing = not self.playing

    def seek(self, index: int) -> None:
        self.index = max(0, min(len(self.events) - 1, index))
        self.playing = False

    # ------------------------------------------------------------------ play mode
    def solution(self) -> Optional[Dict[Variable, int]]:
        if self._solution is None:
            self._solution = BacktrackingSolver().solve(self.csp).solution
        return self._solution

    def check_board(self) -> None:
        """A cell is wrong if one of its runs repeats a digit or (when full) misses the clue sum."""
        self.wrong = set()
        for constraint in self.csp.constraints:
            values = [self.entries[c] for c in constraint.cells if c in self.entries]
            full = len(values) == len(constraint.cells)
            if len(values) != len(set(values)) or (full and sum(values) != constraint.total) or \
                    (not full and sum(values) >= constraint.total):
                self.wrong.update(c for c in constraint.cells if c in self.entries)
        if self.csp.is_solution(self.entries):
            self.toast.show("Congratulations - the board is solved!", Theme.SUCCESS, 3)
        elif self.wrong:
            self.toast.show(f"{len(self.wrong)} cell(s) break a rule", Theme.DANGER)
        else:
            self.toast.show("No rule broken so far", Theme.ACCENT)

    def give_hint(self) -> None:
        solution = self.solution()
        if not solution:
            return
        missing = [v for v in self.csp.variables if self.entries.get(v) != solution[v]]
        if not missing:
            self.toast.show("Board already complete", Theme.SUCCESS)
            return
        target = self.selected if self.selected in missing else missing[0]
        self.entries[target] = solution[target]
        self.wrong.clear()
        self.toast.show(f"Hint: {target} = {solution[target]}", Theme.SUCCESS)

    def clear_entries(self) -> None:
        self.entries.clear()
        self.wrong.clear()

    # ------------------------------------------------------------------ events
    def _cell_at(self, pos) -> Optional[Variable]:
        x, y = pos[0] - self.board_area.x, pos[1] - self.board_area.y
        if x < 0 or y < 0:
            return None
        row, col = y // self.cell, x // self.cell
        return (row, col) if self.puzzle.is_white(row, col) else None

    def handle_event(self, event: pygame.event.Event) -> None:
        for selector in self.selectors:
            if selector.handle_event(event):
                return
        buttons = self.play_buttons if self.play_mode else self.visual_buttons
        for button in buttons + [self.back_button]:
            if button.handle_event(event):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.play_mode and self.timeline.inflate(0, 16).collidepoint(event.pos):
                ratio = (event.pos[0] - self.timeline.x) / self.timeline.width
                self.seek(round(ratio * (len(self.events) - 1)))
            elif self.play_mode:
                self.selected = self._cell_at(event.pos)
        if event.type == pygame.KEYDOWN and self.play_mode and self.selected is not None:
            if pygame.K_1 <= event.key <= pygame.K_9:
                self.entries[self.selected] = event.key - pygame.K_0
                self.wrong.discard(self.selected)
            elif pygame.K_KP1 <= event.key <= pygame.K_KP9:
                self.entries[self.selected] = event.key - pygame.K_KP1 + 1
            elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_0):
                self.entries.pop(self.selected, None)

    def update(self, dt: float) -> None:
        self.toast.update(dt)
        for button in self.visual_buttons + self.play_buttons + [self.back_button]:
            button.update(dt)
        self.play_button.label = "Pause" if self.playing else "Play"
        if self.playing and not self.play_mode:
            self.play_timer += dt
            interval = SPEEDS[self.speed_selector.value]
            while self.play_timer >= interval and self.playing:
                self.play_timer -= interval
                if self.index < len(self.events) - 1:
                    self.index += 1
                else:
                    self.playing = False

    # ------------------------------------------------------------------ drawing
    def draw(self, surface: pygame.Surface) -> None:
        draw_text(surface, "KAKURO", (30, 18), 30, Theme.TEXT, bold=True)
        draw_text(surface, "CSP: variables = white cells, domain = 1..9, constraints = sum + all-different per run",
                  (160, 30), 15, Theme.TEXT_MUTED)
        event = self.events[self.index]
        self._draw_board(surface, event)
        self._draw_panel(surface, event)
        self.toast.draw(surface)

    def _cell_rect(self, row: int, col: int) -> pygame.Rect:
        return pygame.Rect(self.board_area.x + col * self.cell, self.board_area.y + row * self.cell,
                           self.cell, self.cell)

    def _draw_board(self, surface: pygame.Surface, event: TraceEvent) -> None:
        highlight = set()
        if not self.play_mode and event.constraint is not None:
            constraint = self.csp.constraints[event.constraint]
            highlight = set(constraint.cells) | {constraint.clue}
        for line in self.puzzle.grid:
            for cell in line:
                rect = self._cell_rect(cell.row, cell.col)
                if cell.kind is CellKind.BLOCK:
                    self._draw_block(surface, rect, cell, (cell.row, cell.col) in highlight)
                else:
                    self._draw_white(surface, rect, (cell.row, cell.col), event)
        for row, col in highlight:
            pygame.draw.rect(surface, Theme.ACCENT, self._cell_rect(row, col), 3)
        if self.play_mode and self.selected:
            pygame.draw.rect(surface, Theme.GOLD, self._cell_rect(*self.selected), 4)

    def _draw_block(self, surface: pygame.Surface, rect: pygame.Rect, cell, highlighted: bool) -> None:
        pygame.draw.rect(surface, (52, 62, 92) if highlighted else BLOCK_CELL, rect)
        pygame.draw.rect(surface, (24, 27, 36), rect, 1)
        if cell.down is None and cell.right is None:
            return
        pygame.draw.line(surface, (110, 118, 140), rect.topleft, rect.bottomright, 2)
        size = max(12, self.cell // 4)
        if cell.down is not None:
            draw_text(surface, str(cell.down), (rect.x + 6, rect.bottom - 4), size, Theme.TEXT, True, "bottomleft")
        if cell.right is not None:
            draw_text(surface, str(cell.right), (rect.right - 6, rect.y + 4), size, Theme.TEXT, True, "topright")

    def _draw_white(self, surface: pygame.Surface, rect: pygame.Rect, var: Variable, event: TraceEvent) -> None:
        background = WHITE_CELL
        if not self.play_mode and var == event.variable:
            background = (170, 230, 190) if event.kind == "assign" else (246, 170, 170)
        if self.play_mode and var in self.wrong:
            background = (246, 190, 190)
        pygame.draw.rect(surface, background, rect)
        pygame.draw.rect(surface, (150, 156, 172), rect, 1)

        if self.play_mode:
            if var in self.entries:
                color = (200, 40, 40) if var in self.wrong else (34, 60, 130)
                draw_text(surface, str(self.entries[var]), rect.center, int(self.cell * 0.55), color, True, "center")
            return

        if var in event.assignment:
            draw_text(surface, str(event.assignment[var]), rect.center, int(self.cell * 0.55), (34, 60, 130),
                      True, "center")
            return
        domain = event.domains.get(var, frozenset())
        removed = event.removed.get(var, frozenset()) if event.removed else frozenset()
        mini = self.cell / 3
        size = max(10, int(mini * 0.62))
        for digit in range(1, 10):
            if digit not in domain and digit not in removed:
                continue
            cx = rect.x + mini * ((digit - 1) % 3) + mini / 2
            cy = rect.y + mini * ((digit - 1) // 3) + mini / 2
            color = (220, 50, 50) if digit in removed else ((30, 140, 70) if len(domain) == 1 else (70, 76, 92))
            draw_text(surface, str(digit), (cx, cy), size, color, digit in removed, "center")

    def _draw_panel(self, surface: pygame.Surface, event: TraceEvent) -> None:
        draw_panel(surface, pygame.Rect(730, 70, 440, 300), "PUZZLE & SOLVER")
        for selector in self.selectors[:6]:
            selector.draw(surface)
        if self.play_mode:
            for button in self.play_buttons:
                button.draw(surface)
            inner = draw_panel(surface, pygame.Rect(730, 384, 440, 300), "HOW TO PLAY")
            lines = ["Click a white cell, then type 1-9.", "Backspace / 0 clears a cell.",
                     "Each run must sum to its clue and", "contain no repeated digit.",
                     f"Filled: {len(self.entries)} / {len(self.csp.variables)} cells"]
            for i, line in enumerate(lines):
                draw_text(surface, line, (inner.x, inner.y + i * 24), 16, Theme.TEXT_MUTED)
        else:
            self.solve_button.draw(surface)
            draw_panel(surface, pygame.Rect(730, 384, 440, 158), "PLAYBACK  (Space, arrows, Home/End)")
            for button in self.visual_buttons[1:]:
                button.draw(surface)
            self.speed_selector.draw(surface)
            draw_text(surface, f"Step {self.index + 1} / {len(self.events)}", (960, 484), 14, Theme.TEXT_MUTED)
            pygame.draw.rect(surface, Theme.SURFACE_LIGHT, self.timeline, border_radius=5)
            ratio = self.index / max(1, len(self.events) - 1)
            pygame.draw.rect(surface, Theme.ACCENT, (self.timeline.x, self.timeline.y,
                                                     int(self.timeline.width * ratio), 10), border_radius=5)
            inner = draw_panel(surface, pygame.Rect(730, 552, 440, 136), "CURRENT STEP")
            color = EVENT_COLORS.get(event.kind, Theme.TEXT)
            draw_text(surface, event.kind.upper(), (inner.x, inner.y), 15, color, bold=True)
            draw_text(surface, f"depth {event.depth}", (inner.right, inner.y), 14, Theme.TEXT_MUTED,
                      anchor="topright")
            for i, line in enumerate(wrap_text(event.message, 14, inner.width)[:3]):
                draw_text(surface, line, (inner.x, inner.y + 22 + i * 18), 14, Theme.TEXT)
            if self.stats:
                draw_text(surface, f"assignments {self.stats.assignments}  backtracks {self.stats.backtracks}  "
                                   f"pruned {self.stats.pruned_values}  {self.stats.elapsed * 1000:.1f} ms",
                          (inner.x, inner.bottom - 16), 13, Theme.TEXT_MUTED)
        self.back_button.draw(surface)
