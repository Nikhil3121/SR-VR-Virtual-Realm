"""
Enemy projectile — slower, glowing red orb that homes (slightly) toward player.
"""

import math

import pygame

from core.utils import draw_circle_alpha, draw_line_glow_safe


class EnemyBullet:
    __slots__ = ("x", "y", "vx", "vy", "damage", "alive", "life",
                 "max_life", "trail", "_homing", "_anim_t")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 damage: float, homing: bool = False):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.alive = True
        self.max_life = 2.5
        self.life = self.max_life
        self.trail = []
        self._homing = homing
        self._anim_t = 0.0

    def update(self, dt: float, target):
        self._anim_t += dt
        # Mild homing — turn velocity toward target each frame
        if self._homing and target is not None:
            tx, ty = target
            dx = tx - self.x
            dy = ty - self.y
            d = math.hypot(dx, dy) + 1e-6
            tvx = (dx / d) * math.hypot(self.vx, self.vy)
            tvy = (dy / d) * math.hypot(self.vx, self.vy)
            blend = 0.6 * dt
            self.vx = self.vx * (1 - blend) + tvx * blend
            self.vy = self.vy * (1 - blend) + tvy * blend

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def hit_test_target_box(self, target_rect: pygame.Rect) -> bool:
        return target_rect.collidepoint(int(self.x), int(self.y))

    def draw(self, surface):
        if len(self.trail) >= 2:
            for i in range(1, len(self.trail)):
                a = int(40 + 160 * (i / len(self.trail)))
                draw_line_glow_safe(surface, (255, 70, 80, a),
                                    self.trail[i - 1], self.trail[i], 2)
        draw_circle_alpha(surface, (255, 60, 70, 200), (self.x, self.y), 7)
        draw_circle_alpha(surface, (255, 240, 240, 220), (self.x, self.y), 3)
