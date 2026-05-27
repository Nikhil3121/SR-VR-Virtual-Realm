"""
Pickup entity — power-up that drops from a dead enemy.
"""

import math
import random

import pygame

from core import constants as C
from core.utils import draw_circle_alpha, draw_glow_circle, draw_text


class Pickup:
    __slots__ = ("kind", "x", "y", "spawn_t", "life", "_anim_t",
                 "_vy", "alive", "collected", "_letter")

    def __init__(self, kind: str, x: float, y: float):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.spawn_t = 0.0
        self.life = C.PICKUP_LIFETIME
        self._anim_t = random.uniform(0, math.tau)
        # Tiny pop on spawn
        self._vy = -90.0
        self.alive = True
        self.collected = False
        self._letter = {
            C.PICKUP_HEALTH: "+",
            C.PICKUP_ARMOR: "A",
            C.PICKUP_AMMO: "B",
            C.PICKUP_SHIELD: "S",
            C.PICKUP_DOUBLE_DAMAGE: "2x",
            C.PICKUP_SLOWMO: "T",
            C.PICKUP_FIRE_RATE: "R",
        }.get(kind, "?")

    def update(self, dt: float):
        self._anim_t += dt
        self.spawn_t += dt
        # Tiny upward arc then settle
        self.y += self._vy * dt
        self._vy = min(0.0, self._vy + 220 * dt)
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    @property
    def expiring_soon(self) -> bool:
        return self.life <= 3.0

    def color(self) -> tuple:
        return C.PICKUP_DEFINITIONS[self.kind]["color"]

    def label(self) -> str:
        return C.PICKUP_DEFINITIONS[self.kind]["label"]

    def draw(self, surface, font):
        # Blink when about to expire
        if self.expiring_soon and (int(self._anim_t * 8) % 2 == 0):
            return

        color = self.color()
        bob = math.sin(self._anim_t * 3.0) * 5
        cx = int(self.x)
        cy = int(self.y + bob)

        draw_glow_circle(surface, color, (cx, cy), 16, layers=4, alpha=180)
        pygame.draw.circle(surface, color, (cx, cy), 16)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 16, 2)
        # Letter inside
        if font is not None:
            txt = font.render(self._letter, True, (10, 14, 20))
            r = txt.get_rect(center=(cx, cy))
            surface.blit(txt, r)
        # Small floating label below
        if font is not None:
            small = font.render(self.label(), True, (240, 240, 240))
            r = small.get_rect(center=(cx, cy + 28))
            bg = pygame.Surface((r.width + 8, r.height + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            surface.blit(bg, (r.x - 4, r.y - 1))
            surface.blit(small, r)
