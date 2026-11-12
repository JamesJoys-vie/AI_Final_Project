"""
Entry point of Task 2. Run from the `source` folder:
    python -m task2_tank_battle                 -> GUI (menu, human vs AI, AI vs AI)
    python -m task2_tank_battle benchmark       -> compare the 4 search configurations
    python -m task2_tank_battle tournament      -> round-robin tournament between agents
    python -m task2_tank_battle depth           -> search depth reached within a time budget per move
    python -m task2_tank_battle gui --plugin path/to/other_group_agent.py
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv.pop(0) if argv and not argv[0].startswith("-") else "gui"

    if command == "benchmark":
        from task2_tank_battle.experiments.search_benchmark import main as run_benchmark
        run_benchmark(argv)
    elif command == "depth":
        from task2_tank_battle.experiments.depth_budget import main as run_depth
        run_depth(argv)
    elif command == "tournament":
        from task2_tank_battle.experiments.tournament import main as run_tournament
        run_tournament(argv)
    elif command == "gui":
        parser = argparse.ArgumentParser(description="Tank Battle GUI")
        parser.add_argument("--plugin", action="append", default=[], help="extra plugin .py file")
        args = parser.parse_args(argv)
        import pygame
        from task2_tank_battle.ui.tank_battle_app import TankBattleApp
        TankBattleApp(extra_plugins=args.plugin).run()
        pygame.quit()
    else:
        print(f"Unknown command '{command}'. Use: gui | benchmark | tournament | depth")


if __name__ == "__main__":
    main()
