"""Build the initial GameState from a text map, or generate a fair random map."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from task2_tank_battle.core.actions import Direction
from task2_tank_battle.core.entities import WALL_MAX_HP, Base, Tank
from task2_tank_battle.core.game_state import PLAYER_ONE, PLAYER_TWO, GameState

MAPS_DIR = Path(__file__).resolve().parent.parent / "maps"
RANDOM_MAP_NAME = "Random symmetric"
# Menu name -> side length of the generated square map (the description does not fix the map size).
RANDOM_MAP_SIZES = {RANDOM_MAP_NAME: 13, f"{RANDOM_MAP_NAME} 17x17": 17, f"{RANDOM_MAP_NAME} 21x21": 21}


class MapFormatError(ValueError):
    pass


class MapLoader:
    """
    Map symbols:  '.' empty   '#' brick wall (3 HP)   '1' / '2' tank spawn   'A' / 'B' base of P1 / P2.
    Lines starting with ';' are comments.
    """

    @staticmethod
    def available_maps() -> List[str]:
        return sorted(path.stem for path in MAPS_DIR.glob("*.txt"))

    @classmethod
    def load(cls, name_or_path: str, max_turns: int = 200) -> GameState:
        path = Path(name_or_path)
        if not path.exists():
            path = MAPS_DIR / f"{name_or_path}.txt"
        return cls.parse(path.read_text(encoding="utf-8"), max_turns)

    @staticmethod
    def parse(text: str, max_turns: int = 200) -> GameState:
        rows = [line.rstrip() for line in text.splitlines() if line.strip() and not line.startswith(";")]
        if not rows:
            raise MapFormatError("Empty map")
        width, height = len(rows[0]), len(rows)
        walls: Dict[Tuple[int, int], int] = {}
        tanks: List[Optional[Tank]] = [None, None]
        bases: List[Optional[Base]] = [None, None]
        for y, row in enumerate(rows):
            if len(row) != width:
                raise MapFormatError(f"Row {y} has length {len(row)}, expected {width}")
            for x, symbol in enumerate(row):
                if symbol == "#":
                    walls[(x, y)] = WALL_MAX_HP
                elif symbol == "1":
                    tanks[PLAYER_ONE] = Tank(PLAYER_ONE, x, y, Direction.UP)
                elif symbol == "2":
                    tanks[PLAYER_TWO] = Tank(PLAYER_TWO, x, y, Direction.DOWN)
                elif symbol == "A":
                    bases[PLAYER_ONE] = Base(PLAYER_ONE, x, y)
                elif symbol == "B":
                    bases[PLAYER_TWO] = Base(PLAYER_TWO, x, y)
                elif symbol != ".":
                    raise MapFormatError(f"Unknown symbol '{symbol}' at ({x}, {y})")
        if None in tanks or None in bases:
            raise MapFormatError("Map needs tanks '1', '2' and bases 'A', 'B'")
        return GameState(width, height, walls, (tanks[0], tanks[1]), (bases[0], bases[1]), max_turns=max_turns)

    @staticmethod
    def to_text(state: GameState) -> str:
        grid = [["." for _ in range(state.width)] for _ in range(state.height)]
        for (x, y) in state.walls:
            grid[y][x] = "#"
        for symbol, base in zip("AB", state.bases):
            grid[base.y][base.x] = symbol
        for symbol, tank in zip("12", state.tanks):
            grid[tank.y][tank.x] = symbol
        return "\n".join("".join(row) for row in grid)


class RandomMapGenerator:
    """
    Point-symmetric random map: cell (x, y) mirrors (W-1-x, H-1-y), so both sides are equally strong.
    A seed makes every map reproducible for fair experiments.
    """

    def __init__(self, width: int = 13, height: int = 13, wall_density: float = 0.28):
        self.width = width
        self.height = height
        self.wall_density = wall_density

    def generate(self, seed: Optional[int] = None, max_turns: int = 200) -> GameState:
        rng = random.Random(seed)
        w, h = self.width, self.height
        base_x = w // 2
        p1_base = (base_x, h - 1)
        p1_spawn = (rng.choice([2, 3, 4, w - 5, w - 4, w - 3]), h - 2)
        # Brick ring around the base, like a fortress.
        fortress = {(base_x - 1, h - 1), (base_x + 1, h - 1), (base_x - 1, h - 2), (base_x, h - 2), (base_x + 1, h - 2)}

        reserved = {p1_base, p1_spawn} | fortress
        sx, sy = p1_spawn
        reserved |= {(sx + dx, sy + dy) for dx, dy in ((0, -1), (1, 0), (-1, 0), (0, -2))}

        walls: Dict[Tuple[int, int], int] = {}
        for index in range(w * h):
            mirror = w * h - 1 - index
            if index > mirror:
                break
            x, y = index % w, index // w
            mx, my = mirror % w, mirror // w
            if (x, y) in reserved or (mx, my) in reserved:
                continue
            if rng.random() < self.wall_density:
                walls[(x, y)] = WALL_MAX_HP
                walls[(mx, my)] = WALL_MAX_HP
        for (x, y) in fortress:
            walls[(x, y)] = WALL_MAX_HP
            walls[(w - 1 - x, h - 1 - y)] = WALL_MAX_HP

        tanks = (Tank(PLAYER_ONE, sx, sy, Direction.UP), Tank(PLAYER_TWO, w - 1 - sx, h - 1 - sy, Direction.DOWN))
        bases = (Base(PLAYER_ONE, *p1_base), Base(PLAYER_TWO, w - 1 - p1_base[0], h - 1 - p1_base[1]))
        return GameState(w, h, walls, tanks, bases, max_turns=max_turns)


def build_initial_state(map_name: str, seed: Optional[int] = None, max_turns: int = 200) -> GameState:
    if map_name in RANDOM_MAP_SIZES:
        size = RANDOM_MAP_SIZES[map_name]
        return RandomMapGenerator(size, size).generate(seed, max_turns)
    return MapLoader.load(map_name, max_turns)
