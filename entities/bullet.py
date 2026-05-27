"""
Bullets — projectile entity with trail rendering. Supports piercing.
"""

import math

import pygame

from core.utils import draw_circle_alpha, draw_line_glow_safe


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "damage", "color", "alive",
                 "life", "max_life", "trail", "_prev", "pierce_left",
                 "hit_ids")

    def __init__(self, x: float, y: float, angle: float, speed: float,
                 damage: float, color, pierce: int = 0):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.color = color
        self.alive = True
        self.max_life = 0.7
        self.life = self.max_life
        self.trail = []
        self._prev = (x, y)
        self.pierce_left = pierce
        self.hit_ids: set = set()

    def update(self, dt: float, screen_w: int, screen_h: int):
        self._prev = (self.x, self.y)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        if (self.life <= 0 or self.x < -50 or self.x > screen_w + 50
                or self.y < -50 or self.y > screen_h + 50):
            self.alive = False

    def register_hit(self, enemy_id: int) -> bool:
        """Returns True if this bullet should continue (still has pierces left).
        Returns False if the bullet should die."""
        self.hit_ids.add(enemy_id)
        if self.pierce_left > 0:
            self.pierce_left -= 1
            return True
        return False

    def draw(self, surface):
        if len(self.trail) >= 2:
            for i in range(1, len(self.trail)):
                a = int(40 + 180 * (i / len(self.trail)))
                draw_line_glow_safe(surface, (*self.color, a), self.trail[i - 1],
                                    self.trail[i], 2)
        draw_circle_alpha(surface, (*self.color, 240), (self.x, self.y), 4)
        draw_circle_alpha(surface, (255, 255, 255, 200), (self.x, self.y), 2)

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 3, int(self.y) - 3, 6, 6)
