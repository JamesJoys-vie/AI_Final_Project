"""
Draws the battlefield (floor, walls, bases, tanks, bullets) and explosion particles.
Pure view: it reads GameState but never changes it.
"""
from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import pygame

from common.widgets import draw_bar, lerp_color
from task2_tank_battle.core.actions import Direction
from task2_tank_battle.core.entities import BASE_MAX_HP, TANK_MAX_HP, WALL_MAX_HP
from task2_tank_battle.core.game_state import GameState

PLAYER_COLORS = ((255, 196, 70), (92, 214, 140))
PLAYER_DARK = ((150, 104, 24), (36, 118, 74))
FLOOR_A = (28, 32, 40)
FLOOR_B = (31, 36, 45)
BRICK = (178, 86, 54)
BRICK_DARK = (120, 52, 34)
MORTAR = (86, 46, 34)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, vx, vy, life, color, size):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size = color, size


class BattlefieldRenderer:
    def __init__(self):
        self.cell = 48
        self.origin = (0, 0)
        self.particles: List[Particle] = []
        self.rng = random.Random(1)

    # ------------------------------------------------------------------ layout
    def fit(self, state: GameState, area: pygame.Rect) -> None:
        """Choose the largest cell size that fits the map inside `area`, then center it."""
        self.cell = max(8, min(area.width // state.width, area.height // state.height))
        board_w, board_h = self.cell * state.width, self.cell * state.height
        self.origin = (area.x + (area.width - board_w) // 2, area.y + (area.height - board_h) // 2)

    def board_rect(self, state: GameState) -> pygame.Rect:
        return pygame.Rect(self.origin[0], self.origin[1], self.cell * state.width, self.cell * state.height)

    def to_pixels(self, x: float, y: float) -> Tuple[float, float]:
        return self.origin[0] + (x + 0.5) * self.cell, self.origin[1] + (y + 0.5) * self.cell

    # ------------------------------------------------------------------ drawing
    def draw(self, surface: pygame.Surface, state: GameState, previous: Optional[GameState] = None,
             progress: float = 1.0) -> None:
        """
        While animating (progress < 1) tanks slide from `previous` to `state` and bullets follow their trails.
        """
        animating = previous is not None and progress < 1.0
        world = previous if animating else state
        self._draw_floor(surface, state)
        for (x, y), hp in world.walls.items():
            self._draw_wall(surface, x, y, hp)
        for base in world.bases:
            self._draw_base(surface, base.x, base.y, base.player, base.hp)
        for player, tank in enumerate(state.tanks):
            if animating:
                old = previous.tanks[player]
                tx = old.x + (tank.x - old.x) * self._ease(progress)
                ty = old.y + (tank.y - old.y) * self._ease(progress)
                hp = old.hp
            else:
                tx, ty, hp = tank.x, tank.y, tank.hp
            if hp > 0:
                self.draw_tank(surface, tx, ty, tank.facing, player, hp)
        if animating:
            for trail in state.trails:
                self._draw_trail_bullet(surface, trail.cells, trail.owner, progress)
        else:
            for bullet in state.bullets:
                cx, cy = self.to_pixels(bullet.x, bullet.y)
                self._draw_bullet(surface, cx, cy, bullet.owner)
        self._draw_particles(surface)

    @staticmethod
    def _ease(t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    def _draw_floor(self, surface: pygame.Surface, state: GameState) -> None:
        for y in range(state.height):
            for x in range(state.width):
                rect = pygame.Rect(self.origin[0] + x * self.cell, self.origin[1] + y * self.cell, self.cell, self.cell)
                pygame.draw.rect(surface, FLOOR_A if (x + y) % 2 == 0 else FLOOR_B, rect)
        pygame.draw.rect(surface, (64, 72, 92), self.board_rect(state), width=2, border_radius=4)

    def _draw_wall(self, surface: pygame.Surface, x: int, y: int, hp: int) -> None:
        c = self.cell
        rect = pygame.Rect(self.origin[0] + x * c + 1, self.origin[1] + y * c + 1, c - 2, c - 2)
        color = lerp_color(BRICK_DARK, BRICK, hp / WALL_MAX_HP)
        pygame.draw.rect(surface, color, rect, border_radius=3)
        rows = 4
        for i in range(1, rows):
            yy = rect.y + i * rect.height // rows
            pygame.draw.line(surface, MORTAR, (rect.x, yy), (rect.right - 1, yy), 1)
        for i in range(rows):
            offset = rect.width // 4 if i % 2 else rect.width // 2
            top = rect.y + i * rect.height // rows
            pygame.draw.line(surface, MORTAR, (rect.x + offset, top), (rect.x + offset, top + rect.height // rows), 1)
        # Cracks show missing HP.
        for k in range(WALL_MAX_HP - hp):
            sx = rect.x + rect.width * (0.25 + 0.3 * k)
            pygame.draw.lines(surface, (40, 20, 16), False,
                              [(sx, rect.y + 3), (sx + c * 0.12, rect.centery), (sx - c * 0.05, rect.bottom - 3)], 2)

    def _draw_base(self, surface: pygame.Surface, x: int, y: int, player: int, hp: int) -> None:
        if hp <= 0:
            return
        cx, cy = self.to_pixels(x, y)
        c = self.cell
        color = PLAYER_COLORS[player]
        pygame.draw.circle(surface, PLAYER_DARK[player], (cx, cy), c * 0.44)
        pygame.draw.circle(surface, color, (cx, cy), c * 0.44, width=3)
        # Five-point star emblem.
        points = []
        for i in range(10):
            radius = c * 0.30 if i % 2 == 0 else c * 0.13
            angle = -math.pi / 2 + i * math.pi / 5
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)
        bar = pygame.Rect(0, 0, int(c * 0.8), 5)
        bar.midtop = (cx, cy + c * 0.40)
        draw_bar(surface, bar, hp / BASE_MAX_HP, color, (50, 30, 30))

    def draw_tank(self, surface: pygame.Surface, x: float, y: float, facing: Direction, player: int,
                  hp: int, scale: float = 1.0) -> None:
        cx, cy = self.to_pixels(x, y)
        c = self.cell * scale
        color, dark = PLAYER_COLORS[player], PLAYER_DARK[player]
        vertical = facing in (Direction.UP, Direction.DOWN)
        body_w, body_h = (c * 0.62, c * 0.70) if vertical else (c * 0.70, c * 0.62)
        body = pygame.Rect(0, 0, body_w, body_h)
        body.center = (cx, cy)
        # Tracks on both sides, parallel to the moving direction.
        if vertical:
            tracks = [pygame.Rect(body.x - c * 0.08, body.y - c * 0.04, c * 0.16, body_h + c * 0.08),
                      pygame.Rect(body.right - c * 0.08, body.y - c * 0.04, c * 0.16, body_h + c * 0.08)]
        else:
            tracks = [pygame.Rect(body.x - c * 0.04, body.y - c * 0.08, body_w + c * 0.08, c * 0.16),
                      pygame.Rect(body.x - c * 0.04, body.bottom - c * 0.08, body_w + c * 0.08, c * 0.16)]
        for track in tracks:
            pygame.draw.rect(surface, (34, 36, 42), track, border_radius=3)
        pygame.draw.rect(surface, dark, body, border_radius=int(c * 0.12))
        pygame.draw.rect(surface, color, body.inflate(-c * 0.12, -c * 0.12), border_radius=int(c * 0.1))
        end = (cx + facing.dx * c * 0.48, cy + facing.dy * c * 0.48)
        pygame.draw.line(surface, (40, 40, 46), (cx, cy), end, max(3, int(c * 0.13)))
        pygame.draw.line(surface, dark, (cx, cy), end, max(2, int(c * 0.08)))
        pygame.draw.circle(surface, dark, (cx, cy), c * 0.17)
        pygame.draw.circle(surface, color, (cx, cy), c * 0.11)
        if scale == 1.0:
            bar = pygame.Rect(0, 0, int(c * 0.8), 4)
            bar.midbottom = (cx, cy - c * 0.40)
            draw_bar(surface, bar, hp / TANK_MAX_HP, (250, 90, 90) if hp <= 2 else color, (50, 30, 30))

    def _draw_bullet(self, surface: pygame.Surface, cx: float, cy: float, owner: int) -> None:
        glow = pygame.Surface((self.cell, self.cell), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*PLAYER_COLORS[owner], 70), (self.cell // 2, self.cell // 2), self.cell * 0.22)
        surface.blit(glow, (cx - self.cell // 2, cy - self.cell // 2))
        pygame.draw.circle(surface, (255, 250, 230), (cx, cy), max(3, self.cell * 0.09))

    def _draw_trail_bullet(self, surface: pygame.Surface, cells, owner: int, progress: float) -> None:
        if len(cells) < 2:
            return
        position = progress * (len(cells) - 1)
        index = min(int(position), len(cells) - 2)
        t = position - index
        x = cells[index][0] + (cells[index + 1][0] - cells[index][0]) * t
        y = cells[index][1] + (cells[index + 1][1] - cells[index][1]) * t
        cx, cy = self.to_pixels(x, y)
        self._draw_bullet(surface, cx, cy, owner)

    # ------------------------------------------------------------------ particles
    def spawn_explosion(self, x: int, y: int, big: bool = False, color=(255, 170, 60)) -> None:
        cx, cy = self.to_pixels(x, y)
        for _ in range(40 if big else 16):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(40, 220 if big else 120)
            life = self.rng.uniform(0.3, 0.9 if big else 0.5)
            shade = lerp_color(color, (255, 240, 200), self.rng.random())
            self.particles.append(Particle(cx, cy, math.cos(angle) * speed, math.sin(angle) * speed,
                                           life, shade, self.rng.uniform(2, 6 if big else 4)))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.92
            p.vy *= 0.92
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]

    def _draw_particles(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            alpha = p.life / p.max_life
            pygame.draw.circle(surface, lerp_color((60, 40, 30), p.color, alpha), (p.x, p.y), max(1, p.size * alpha))
