"""
Entry point of Task 3. Run from the `source` folder:
    python -m task3_kakuro                     -> GUI (visualize the solver / play yourself)
    python -m task3_kakuro solve advanced_9x9  -> print the solution of one puzzle
    python -m task3_kakuro benchmark           -> correctness / stability / effectiveness experiments
"""
from __future__ import annotations

import sys
from typing import Optional, Sequence


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
