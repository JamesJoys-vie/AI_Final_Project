"""
Experiment 2 - round-robin tournament. Every pair plays on the same maps twice with sides swapped,
so neither side or map gives an advantage. Win = 3 pts, draw = 1 pt.
"""
from __future__ import annotations

import argparse
import csv
import itertools
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from task2_tank_battle.agents.agent_registry import AgentRegistry
from task2_tank_battle.core.map_loader import RANDOM_MAP_NAME, build_initial_state
from task2_tank_battle.core.match_runner import MatchRunner

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
DEFAULT_AGENTS = ("Minimax", "Alpha-Beta", "Heuristic Minimax", "Heuristic Alpha-Beta", "Random",
                  "Greedy Hunter [plugin]")


class Standing:
    def __init__(self, name: str):
        self.name = name
        self.wins = self.draws = self.losses = 0
        self.think_ms: List[float] = []

    @property
    def points(self) -> int:
        return 3 * self.wins + self.draws

    @property
    def played(self) -> int:
        return self.wins + self.draws + self.losses


class Tournament:
    def __init__(self, agent_keys: Sequence[str], maps: Sequence[str], depth: int = 4,
                 time_limit: float = 0.15, max_turns: int = 150, seed: int = 7):
        self.registry = AgentRegistry()
        self.registry.load_plugins()
        self.agent_keys = [key for key in agent_keys if key in self.registry.keys]
        self.maps = maps
        self.depth = depth
        self.time_limit = time_limit
        self.max_turns = max_turns
        self.seed = seed
        self.records: List[Dict] = []
        self.standings = {key: Standing(key) for key in self.agent_keys}

    def run(self, verbose: bool = True, on_match=None) -> List[Standing]:
        runner = MatchRunner()
        match_id = 0
        for (key_a, key_b), (map_index, map_name) in itertools.product(
                itertools.combinations(self.agent_keys, 2), enumerate(self.maps)):
            map_seed = self.seed + map_index
            for first, second in ((key_a, key_b), (key_b, key_a)):
                match_id += 1
                state = build_initial_state(map_name, map_seed, self.max_turns)
                agents = [self.registry.create(first, self.depth, self.time_limit, self.seed + match_id),
                          self.registry.create(second, self.depth, self.time_limit, self.seed + 100 + match_id)]
                result = runner.play(state, agents)
                self._record(match_id, map_name, map_seed, first, second, result)
                if verbose:
                    print(f"#{match_id:03d} {map_name:16s} {first:24s} vs {second:24s} -> "
                          f"{result.outcome.value:14s} ({result.turns} turns)")
                if on_match:
                    on_match(match_id)
        return self.table()

    def _record(self, match_id: int, map_name: str, map_seed: int, first: str, second: str, result) -> None:
        names = (first, second)
        for player, name in enumerate(names):
            standing = self.standings[name]
            standing.think_ms.append(result.average_ms(player))
            if result.winner is None:
                standing.draws += 1
            elif result.winner == player:
                standing.wins += 1
            else:
                standing.losses += 1
        self.records.append({"match": match_id, "map": map_name, "map_seed": map_seed,
                             "player_1": first, "player_2": second, "outcome": result.outcome.value,
                             "turns": result.turns,
                             "p1_ms_per_move": round(result.average_ms(0), 2),
                             "p2_ms_per_move": round(result.average_ms(1), 2)})

    def table(self) -> List[Standing]:
        return ranked(self.standings.values())

    def print_table(self) -> None:
        print_standings(self.table())

    def save(self, path: Optional[Path] = None) -> Path:
        path = path or RESULTS_DIR / "tournament_matches.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(self.records[0].keys()))
            writer.writeheader()
            writer.writerows(self.records)
        save_standings(self.table(), path.with_name(path.stem.replace("matches", "standings") + ".csv"))
        return path


def ranked(standings) -> List[Standing]:
    return sorted(standings, key=lambda s: (s.points, s.wins), reverse=True)


def print_standings(table: Sequence[Standing]) -> None:
    print(f"\n{'Rank':<5}{'Agent':<26}{'P':>4}{'W':>4}{'D':>4}{'L':>4}{'Pts':>5}{'ms/move':>10}")
    for rank, s in enumerate(table, 1):
        avg = sum(s.think_ms) / max(1, len(s.think_ms))
        print(f"{rank:<5}{s.name:<26}{s.played:>4}{s.wins:>4}{s.draws:>4}{s.losses:>4}{s.points:>5}{avg:>10.1f}")


def save_standings(table: Sequence[Standing], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["rank", "agent", "played", "wins", "draws", "losses", "points", "avg_ms_per_move"])
        for rank, s in enumerate(table, 1):
            writer.writerow([rank, s.name, s.played, s.wins, s.draws, s.losses, s.points,
                             round(sum(s.think_ms) / max(1, len(s.think_ms)), 2)])
    return path


def combine_match_files(paths: Sequence[Path]) -> List[Standing]:
    """Standings over several match CSVs (e.g. one tournament per map, each with its own seed)."""
    standings: Dict[str, Standing] = {}
    for path in paths:
        with open(path, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                winner = {"Player 1 wins": 0, "Player 2 wins": 1}.get(row["outcome"])
                for player, name in enumerate((row["player_1"], row["player_2"])):
                    standing = standings.setdefault(name, Standing(name))
                    standing.think_ms.append(float(row[f"p{player + 1}_ms_per_move"]))
                    if winner is None:
                        standing.draws += 1
                    elif winner == player:
                        standing.wins += 1
                    else:
                        standing.losses += 1
    return ranked(standings.values())


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Tank Battle round-robin tournament")
    parser.add_argument("--agents", nargs="*", default=list(DEFAULT_AGENTS))
    parser.add_argument("--maps", nargs="*", default=["classic", RANDOM_MAP_NAME])
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--time-limit", type=float, default=0.15)
    parser.add_argument("--max-turns", type=int, default=150)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", default=None, help="CSV path for the match list")
    parser.add_argument("--combine", nargs="+", default=None, metavar="MATCHES_CSV",
                        help="do not play: build one standings table from existing match CSVs "
                             "(written to --output, default results/tournament_standings_combined.csv)")
    args = parser.parse_args(argv)
    if args.combine:
        table = combine_match_files([Path(p) for p in args.combine])
        print_standings(table)
        output = Path(args.output) if args.output else RESULTS_DIR / "tournament_standings_combined.csv"
        print("CSV:", save_standings(table, output))
        return
    tournament = Tournament(args.agents, args.maps, args.depth, args.time_limit, args.max_turns, args.seed)
    tournament.run()
    tournament.print_table()
    print("CSV:", tournament.save(Path(args.output) if args.output else None))


if __name__ == "__main__":
    main()
