"""Shared colors, fonts and window size used by every task UI."""
from __future__ import annotations

import pygame

WINDOW_SIZE = (1200, 760)
FPS = 60


class Theme:
    """Dark color palette. Change values here to restyle all screens at once."""

    BACKGROUND = (16, 19, 27)
    SURFACE = (26, 31, 43)
    SURFACE_LIGHT = (36, 43, 59)
    SURFACE_HOVER = (48, 57, 78)
    BORDER = (58, 68, 92)

    TEXT = (232, 236, 244)
    TEXT_MUTED = (148, 157, 179)
    TEXT_DIM = (98, 106, 128)

    ACCENT = (92, 166, 255)
    ACCENT_DARK = (52, 108, 190)
    GOLD = (255, 190, 70)
    SUCCESS = (84, 212, 138)
    DANGER = (255, 96, 96)
    WARNING = (255, 170, 64)
    PURPLE = (176, 132, 255)


class FontBook:
    """Lazy font cache so each (size, bold) pair is created only once."""

    _FONT_NAMES = "segoeui,helveticaneue,helvetica,arial,dejavusans"
    _MONO_NAMES = "consolas,menlo,monaco,couriernew,dejavusansmono"
    _cache: dict = {}

    @classmethod
    def get(cls, size: int, bold: bool = False, mono: bool = False) -> pygame.font.Font:
        key = (size, bold, mono)
        if key not in cls._cache:
            if not pygame.font.get_init():
                pygame.font.init()
            names = cls._MONO_NAMES if mono else cls._FONT_NAMES
            cls._cache[key] = pygame.font.SysFont(names, size, bold=bold)
        return cls._cache[key]
