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

- **`sat_glucose3.csv`**: variables, clauses, and encode / load / search / solve time per encoding.
  - Covers N = 4…200; each timing is the median of 3 runs.
  - Each encoding stops at a different N: pairwise at 100, pairwise+alo at 128, seqcounter+alo at 200.
- **`min_conflicts.csv`**: success rate, attacking pairs at the start, steps, restarts and time per strategy and start mode.
  - Covers N = 8…10,000 with 20 seeds per configuration.
  - The random start stops at N = 5000.
- **`nqueens_experiments.png`**: plots of the above.

Highlights:

| Glucose3, N = 100 | clauses | encode + solve |
|---|---:|---:|
| pairwise | 1,646,800 | 5.7 s |
| pairwise + column ALO | 1,646,900 | 0.82 s |
| seqcounter + column ALO | 117,788 | 0.12 s |

| Min-Conflicts, 20 seeds | standard: mean steps / median ms | heuristic: mean steps / median ms |
|---|---:|---:|
| N = 1000, random start | 710 / 68 | 544 / 53 |
| N = 1000, greedy start | 103 / 11 | 51 / 7.4 |
| N = 5000, random start | 3155 / 1221 | 2482 / 1097 |
| N = 10000, greedy start | 167 / 183 | 123 / 129 |

- **Heuristic vs standard:** the proposed heuristic needs fewer steps than the standard version at every N, with both start modes. All runs succeed.
- **Greedy start:** starting greedy cuts the attacking pairs at the start (N = 1000: from about 1155 to about 17) and the time by roughly 5–20× for N ≥ 1000. The gain is small for N ≤ 64.
- **Column ALO:** these redundant clauses are what make Glucose3 fast.
- **Sequential counter:** it shrinks the formula by about 14× at N = 100. Its search time varies more, though: about 0.6 s at N = 48 against 11 ms at N = 64.

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
| Heuristic Alpha-Beta | Alpha-Beta + move ordering, killer moves, transposition table, internal iterative deepening | Heuristic `EVAL(s)` |

The heuristic `EVAL(s)` is a weighted sum of five features, all from MAX's point of view:
progress toward destroying the closer enemy target, total damage dealt vs. received,
Dijkstra distance to the enemy base (walls weighted by the shots needed to break them),
aim (being lined up with and facing a target), and bullets already flying toward a target.
Optional **iterative deepening** with a time budget keeps the GUI real-time.

**Fast game engine.** `RESULT(s, a)` runs once per generated node, so it is written for speed: direction
offsets are plain attributes (no Enum property or Enum hashing in the inner loop), states are built with
`tuple.__new__` instead of `NamedTuple._replace`, there is no closure per call, and a cycle with no bullet in the
air skips the bullet phase. The search checks `TERMINAL-TEST` once per node, and each state's MIN replies are
ordered once instead of once per MAX action. The tests check against a frozen copy of the original code that every
state and `EVAL(s)` value is unchanged, and the benchmark explores exactly the same nodes as before; only the time
changes: **2.0–2.6× more nodes per second** for all four configurations (see `results/baseline/` vs `results/phase2/`).

**Search enhancements (Heuristic Alpha-Beta).** Alpha-Beta prunes only as well as its move ordering, so the
heuristic configuration adds the classic enhancements on top of the static ordering. Plain Minimax and
Alpha-Beta stay textbook.
- *Killer moves and countermoves:* an action that caused a cut-off is tried first in sibling nodes at the same ply.
  At MIN nodes the reply that refuted the same MAX action comes first.
- *Transposition table:* stores each searched state's value with a bound flag (exact / lower / upper) and its best
  action. The turn is part of the key, so within one search a state is always reached at the same remaining depth;
  bound entries are used only for cut-offs. The root value therefore stays exactly the Minimax value (tested).
- *Internal iterative deepening:* depths 1 … d−1 are searched first, so the table and killers order depth d well.
  With a time budget, the agent's own iterative deepening keeps the table between depths and searches the
  previous best action first.

Each enhancement can be switched on separately (`--ablation` in the benchmark). Summed over the 4 benchmark
scenarios at depth 4:

| Heuristic Alpha-Beta variant | Nodes | Time |
|------------------------------|------:|-----:|
| No move ordering | 102,280 | 634 ms |
| + static move ordering | 20,135 | 214 ms |
| + killer moves / countermoves | 18,059 | 192 ms |
| + transposition table | 12,617 | 138 ms |
| + internal iterative deepening (final) | 10,406 | 116 ms |

### Usage

```bash
python -m task2_tank_battle                                  # GUI
python -m task2_tank_battle gui --plugin path/to/agent.py    # GUI with an extra agent file
python -m task2_tank_battle benchmark                        # compare the 4 search configurations
python -m task2_tank_battle tournament                       # round-robin tournament between agents
python -m task2_tank_battle depth                            # search depth reached within a time budget
```

Benchmark options: `--depths`, `--minimax-max-depth`, `--repeats` (times are medians; searches slower
than 1 s run once), `--configs`, `--ablation`, `--seed`, `--output`, `--no-plot`.
Tournament options: `--agents`, `--maps`, `--depth`, `--time-limit`, `--max-turns`, `--seed`, `--output`,
`--combine <matches.csv…>` (standings over several finished tournaments, without playing).
Depth options: `--budgets` (seconds per move), `--configs`, `--max-depth`, `--repeats`, `--seed`, `--output`, `--no-plot`.

The committed results were produced with:

```bash
python -m task2_tank_battle benchmark --ablation
python -m task2_tank_battle depth
python -m task2_tank_battle tournament --maps classic --max-turns 120 --time-limit 0.1 --output task2_tank_battle/results/tournament_classic_matches.csv
python -m task2_tank_battle tournament --maps "Random symmetric" --max-turns 120 --time-limit 0.1 --output task2_tank_battle/results/tournament_random_matches.csv
python -m task2_tank_battle tournament --combine task2_tank_battle/results/tournament_classic_matches.csv task2_tank_battle/results/tournament_random_matches.csv
python -m task2_tank_battle tournament --maps classic "Random symmetric" --depth 8 --max-turns 120 --time-limit 0.1 --output task2_tank_battle/results/tournament_depth8_matches.csv
```

### Tests

```bash
python -m unittest discover -s task2_tank_battle/tests -t .
```

The tests cover:
- **Rules:** bullets fly 3 cells per cycle with a collision check after every cell, walls, one bullet per tank,
  movement conflicts, terminal states and utility.
- **Reference engine:** `step()` and the heuristic `EVAL(s)` give exactly the same results as a frozen copy of
  the original code (`tests/reference_impl.py`) on 300 sampled states and all 36 joint actions.
- **Search:** Alpha-Beta with every combination of enhancements returns the Minimax value on sampled states;
  bound entries of the transposition table are never used as exact values, also when the table is kept between
  iterative-deepening depths; the previous best action is searched first; every configuration takes a win in one
  and dodges a lethal shot; iterative deepening respects its time budget.

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
- `search_benchmark.csv` / `.png`: time (median of 5 runs), generated nodes, nodes per second, evaluated
  leaves, prunings, table hits and effective branching factor for depths 1–4 on four fixed scenarios, plus the
  Heuristic Alpha-Beta ablation rows (`search_ablation.png`). The benchmark asserts that every configuration
  with the same evaluator returns the same root value.
- `depth_budget.csv` / `_summary.csv` / `.png`: depth completed by iterative deepening within 50 / 150 / 500 ms
  per move on 12 states (scenarios, every bundled map, random 13×13 / 17×17 / 21×21 maps).
- `tournament_classic_*`, `tournament_random_*`, `tournament_standings_combined.csv`: round-robin
  tournaments, 100 ms per move; `tournament_depth8_*`: the same with depth cap 8 instead of 4.
- `baseline/`, `phase2/`, `phase3/`: the benchmark after each optimization phase (and the depth experiment
  run on the original code in `baseline/`), kept for before/after comparisons.

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
│   ├── tests/               # unittest suite (rules, reference engine, search)
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
