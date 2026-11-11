"""Small reusable PyGame widgets: text helpers, panel, button, option selector, toast."""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

import pygame

from common.theme import FontBook, Theme

Color = Tuple[int, int, int]


def lerp_color(a: Color, b: Color, t: float) -> Color:
    """Linear blend between two colors, t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def draw_text(surface: pygame.Surface, text: str, pos: Tuple[int, int], size: int = 18,
              color: Color = Theme.TEXT, bold: bool = False, anchor: str = "topleft",
              mono: bool = False) -> pygame.Rect:
    """Render one line of text; `anchor` is any pygame.Rect attribute (center, midleft...)."""
    image = FontBook.get(size, bold, mono).render(str(text), True, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def wrap_text(text: str, size: int, max_width: int, bold: bool = False) -> List[str]:
    """Split text into lines that fit `max_width` pixels."""
    font = FontBook.get(size, bold)
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, title: Optional[str] = None,
               color: Color = Theme.SURFACE, radius: int = 12) -> pygame.Rect:
    """Rounded card with optional title. Returns the inner content rect."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, Theme.BORDER, rect, width=1, border_radius=radius)
    inner = rect.inflate(-24, -20)
    if title:
        draw_text(surface, title, (inner.x, inner.y), 16, Theme.TEXT_MUTED, bold=True)
        inner.y += 28
        inner.height -= 28
    return inner


def draw_bar(surface: pygame.Surface, rect: pygame.Rect, ratio: float, color: Color,
             back: Color = Theme.SURFACE_LIGHT) -> None:
    """Horizontal progress / HP bar."""
    pygame.draw.rect(surface, back, rect, border_radius=rect.height // 2)
    fill = rect.copy()
    fill.width = int(rect.width * max(0.0, min(1.0, ratio)))
    if fill.width > 0:
        pygame.draw.rect(surface, color, fill, border_radius=rect.height // 2)


class Button:
    """Clickable button with smooth hover animation."""

    def __init__(self, rect: Tuple[int, int, int, int], label: str, on_click: Callable[[], None],
                 style: str = "primary", hotkey: Optional[int] = None, font_size: int = 17):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.style = style
        self.hotkey = hotkey
        self.font_size = font_size
        self.enabled = True
        self._hover = 0.0

    def _colors(self) -> Tuple[Color, Color]:
        if self.style == "primary":
            return Theme.ACCENT_DARK, Theme.ACCENT
        if self.style == "danger":
            return (150, 52, 60), Theme.DANGER
        if self.style == "success":
            return (40, 130, 86), Theme.SUCCESS
        return Theme.SURFACE_LIGHT, Theme.SURFACE_HOVER

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.on_click()
            return True
        if self.hotkey is not None and event.type == pygame.KEYDOWN and event.key == self.hotkey:
            self.on_click()
            return True
        return False

    def update(self, dt: float) -> None:
        target = 1.0 if self.enabled and self.rect.collidepoint(pygame.mouse.get_pos()) else 0.0
        self._hover += (target - self._hover) * min(1.0, dt * 12)

    def draw(self, surface: pygame.Surface) -> None:
        base, hover = self._colors()
        color = lerp_color(base, hover, self._hover) if self.enabled else Theme.SURFACE
        rect = self.rect.move(0, -int(2 * self._hover))
        pygame.draw.rect(surface, color, rect, border_radius=10)
        text_color = Theme.TEXT if self.enabled else Theme.TEXT_DIM
        draw_text(surface, self.label, rect.center, self.font_size, text_color, bold=True, anchor="center")


class OptionSelector:
    """"<  value  >" selector that cycles through a list of options."""

    def __init__(self, rect: Tuple[int, int, int, int], label: str, options: Sequence[str],
                 index: int = 0, on_change: Optional[Callable[[int], None]] = None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.options = list(options)
        self.index = index if 0 <= index < len(self.options) else 0
        self.on_change = on_change
        self.left_rect = pygame.Rect(self.rect.x, self.rect.bottom - 34, 34, 34)
        self.right_rect = pygame.Rect(self.rect.right - 34, self.rect.bottom - 34, 34, 34)

    @property
    def value(self) -> str:
        return self.options[self.index]

    def set_options(self, options: Sequence[str], keep_value: bool = True) -> None:
        old = self.value if self.options else None
        self.options = list(options)
        self.index = self.options.index(old) if keep_value and old in self.options else 0

    def _shift(self, step: int) -> None:
        self.index = (self.index + step) % len(self.options)
        if self.on_change:
            self.on_change(self.index)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_rect.collidepoint(event.pos):
                self._shift(-1)
                return True
            if self.right_rect.collidepoint(event.pos):
                self._shift(1)
                return True
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self._shift(-1 if event.y > 0 else 1)
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        draw_text(surface, self.label, (self.rect.x, self.rect.y), 14, Theme.TEXT_MUTED)
        box = pygame.Rect(self.rect.x, self.rect.bottom - 34, self.rect.width, 34)
        pygame.draw.rect(surface, Theme.SURFACE_LIGHT, box, border_radius=8)
        mouse = pygame.mouse.get_pos()
        for arrow_rect, symbol in ((self.left_rect, "<"), (self.right_rect, ">")):
            color = Theme.ACCENT if arrow_rect.collidepoint(mouse) else Theme.TEXT_MUTED
            draw_text(surface, symbol, arrow_rect.center, 20, color, bold=True, anchor="center")
        draw_text(surface, self.value, box.center, 16, Theme.TEXT, bold=True, anchor="center")


class Toast:
    """Short message that fades out after a few seconds."""

    def __init__(self):
        self.message = ""
        self.color = Theme.TEXT
        self.time_left = 0.0

    def show(self, message: str, color: Color = Theme.TEXT, seconds: float = 2.5) -> None:
        self.message, self.color, self.time_left = message, color, seconds

    def update(self, dt: float) -> None:
        self.time_left = max(0.0, self.time_left - dt)

    def draw(self, surface: pygame.Surface) -> None:
        if self.time_left <= 0:
            return
        alpha = int(255 * min(1.0, self.time_left / 0.4))
        image = FontBook.get(16, True).render(self.message, True, self.color)
        box = pygame.Surface((image.get_width() + 32, image.get_height() + 16), pygame.SRCALPHA)
        pygame.draw.rect(box, (*Theme.SURFACE_LIGHT, 235), box.get_rect(), border_radius=10)
        box.blit(image, (16, 8))
        box.set_alpha(alpha)
        surface.blit(box, box.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 18)))
