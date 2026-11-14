"""Modern Dark-Theme GUI Visualizer for N-Queens Problem.
Supports Glucose3 SAT and Min-Conflicts local search with live conflict rays,
step-by-step animation, and coordinate borders.
"""
from __future__ import annotations

import string
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional, Set, Tuple

import numpy as np

from nqueens.board import Board
from nqueens.min_conflicts import (
    ConflictState,
    MaxConflictSelector,
    RandomConflictedSelector,
)

try:
    from nqueens.sat_solver import GlucoseQueenSolver
    HAS_PYSAT = True
except ImportError:
    HAS_PYSAT = False


# Theme Palette (Cyber Slate & Royal Gold)
PALETTE = {
    "bg_main": "#0F172A",       # Deep slate blue
    "bg_card": "#1E293B",       # Card background
    "bg_card_inner": "#0B1120", # Input inner bg
    "border": "#334155",        # Slate border
    "text_primary": "#F8FAFC",  # Bright white
    "text_muted": "#94A3B8",    # Muted gray
    "accent_blue": "#38BDF8",   # Sky blue
    "accent_emerald": "#10B981",# Emerald green (success)
    "accent_coral": "#F43F5E",  # Coral red (conflict)
    "accent_gold": "#F59E0B",   # Royal gold (queens)
    "sq_light": "#CBD5E1",      # Board light square
    "sq_dark": "#475569",       # Board dark square
    "sq_conflict": "#7F1D1D",   # Highlight attacked square
    "sq_safe": "#064E3B",       # Highlight solved square
}


class ModernCard(tk.Frame):
    """Sleek styled card container with rounded aesthetic."""
    def __init__(self, parent, title: str = "", **kwargs):
        super().__init__(parent, bg=PALETTE["bg_card"], bd=1, relief=tk.SOLID,
                         highlightbackground=PALETTE["border"], highlightthickness=1, **kwargs)
        if title:
            lbl = tk.Label(self, text=title, font=("Segoe UI", 10, "bold"),
                           fg=PALETTE["accent_blue"], bg=PALETTE["bg_card"])
            lbl.pack(anchor=tk.W, padx=12, pady=(10, 4))


class NQueensGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("N-Queens AI Studio - Solver & Visualizer")
        self.root.geometry("1060x780")
        self.root.minsize(920, 680)
        self.root.configure(bg=PALETTE["bg_main"])

        self.n = 8
        self.queens: List[int] = list(range(self.n))  # queens[col] = row
        self.conflicted_cols: Set[int] = set()
        self.attacking_pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        
        self.is_running = False
        self.stop_requested = False

        self._setup_layout()
        self._refresh_conflict_analysis()
        self.draw_board()

    def _setup_layout(self):
        # 1. Header Bar
        header = tk.Frame(self.root, bg=PALETTE["bg_card"], height=56, padx=20)
        header.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(header, text="♛ N-QUEENS AI VISUALIZER", font=("Segoe UI", 14, "bold"),
                             fg=PALETTE["text_primary"], bg=PALETTE["bg_card"])
        title_lbl.pack(side=tk.LEFT, pady=12)

        sub_lbl = tk.Label(header, text="Propositional SAT (Glucose3) & Heuristic Local Search",
                           font=("Segoe UI", 10), fg=PALETTE["text_muted"], bg=PALETTE["bg_card"])
        sub_lbl.pack(side=tk.LEFT, padx=15, pady=12)

        # 2. Main Container
        main_box = tk.Frame(self.root, bg=PALETTE["bg_main"], padx=15, pady=15)
        main_box.pack(fill=tk.BOTH, expand=True)

        # Left Panel (Controls)
        left_panel = tk.Frame(main_box, bg=PALETTE["bg_main"], width=340)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_panel.pack_propagate(False)

        # Right Panel (Board Canvas)
        right_panel = ModernCard(main_box, title="Interactive Chessboard")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(right_panel, bg=PALETTE["bg_card_inner"], bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda e: self.draw_board())

        # Populate Left Controls
        self._build_settings_card(left_panel)
        self._build_solver_card(left_panel)
        self._build_actions_card(left_panel)
        self._build_stats_card(left_panel)

    def _build_settings_card(self, parent):
        card = ModernCard(parent, title="1. BOARD CONFIGURATION")
        card.pack(fill=tk.X, pady=(0, 10))

        row1 = tk.Frame(card, bg=PALETTE["bg_card"])
        row1.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(row1, text="Size (N):", font=("Segoe UI", 10), fg=PALETTE["text_primary"],
                 bg=PALETTE["bg_card"]).pack(side=tk.LEFT)

        self.n_var = tk.IntVar(value=8)
        self.n_entry = tk.Spinbox(row1, from_=4, to=64, textvariable=self.n_var, width=6,
                                  font=("Segoe UI", 10, "bold"), bg=PALETTE["bg_card_inner"],
                                  fg=PALETTE["text_primary"], buttonbackground=PALETTE["border"],
                                  bd=1, relief=tk.SOLID)
        self.n_entry.pack(side=tk.LEFT, padx=10)

        btn_apply = tk.Button(row1, text="Apply", command=self.on_set_n, bg=PALETTE["accent_blue"],
                              fg="#000000", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=2, cursor="hand2")
        btn_apply.pack(side=tk.LEFT)

        # Preset Buttons
        preset_row = tk.Frame(card, bg=PALETTE["bg_card"])
        preset_row.pack(fill=tk.X, padx=12, pady=(6, 12))
        tk.Label(preset_row, text="Quick N:", font=("Segoe UI", 8), fg=PALETTE["text_muted"],
                 bg=PALETTE["bg_card"]).pack(side=tk.LEFT, padx=(0, 5))
        for preset_n in (4, 8, 12, 16, 24, 32):
            b = tk.Button(preset_row, text=str(preset_n), font=("Segoe UI", 8),
                          bg=PALETTE["border"], fg=PALETTE["text_primary"], bd=0, padx=5,
                          command=lambda val=preset_n: self.set_preset_n(val), cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)

    def _build_solver_card(self, parent):
        card = ModernCard(parent, title="2. ALGORITHM & VISUALS")
        card.pack(fill=tk.X, pady=(0, 10))

        self.algo_var = tk.StringVar(value="max_conflict")
        radios = [
            ("★ Proposed (Max-Conflict + Tabu)", "max_conflict"),
            ("Standard Min-Conflicts (Random)", "standard"),
        ]
        if HAS_PYSAT:
            radios.append(("Propositional SAT (Glucose3)", "glucose"))

        for text, val in radios:
            rb = tk.Radiobutton(card, text=text, variable=self.algo_var, value=val,
                                font=("Segoe UI", 9), fg=PALETTE["text_primary"], bg=PALETTE["bg_card"],
                                selectcolor=PALETTE["bg_card_inner"], activebackground=PALETTE["bg_card"],
                                activeforeground=PALETTE["accent_blue"])
            rb.pack(anchor=tk.W, padx=12, pady=2)

        # Visual Toggles
        sep = tk.Frame(card, height=1, bg=PALETTE["border"])
        sep.pack(fill=tk.X, padx=12, pady=8)

        self.animate_var = tk.BooleanVar(value=True)
        cb1 = tk.Checkbutton(card, text="Enable Step Animation", variable=self.animate_var,
                             font=("Segoe UI", 9), fg=PALETTE["text_primary"], bg=PALETTE["bg_card"],
                             selectcolor=PALETTE["bg_card_inner"], activebackground=PALETTE["bg_card"])
        cb1.pack(anchor=tk.W, padx=12, pady=2)

        self.rays_var = tk.BooleanVar(value=True)
        cb2 = tk.Checkbutton(card, text="Draw Conflict Attack Rays", variable=self.rays_var,
                             font=("Segoe UI", 9), fg=PALETTE["text_primary"], bg=PALETTE["bg_card"],
                             selectcolor=PALETTE["bg_card_inner"], activebackground=PALETTE["bg_card"],
                             command=self.draw_board)
        cb2.pack(anchor=tk.W, padx=12, pady=2)

        # Speed slider
        slider_row = tk.Frame(card, bg=PALETTE["bg_card"])
        slider_row.pack(fill=tk.X, padx=12, pady=(6, 12))
        tk.Label(slider_row, text="Delay:", font=("Segoe UI", 9), fg=PALETTE["text_muted"],
                 bg=PALETTE["bg_card"]).pack(side=tk.LEFT)
        self.speed_slider = tk.Scale(slider_row, from_=0, to=150, orient=tk.HORIZONTAL,
                                     bg=PALETTE["bg_card"], fg=PALETTE["text_muted"],
                                     highlightthickness=0, troughcolor=PALETTE["bg_card_inner"],
                                     activebackground=PALETTE["accent_blue"])
        self.speed_slider.set(20)
        self.speed_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

    def _build_actions_card(self, parent):
        card = tk.Frame(parent, bg=PALETTE["bg_main"])
        card.pack(fill=tk.X, pady=(0, 10))

        self.btn_solve = tk.Button(card, text="▶ START SOLVER", font=("Segoe UI", 11, "bold"),
                                   bg=PALETTE["accent_emerald"], fg="#000000", bd=0, pady=8,
                                   cursor="hand2", command=self.start_solve)
        self.btn_solve.pack(fill=tk.X, pady=3)

        btn_row = tk.Frame(card, bg=PALETTE["bg_main"])
        btn_row.pack(fill=tk.X, pady=2)

        self.btn_stop = tk.Button(btn_row, text="■ Stop", font=("Segoe UI", 9, "bold"),
                                  bg=PALETTE["accent_coral"], fg="#FFFFFF", bd=0, pady=6,
                                  cursor="hand2", command=self.stop_solve, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.btn_reset = tk.Button(btn_row, text="🔄 Randomize", font=("Segoe UI", 9, "bold"),
                                   bg=PALETTE["border"], fg=PALETTE["text_primary"], bd=0, pady=6,
                                   cursor="hand2", command=self.randomize_board)
        self.btn_reset.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

    def _build_stats_card(self, parent):
        card = ModernCard(parent, title="3. TELEMETRY & RESULTS")
        card.pack(fill=tk.BOTH, expand=True)

        def make_stat_row(label_text: str):
            row = tk.Frame(card, bg=PALETTE["bg_card"])
            row.pack(fill=tk.X, padx=12, pady=3)
            tk.Label(row, text=label_text, font=("Segoe UI", 9), fg=PALETTE["text_muted"],
                     bg=PALETTE["bg_card"]).pack(side=tk.LEFT)
            val = tk.Label(row, text="-", font=("Segoe UI", 9, "bold"), fg=PALETTE["text_primary"],
                           bg=PALETTE["bg_card"])
            val.pack(side=tk.RIGHT)
            return val

        self.lbl_status = make_stat_row("Status:")
        self.lbl_time = make_stat_row("Time Elapsed:")
        self.lbl_metric = make_stat_row("Steps / Clauses:")
        self.lbl_conflicts = make_stat_row("Attacking Pairs:")
        self.lbl_valid = make_stat_row("Solution Validity:")

        self.lbl_status.config(text="Idle / Ready", fg=PALETTE["accent_blue"])

    def set_preset_n(self, val: int):
        self.n_var.set(val)
        self.on_set_n()

    def on_set_n(self):
        if self.is_running:
            return
        try:
            val = int(self.n_var.get())
            if not (4 <= val <= 64):
                messagebox.showerror("Error", "Please pick N between 4 and 64 for optimal visualization.")
                return
            self.n = val
            self.randomize_board()
        except ValueError:
            messagebox.showerror("Error", "Please input an integer for N.")

    def randomize_board(self):
        rng = np.random.default_rng()
        self.queens = list(rng.integers(0, self.n, size=self.n))
        self._refresh_conflict_analysis()
        self.lbl_status.config(text="Random Initial State", fg=PALETTE["accent_blue"])
        self.lbl_time.config(text="-", fg=PALETTE["text_primary"])
        self.lbl_metric.config(text="-", fg=PALETTE["text_primary"])
        self.draw_board()

    def _refresh_conflict_analysis(self):
        """Analyzes all pairs of attacking queens to draw conflict rays and compute pairs."""
        n = self.n
        self.conflicted_cols.clear()
        self.attacking_pairs.clear()

        cells = [(self.queens[c], c) for c in range(n) if self.queens[c] is not None]
        for i in range(len(cells)):
            r1, c1 = cells[i]
            for j in range(i + 1, len(cells)):
                r2, c2 = cells[j]
                if r1 == r2 or abs(r1 - r2) == abs(c1 - c2):
                    self.conflicted_cols.add(c1)
                    self.conflicted_cols.add(c2)
                    self.attacking_pairs.append(((r1, c1), (r2, c2)))

        count = len(self.attacking_pairs)
        if count == 0:
            self.lbl_conflicts.config(text="0 (Clean)", fg=PALETTE["accent_emerald"])
            self.lbl_valid.config(text="✔ VALID (Non-attacking)", fg=PALETTE["accent_emerald"])
        else:
            self.lbl_conflicts.config(text=f"{count} pairs", fg=PALETTE["accent_coral"])
            self.lbl_valid.config(text="✘ Invalid (Collisions)", fg=PALETTE["accent_coral"])

    def draw_board(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        margin = 32  # Margin for coordinates border
        board_size = min(w, h) - 2 * margin
        if board_size <= 0:
            return

        cell_size = board_size / self.n
        start_x = (w - board_size) // 2
        start_y = (h - board_size) // 2

        # 1. Coordinate Labels (Rank & File)
        font_coord = ("Segoe UI", max(8, int(cell_size * 0.22)), "bold")
        for i in range(self.n):
            cx = start_x + (i + 0.5) * cell_size
            col_char = string.ascii_uppercase[i] if i < 26 else f"{i}"
            # Top & Bottom File Labels
            self.canvas.create_text(cx, start_y - 12, text=col_char, font=font_coord, fill=PALETTE["text_muted"])
            self.canvas.create_text(cx, start_y + board_size + 12, text=col_char, font=font_coord, fill=PALETTE["text_muted"])

            cy = start_y + (i + 0.5) * cell_size
            row_char = str(self.n - i)
            # Left & Right Rank Labels
            self.canvas.create_text(start_x - 14, cy, text=row_char, font=font_coord, fill=PALETTE["text_muted"])
            self.canvas.create_text(start_x + board_size + 14, cy, text=row_char, font=font_coord, fill=PALETTE["text_muted"])

        # 2. Draw Squares
        for r in range(self.n):
            for c in range(self.n):
                x1 = start_x + c * cell_size
                y1 = start_y + r * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size

                # Square Color
                is_light = (r + c) % 2 == 0
                bg = PALETTE["sq_light"] if is_light else PALETTE["sq_dark"]

                # Conflict Background tint
                if c in self.conflicted_cols and self.queens[c] == r:
                    bg = PALETTE["sq_conflict"]
                elif len(self.conflicted_cols) == 0 and self.queens[c] == r:
                    bg = PALETTE["sq_safe"]

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg, outline="#1E293B", width=1)

        # 3. Draw Conflict Attack Rays (Optional)
        if self.rays_var.get() and self.attacking_pairs and self.n <= 32:
            for ((r1, c1), (r2, c2)) in self.attacking_pairs:
                x1 = start_x + (c1 + 0.5) * cell_size
                y1 = start_y + (r1 + 0.5) * cell_size
                x2 = start_x + (c2 + 0.5) * cell_size
                y2 = start_y + (r2 + 0.5) * cell_size
                self.canvas.create_line(x1, y1, x2, y2, fill=PALETTE["accent_coral"],
                                        width=2, dash=(4, 4))

        # 4. Draw Queens with Crown Symbol
        crown_size = max(11, int(cell_size * 0.70))
        for c in range(self.n):
            r = self.queens[c]
            if r is not None and 0 <= r < self.n:
                qx = start_x + (c + 0.5) * cell_size
                qy = start_y + (r + 0.5) * cell_size

                is_conflicted = c in self.conflicted_cols
                crown_color = PALETTE["accent_coral"] if is_conflicted else PALETTE["accent_gold"]

                # Subtle shadow
                self.canvas.create_text(qx + 1, qy + 1, text="♛", font=("Segoe UI Symbol", crown_size, "bold"),
                                        fill="#000000")
                # Main Crown
                self.canvas.create_text(qx, qy, text="♛", font=("Segoe UI Symbol", crown_size, "bold"),
                                        fill=crown_color)

    def start_solve(self):
        if self.is_running:
            return
        self.is_running = True
        self.stop_requested = False
        self.btn_solve.config(state=tk.DISABLED, bg=PALETTE["border"])
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_reset.config(state=tk.DISABLED)
        self.lbl_status.config(text="Solving in progress...", fg=PALETTE["accent_gold"])

        threading.Thread(target=self._solve_worker, daemon=True).start()

    def stop_solve(self):
        self.stop_requested = True
        self.lbl_status.config(text="Stopping...", fg=PALETTE["accent_coral"])

    def _solve_worker(self):
        algo = self.algo_var.get()
        n = self.n
        t0 = time.perf_counter()

        # Mode 1: Glucose3 SAT Solver
        if algo == "glucose":
            if not HAS_PYSAT:
                messagebox.showerror("PySAT Missing", "python-sat is not installed in current environment.")
                self._finish_ui(False, 0, 0, [], is_sat=True)
                return
            solver = GlucoseQueenSolver()
            res = solver.solve(n)
            elapsed = res.solve_time
            if res.satisfiable and res.board:
                col_queens = [0] * n
                for r, c in res.board.queens:
                    col_queens[c] = r
                self._finish_ui(True, elapsed, res.num_clauses, col_queens, is_sat=True)
            else:
                self._finish_ui(False, elapsed, res.num_clauses, [], is_sat=True)
            return

        # Mode 2: Min-Conflicts Local Search
        selector = MaxConflictSelector() if algo == "max_conflict" else RandomConflictedSelector()
        animate = self.animate_var.get()

        rng = np.random.default_rng()
        # Start from current board if already assigned, else random
        initial_q = np.array(self.queens) if len(self.queens) == n else rng.integers(0, n, size=n)
        state = ConflictState(n, initial_q)
        last_moved = None
        max_steps = 100_000
        solved = False
        step = 0

        for step in range(max_steps + 1):
            if self.stop_requested:
                break

            conflicts = state.all_conflicts()
            conflicted = np.flatnonzero(conflicts > 0)
            if conflicted.size == 0:
                solved = True
                break
            if step == max_steps:
                break

            col = selector.select(conflicts, conflicted, rng, last_moved)
            costs = state.row_costs(col)
            new_row = int(rng.choice(np.flatnonzero(costs == costs.min())))
            state.move(col, new_row)
            last_moved = col

            if animate and n <= 32:
                delay = self.speed_slider.get() / 1000.0
                self.queens = list(state.queens)
                # Thread-safe UI update
                self.root.after(0, self._step_refresh, step)
                if delay > 0:
                    time.sleep(delay)

        elapsed = time.perf_counter() - t0
        self._finish_ui(solved, elapsed, step, list(state.queens), is_sat=False)

    def _step_refresh(self, step: int):
        self._refresh_conflict_analysis()
        self.lbl_metric.config(text=f"Step #{step:,}", fg=PALETTE["text_primary"])
        self.draw_board()

    def _finish_ui(self, solved: bool, elapsed: float, metric: int, final_q: List[int], is_sat: bool):
        def update():
            self.is_running = False
            self.stop_requested = False
            self.btn_solve.config(state=tk.NORMAL, bg=PALETTE["accent_emerald"])
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_reset.config(state=tk.NORMAL)

            if solved and final_q:
                self.queens = final_q
                self._refresh_conflict_analysis()
                self.draw_board()
                self.lbl_status.config(text="✔ SOLVED SUCCESSFULLY!", fg=PALETTE["accent_emerald"])
            else:
                self._refresh_conflict_analysis()
                self.draw_board()
                msg = "Stopped" if self.stop_requested else "Failed / Limit reached"
                self.lbl_status.config(text=msg, fg=PALETTE["accent_coral"])

            self.lbl_time.config(text=f"{elapsed:.4f} seconds", fg=PALETTE["accent_blue"])
            metric_title = "Clauses" if is_sat else "Steps"
            self.lbl_metric.config(text=f"{metric:,} ({metric_title})", fg=PALETTE["text_primary"])

        self.root.after(0, update)


def main():
    root = tk.Tk()
    # High DPI scaling for ultra-sharp crisp rendering
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = NQueensGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()