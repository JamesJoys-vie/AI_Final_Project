"""
Entry point of Task 3. Run from the `source` folder (the repository root):
    python -m task3_kakuro                     -> GUI (visualize the solver / play yourself)
    python -m task3_kakuro solve advanced_9x9  -> print the solution of one puzzle
    python -m task3_kakuro benchmark           -> correctness / stability / effectiveness experiments
It can also be started as a script from any folder, e.g.  python path/to/task3_kakuro/main.py solve advanced_9x9
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

if __package__ in (None, ""):  # run as a script, not with -m: make `task3_kakuro` (and `common`) importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv.pop(0) if argv else "gui"

    if command == "solve":
        from task3_kakuro.experiments.benchmark import print_solution
        print_solution(argv[0] if argv else "advanced_9x9")
    elif command == "benchmark":
        from task3_kakuro.experiments.benchmark import main as run_benchmark
        run_benchmark(argv)
    elif command == "gui":
        import pygame
        from task3_kakuro.ui.kakuro_app import KakuroApp
        KakuroApp().run()
        pygame.quit()
    else:
        print(f"Unknown command '{command}'. Use: gui | solve NAME | benchmark")


if __name__ == "__main__":
    main()
