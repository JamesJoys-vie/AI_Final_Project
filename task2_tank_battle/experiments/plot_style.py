"""Shared look of the experiment plots (matplotlib), so every figure uses the same colours per configuration."""
from __future__ import annotations

# Categorical slots 1-4 of a palette validated for colour-vision deficiencies on a light surface.
# Each configuration keeps its colour in every figure. Aqua and yellow are below 3:1 contrast on the
# surface, so bars carry value labels and every figure has a CSV table next to it.
CONFIG_COLORS = {
    "Minimax": "#2a78d6",
    "Alpha-Beta": "#eb6834",
    "Heuristic Minimax": "#1baf7a",
    "Heuristic Alpha-Beta": "#eda100",
}
SEQUENTIAL = "#2a78d6"  # single-series charts (e.g. the ablation bars)
INK, MUTED, SURFACE, GRID, AXIS = "#2b2b29", "#6b6a64", "#fcfcfb", "#e4e3df", "#c9c8c2"


def color_of(config: str, index: int = 0) -> str:
    return CONFIG_COLORS.get(config, list(CONFIG_COLORS.values())[index % len(CONFIG_COLORS)])


def style_axes(ax, grid_axis: str = "y") -> None:
    """Recessive grid and axes: light grid lines, no box, muted tick labels."""
    ax.set_facecolor(SURFACE)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
