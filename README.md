# AI Final Project — Group N04

Final project for **503043 – Introduction to Artificial Intelligence** (Ton Duc Thang University).
The repository contains three independent tasks, each in its own package, plus a shared PyGame launcher.

| # | Task | Topic | Owner |
|---|------|-------|-------|
| 1 | [N-Queens](task1_nqueens/) | Propositional Logic (CNF + Glucose3) & Local Search (Min-Conflicts) | Trinh Hai Huy |
| 2 | [Tank Battle](task2_tank_battle/) | Adversarial Search (Minimax, Alpha-Beta, Heuristic Minimax) | Phan Huy Binh |
| 3 | [Kakuro](task3_kakuro/) | Constraint Satisfaction (GAC-3 + Backtracking with MRV / Degree / LCV) | Tran Hong Nhat Duy |

---

## Table of contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Quick start](#quick-start)
4. [Task 1 — N-Queens](#task-1--n-queens)
5. [Task 2 — Tank Battle](#task-2--tank-battle)
6. [Task 3 — Kakuro](#task-3--kakuro)
7. [Project structure](#project-structure)
8. [Reproducing the experiments](#reproducing-the-experiments)

---

## Requirements

- **Python 3.10 or newer**
- Python packages listed in [`requirements.txt`](requirements.txt):

| Package | Used by | Purpose |
|---------|---------|---------|
| `pygame` ≥ 2.5 | all tasks | Graphical user interfaces |
| `python-sat` | Task 1 | Glucose3 SAT solver (PySAT) |
| `matplotlib` ≥ 3.7 | experiments | Plots in `results/` (optional — experiments still write CSV without it) |

The project was developed with Visual Studio Code and targets the evaluation configuration
macOS 13.7.8 (Ventura) on an Intel Core i5; it also runs on Windows and Linux.

## Installation

```bash
git clone https://github.com/JamesJoys-vie/AI_Final_Project.git
cd AI_Final_Project
```

Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

> If `pip` cannot find `python-sat`, install it explicitly with `pip install python-sat`.
> On Python versions without a pre-built wheel a C/C++ compiler is required
> (Xcode Command Line Tools on macOS: `xcode-select --install`).

## Quick start

All commands are run **from the repository root** (the folder that contains `main.py`).

```bash
python main.py
```

The launcher opens one window with a card for each task. Click a card or press `1`–`3`
to open a task; press `Esc` inside a task to return to the launcher.

Every task can also be started on its own:

```bash
python -m task1_nqueens
python -m task2_tank_battle
python -m task3_kakuro
```

---

## Task 1 — N-Queens

Place N queens on an N × N board so that no two queens attack each other.

### Approach

- **Propositional logic.** Each square `(r, c)` is a Boolean variable `Q(r,c)` (True = queen).
  Constraints are discovered by grouping squares into *lines* (rows, columns, diagonals `r − c = k`,
  anti-diagonals `r + c = k`) and are converted to CNF:
  - *at least one queen per row*: `Q(r,0) ∨ Q(r,1) ∨ … ∨ Q(r,N−1)`
  - *at most one queen per line*: `¬Q(a) ∨ ¬Q(b)` for every pair of squares on the same line.

  The clause count matches the closed form `N + N²(N−1) + N(N−1)(2N−1)/3`.

  Two optional variants of the encoding are compared in the experiments:
  - **Sequential counter** (`--amo=seqcounter`, Sinz 2005): "at most one" on a line of `k` squares with
    `k − 1` helper variables and `3k − 4` clauses instead of `k(k−1)/2`. Used only on lines where it is
    smaller (`k ≥ 6`), so the formula has O(N²) clauses instead of O(N³).
  - **Column ALO** (`--column-alo`): the redundant clauses *at least one queen per column*. They don't change
    the set of solutions but give Glucose3 much more unit propagation.
- **Glucose3** (PySAT) solves the CNF formula. Pre-placed queens are passed as SAT *assumptions*.
  The GUI and `sat N` use the plain pairwise encoding by default.
- **Min-Conflicts** works on the row-based CSP (one variable per row, value = column). Two
  variable-selection strategies are compared:
  - *Standard*: pick a conflicted row uniformly at random.
  - *Proposed heuristic*: pick the **most-conflicted** row (random tie-break) with a short **tabu list**
    of recently moved rows to avoid cycling on plateaus.

  Implementation details:
  - The board keeps per-line queen counts, each row's conflict count, the set of conflicted rows and
    the attacking-pair total up to date after every move. A move only touches the queens on the 6 lines
    it affects, so only scoring the N columns of the chosen row costs O(N).
  - **Initial assignment** (`init`): `random` (textbook, the default) or `greedy`. Greedy draws columns
    without repeats and gives each row the first of up to 20 random columns no placed queen attacks
    diagonally, so the search starts with only a few conflicts.
  - **Restarts**: if `50·N` repairs don't reach a solution, the search restarts from a new initial
    assignment (up to 10 times).
- Every solver result is checked by an independent O(N) checker (`is_valid_solution`).

### Usage

```bash
python -m task1_nqueens                                        # GUI
python -m task1_nqueens sat 8                                  # solve N = 8 with Glucose3 and print the board
python -m task1_nqueens sat 100 --amo=seqcounter --column-alo  # smaller CNF encoding
python -m task1_nqueens minconflicts 64                        # standard vs heuristic, random and greedy start
python -m task1_nqueens minconflicts 1000 --init=greedy        # greedy start only
python -m task1_nqueens benchmark --runs 20                    # full experiments (a few minutes)
```

Benchmark options: `--runs` (Min-Conflicts seeds), `--sat-max`, `--mc-max`, `--sat-repeats`
(SAT timings are medians), `--init random|greedy|both`, and
`--sat-encodings pairwise pairwise+alo seqcounter seqcounter+alo`.

### Tests

```bash
python -m unittest discover -s task1_nqueens/tests -t .
```

The tests cover:
- **Encodings:** every encoding has exactly the known number of solutions for N = 1…8.
- **Min-Conflicts:** the optimized search makes the same moves as a straightforward reference version for the same seeds.
- **Board and checker:** both agree with brute-force checks.

### GUI controls

| Key / action | Effect |
|--------------|--------|
| Click a square | Place / remove a queen (attacked squares are highlighted) |
| `1` | Solve with SAT (Glucose3) |
| `2` / `3` | Min-Conflicts — standard / proposed heuristic (animated) |
| `4` | Complete the current board with SAT (your queens are kept) |
| `R` / `C` | Random board / clear board |
| `Esc` | Back |

### Results

Stored in [`task1_nqueens/results/`](task1_nqueens/results/):
`sat_glucose3.csv` (variables, clauses, encode and solve time for N = 4…100),
`min_conflicts.csv` (success rate, steps and time for N = 8…1000, 20 seeds per configuration)
and `nqueens_experiments.png`.

---

## Task 2 — Tank Battle

A turn-based two-player tank game. Each player controls one tank and defends one base.

### Game rules

| Entity | Initial HP | Damage per hit |
|--------|-----------:|---------------:|
| Tank   | 6 | 1 |
| Base   | 9 | 1 |
| Wall   | 3 | 1 |

- Actions: `MOVE_UP`, `MOVE_DOWN`, `MOVE_LEFT`, `MOVE_RIGHT`, `FIRE`, `STAY`.
- A tank moves one cell per cycle. A bullet travels **3 cells per cycle** in the direction the tank is
  facing, one cell at a time, with a collision check after every cell; it stops on the first wall,
  tank or base it hits. Each tank may have one bullet in flight at a time.
- The game ends when a tank or a base is destroyed; the player whose tank and base both survive wins.
  A turn limit produces a draw.

### Approach

The game is modelled as a two-player **zero-sum game** (`TankBattleRules`: `ACTIONS`, `RESULT`,
`TERMINAL-TEST`, `UTILITY`). One game cycle is searched as two plies: MAX chooses its action, then MIN
replies, then both are applied simultaneously.

| Configuration | Search | Evaluation at the depth cut-off |
|---------------|--------|---------------------------------|
| Minimax | Minimax | Terminal utility only |
| Alpha-Beta | Alpha-Beta pruning | Terminal utility only |
| Heuristic Minimax | Minimax | Heuristic `EVAL(s)` |
| Heuristic Alpha-Beta | Alpha-Beta + move ordering | Heuristic `EVAL(s)` |

The heuristic `EVAL(s)` is a weighted sum of five features, all from MAX's point of view:
progress toward destroying the closer enemy target, total damage dealt vs. received,
Dijkstra distance to the enemy base (walls weighted by the shots needed to break them),
aim (being lined up with and facing a target), and bullets already flying toward a target.
Optional **iterative deepening** with a time budget keeps the GUI real-time.

### Usage

```bash
python -m task2_tank_battle                                  # GUI
python -m task2_tank_battle gui --plugin path/to/agent.py    # GUI with an extra agent file
python -m task2_tank_battle benchmark                        # compare the 4 search configurations
python -m task2_tank_battle tournament                       # round-robin tournament between agents
```

Tournament options: `--agents`, `--maps`, `--depth`, `--time-limit`, `--max-turns`, `--seed`, `--output`.

### GUI controls

In the menu, choose the controller of each player (Human, one of the 4 search configurations,
Random, or a plugin), the map, the search depth and the time budget, then press `Enter`.

| Player 1 | Player 2 | Action |
|----------|----------|--------|
| `W` `A` `S` `D` | Arrow keys | Move |
| `Space` | `Enter` | Fire |
| `X` | `Right Shift` | Stay |

`P` pause · `N` single step · `F` change speed · `R` restart · `Esc` back to menu.

### Integrating algorithms from other groups

Any `.py` file placed in [`task2_tank_battle/plugins/`](task2_tank_battle/plugins/) (or passed with
`--plugin`) is loaded automatically; press **Reload plugins** in the menu to pick up new files.
A plugin may provide **any one** of:

1. a subclass of `BaseAgent` implementing `choose_action(state, player)`;
2. any class with a `choose_action(state, player)` method;
3. a module-level function `choose_action(state, player)`.

`choose_action` may return an `Action` or its name as a string (e.g. `"FIRE"`). Exceptions and
unknown values are converted to `STAY`, so a faulty plugin cannot crash a match.

```python
# task2_tank_battle/plugins/my_group_agent.py
from task2_tank_battle.agents.base_agent import BaseAgent
from task2_tank_battle.core.actions import Action


class MyGroupAgent(BaseAgent):
    name = "My Group"

    def choose_action(self, state, player):
        return Action.FIRE
```

See [`greedy_hunter_agent.py`](task2_tank_battle/plugins/greedy_hunter_agent.py) for a complete example.

### Custom maps

Maps are plain-text files in [`task2_tank_battle/maps/`](task2_tank_battle/maps/):
`.` empty, `#` brick wall, `1` / `2` tank spawns, `A` / `B` bases of player 1 / 2,
lines starting with `;` are comments. Random symmetric maps (13×13, 17×17, 21×21) can also be generated
from the menu.

### Results

Stored in [`task2_tank_battle/results/`](task2_tank_battle/results/):
`search_benchmark.csv` / `.png` (time, generated nodes, evaluated leaves, prunings and effective
branching factor for depths 1–4 on four fixed scenarios) and the tournament logs and standings.
The benchmark asserts that Alpha-Beta always returns the same root value as Minimax.

---

## Task 3 — Kakuro

### CSP formulation

| Component | Definition |
|-----------|------------|
| Variables | Every white cell |
| Domains | `{1, …, 9}` |
| Constraints | One n-ary constraint per clue: the cells of the run are **all different** and **sum** to the clue |

### Solver

- **Preprocessing (node consistency):** each cell keeps only the digits that appear in some valid
  digit set of its runs (e.g. 2 cells summing to 16 → `{7, 9}`).
- **GAC-3:** a value survives only if a valid digit set contains it *and* the other cells of the run can
  take the remaining digits (checked with bipartite perfect matching).
- **Backtracking search** with **MAC** (GAC-3 after every assignment) or forward checking,
  **MRV** with **Degree** tie-break for variable ordering, and **LCV** for value ordering.

### Usage

```bash
python -m task3_kakuro                        # GUI
python -m task3_kakuro solve advanced_9x9     # print the solution of a puzzle
python -m task3_kakuro benchmark              # correctness / stability / effectiveness experiments
```

Benchmark options: `--puzzles <names…>` and `--seeds <n>` (number of shuffled variable orders).

### GUI

- **Solver mode** — press `S` to solve and record a trace, then replay it with `Space` (play / pause),
  `←` / `→` (step), `Home` / `End`. Each cell shows its **current domain**; the panel shows the active
  constraint, values removed by propagation, assignments, wipe-outs and backtracks.
- **Play mode** — select a cell and type `1`–`9` (`Backspace` / `0` to erase), `C` to check,
  `H` for a hint.

### Puzzles

Stored in [`task3_kakuro/puzzles/`](task3_kakuro/puzzles/): `basic_5x5.txt` (example board) and
`advanced_9x9.txt` (the more complex test case). Format: `X` block, `.` white cell,
`D\R` clue with down sum `D` and across sum `R` (either may be empty, e.g. `21\` or `\16`).

### Results

[`task3_kakuro/results/kakuro_benchmark.csv`](task3_kakuro/results/kakuro_benchmark.csv) and
`kakuro_benchmark.png` compare seven solver configurations, from plain backtracking to
MAC + MRV/Degree + LCV + initial GAC, over 10 shuffled variable orders per puzzle.

---

## Project structure

```
.
├── main.py                  # Launcher hub for the three tasks
├── requirements.txt
├── common/                  # Shared PyGame base app, theme and widgets
├── task1_nqueens/
│   ├── core/                # Board model and solution checker
│   ├── logic/               # Variable mapping and CNF encoder
│   ├── solvers/             # Glucose3 solver, Min-Conflicts, variable selectors
│   ├── experiments/         # Benchmark script
│   ├── tests/               # unittest suite (encodings, Min-Conflicts, board / checker)
│   ├── ui/                  # PyGame interface
│   └── results/             # CSV and plots
├── task2_tank_battle/
│   ├── core/                # Actions, entities, game state, rules, map loader, match runner
│   ├── ai/                  # Minimax / Alpha-Beta and evaluation functions
│   ├── agents/              # Agent interface, search agents, plugin registry
│   ├── plugins/             # Drop-in agents from other groups
│   ├── maps/                # Text maps
│   ├── experiments/         # Search benchmark, scenarios, tournament
│   ├── ui/                  # PyGame interface
│   └── results/             # CSV, logs and plots
└── task3_kakuro/
    ├── core/                # Puzzle model, loader and CSP model
    ├── solvers/             # Digit-set table, propagation, backtracking, trace recorder
    ├── puzzles/             # Puzzle files
    ├── experiments/         # Benchmark script
    ├── ui/                  # PyGame interface
    └── results/             # CSV and plots
```

## Reproducing the experiments

```bash
python -m task1_nqueens benchmark --runs 20
python -m task2_tank_battle benchmark
python -m task2_tank_battle tournament
python -m task3_kakuro benchmark
```

Each command prints a summary table and overwrites the CSV and PNG files in the task's `results/`
folder. All experiments use fixed seeds, so the search statistics are reproducible; timings depend on
the machine.
