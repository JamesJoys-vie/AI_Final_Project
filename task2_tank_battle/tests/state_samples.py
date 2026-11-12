"""Reproducible sample of reachable game states (bullets in flight, damaged walls, low HP, terminal states)."""
from __future__ import annotations

import random
from typing import List

from task2_tank_battle.core.actions import ALL_ACTIONS, Action
from task2_tank_battle.core.game_state import GameState
from task2_tank_battle.core.map_loader import MapLoader, build_initial_state
from task2_tank_battle.experiments.scenarios import build_scenarios
from task2_tank_battle.tests.reference_impl import ReferenceRules

# FIRE is drawn more often so that walls get damaged and bullets are usually in the air.
_WEIGHTS = {Action.FIRE: 4, Action.STAY: 1, Action.MOVE_UP: 2, Action.MOVE_DOWN: 2,
            Action.MOVE_LEFT: 2, Action.MOVE_RIGHT: 2}


def _random_action(rng: random.Random, rules: ReferenceRules, state: GameState, player: int) -> Action:
    actions = rules.legal_actions(state, player)
    return rng.choices(actions, weights=[_WEIGHTS[a] for a in actions])[0]


def _with_low_hp(rng: random.Random, state: GameState) -> GameState:
    """Same position with random HP, so hits can end the game within the next cycle."""
    tanks = tuple(t._replace(hp=rng.randint(1, 3)) for t in state.tanks)
    bases = tuple(b._replace(hp=rng.randint(1, 3)) for b in state.bases)
    return GameState(state.width, state.height, state.walls, tanks, bases, state.bullets,
                     state.turn, state.max_turns)


def initial_states() -> List[GameState]:
    states = [MapLoader.load(name) for name in MapLoader.available_maps()]
    states += [build_initial_state("Random symmetric", seed) for seed in (1, 2, 3)]
    states += [build_initial_state("Random symmetric 17x17", 4)]
    states += list(build_scenarios().values())
    return states


def sample_states(count: int = 300, seed: int = 12345, include_terminal: bool = True) -> List[GameState]:
    """`count` states collected along random playouts from every map and benchmark scenario."""
    rng = random.Random(seed)
    rules = ReferenceRules()
    starts = initial_states()
    samples: List[GameState] = []
    while len(samples) < count:
        state = rng.choice(starts)
        if rng.random() < 0.4:
            state = _with_low_hp(rng, state)
        for _ in range(rng.randint(1, 60)):
            if rules.is_terminal(state):
                break
            state = rules.step(state, (_random_action(rng, rules, state, 0), _random_action(rng, rules, state, 1)))
            if rng.random() < 0.15 and (include_terminal or not rules.is_terminal(state)):
                samples.append(state)
        if include_terminal or not rules.is_terminal(state):
            samples.append(state)
    return samples[:count]
