"""Registry of every selectable controller + plugin loader for algorithms written by other groups."""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional

from task2_tank_battle.agents.base_agent import BaseAgent
from task2_tank_battle.agents.search_agent import SEARCH_CONFIGS, create_search_agent
from task2_tank_battle.agents.simple_agents import HumanAgent, RandomAgent
from task2_tank_battle.core.actions import Action, parse_action
from task2_tank_battle.core.game_state import GameState

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins"


class AgentSpec(NamedTuple):
    key: str
    source: str
    uses_search: bool
    factory: Callable[[int, Optional[float], Optional[int]], BaseAgent]


class ExternalAgentAdapter(BaseAgent):
    """
    Adapter pattern: wraps a foreign object/function so it behaves like a BaseAgent.
    Accepts actions returned as Action or as strings ("FIRE"); crashes become STAY so the match goes on.
    """

    def __init__(self, name: str, decide: Callable[[GameState, int], object]):
        super().__init__(name)
        self._decide = decide
        self.errors = 0

    def choose_action(self, state: GameState, player: int) -> Action:
        try:
            return parse_action(self._decide(state, player))
        except Exception:
            self.errors += 1
            return Action.STAY


class AgentRegistry:
    def __init__(self, plugin_dir: Path = PLUGIN_DIR):
        self.plugin_dir = Path(plugin_dir)
        self._specs: Dict[str, AgentSpec] = {}
        self.load_errors: List[str] = []
        self._register_builtins()

    def _register_builtins(self) -> None:
        self._add(AgentSpec("Human", "built-in", False, lambda d, t, s: HumanAgent()))
        for config in SEARCH_CONFIGS:
            self._add(AgentSpec(config, "built-in", True,
                                lambda d, t, s, c=config: create_search_agent(c, d, t, s)))
        self._add(AgentSpec("Random", "built-in", False, lambda d, t, s: RandomAgent(s)))

    def _add(self, spec: AgentSpec) -> None:
        self._specs[spec.key] = spec

    @property
    def keys(self) -> List[str]:
        return list(self._specs)

    def spec(self, key: str) -> AgentSpec:
        return self._specs[key]

    def create(self, key: str, depth: int = 2, time_limit: Optional[float] = None,
               seed: Optional[int] = None) -> BaseAgent:
        return self._specs[key].factory(depth, time_limit, seed)

    # ------------------------------------------------------------------ plugins
    def load_plugins(self, extra_files: Optional[List[str]] = None) -> List[str]:
        """
        Import every *.py in plugins/ (and extra files). A plugin may provide:
        (a) a subclass of BaseAgent, (b) any class with choose_action(state, player),
        or (c) a module-level function choose_action(state, player).
        """
        self._specs = {k: v for k, v in self._specs.items() if v.source == "built-in"}
        self.load_errors = []
        files = sorted(self.plugin_dir.glob("*.py")) if self.plugin_dir.exists() else []
        files += [Path(f) for f in (extra_files or [])]
        loaded = []
        for path in files:
            if path.name.startswith("_"):
                continue
            try:
                loaded += self._load_file(path)
            except Exception as error:
                self.load_errors.append(f"{path.name}: {error}")
        return loaded

    def _load_file(self, path: Path) -> List[str]:
        spec = importlib.util.spec_from_file_location(f"tank_plugin_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        names = []
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            if issubclass(cls, BaseAgent) and not inspect.isabstract(cls):
                key = f"{getattr(cls, 'name', cls.__name__)} [plugin]"
                self._add(AgentSpec(key, path.name, False, lambda d, t, s, c=cls: c()))
                names.append(key)
            elif callable(getattr(cls, "choose_action", None)):
                key = f"{cls.__name__} [plugin]"
                self._add(AgentSpec(key, path.name, False,
                                    lambda d, t, s, c=cls, k=key: ExternalAgentAdapter(k, c().choose_action)))
                names.append(key)
        function = getattr(module, "choose_action", None)
        if callable(function) and not inspect.isclass(function):
            key = f"{path.stem} [plugin]"
            self._add(AgentSpec(key, path.name, False, lambda d, t, s, f=function, k=key: ExternalAgentAdapter(k, f)))
            names.append(key)
        return names
