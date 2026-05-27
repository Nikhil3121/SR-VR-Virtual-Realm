"""Particle system — pooled with __slots__, capped at MAX_PARTICLES."""

import math
import random

import pygame

from core import constants as C
from core.utils import draw_circle_alpha


KIND_SPARK = 0
KIND_SMOKE = 1
KIND_BLOOD = 2
KIND_SHELL = 3
KIND_DEBRIS = 4
KIND_RING = 5
KIND_NUMBER = 6  # floating damage number


class Particle:
    __slots__ = ("kind", "x", "y", "vx", "vy", "life", "max_life",
                 "size", "color", "gravity", "fade", "text", "_font_cache")

    def __init__(self, kind, x, y, vx, vy, life, size, color,
                 gravity=0.0, fade=True, text=None):
        self.kind = kind
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity
        self.fade = fade
        self.text = text
        self._font_cache = None

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.gravity:
            self.vy += self.gravity * dt
        # Air drag
        self.vx *= (1 - dt * 1.2)
        self.vy *= (1 - dt * 1.2)
        self.life -= dt

    def alive(self) -> bool:
        return self.life > 0

    def alpha(self) -> int:
        if not self.fade:
            return 255
        return max(0, int(255 * (self.life / self.max_life)))

    def draw(self, surface, font_cache):
        a = self.alpha()
        if a <= 0:
            return
        if self.kind == KIND_NUMBER:
            # Floating damage number
            font = font_cache.get(int(self.size))
            if font is None:
                font = pygame.font.SysFont("consolas", int(self.size), bold=True)
                font_cache[int(self.size)] = font
            text_surf = font.render(self.text or "", True, self.color)
            text_surf.set_alpha(a)
            surface.blit(text_surf, (int(self.x), int(self.y)))
            return
        if self.kind == KIND_SPARK:
            draw_circle_alpha(surface, (*self.color, a), (self.x, self.y), self.size)
            draw_circle_alpha(surface, (255, 255, 255, min(255, a + 40)),
                              (self.x, self.y), max(1, self.size * 0.5))
            return
        if self.kind == KIND_SMOKE:
            r = self.size + (self.max_life - self.life) * 10
            draw_circle_alpha(surface, (*self.color, a // 3), (self.x, self.y), r)
            return
        if self.kind == KIND_BLOOD:
            draw_circle_alpha(surface, (*self.color, a), (self.x, self.y), self.size)
            return
        if self.kind == KIND_SHELL:
            # Tiny rotated rectangle (cheap fake)
            rect = pygame.Rect(int(self.x), int(self.y), 4, 8)
            pygame.draw.rect(surface, self.color, rect, border_radius=1)
            return
        if self.kind == KIND_DEBRIS:
            draw_circle_alpha(surface, (*self.color, a), (self.x, self.y), self.size)
            return
        if self.kind == KIND_RING:
            r = int(self.size + (self.max_life - self.life) * 120)
            pygame.draw.circle(surface, (*self.color, max(8, a // 2)),
                               (int(self.x), int(self.y)), r, 2)


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self._font_cache: dict = {}

    def update(self, dt: float):
        # In-place filter for perf
        kept = []
        for p in self.particles:
            p.update(dt)
            if p.alive():
                kept.append(p)
        # Cap
        if len(kept) > C.MAX_PARTICLES:
            kept = kept[-C.MAX_PARTICLES:]
        self.particles = kept

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface, self._font_cache)

    def spawn(self, p: Particle):
        self.particles.append(p)

    def spawn_muzzle_flash(self, x, y, angle, color):
        for _ in range(7):
            a = angle + random.uniform(-0.5, 0.5)
            speed = random.uniform(180, 420)
            self.spawn(Particle(KIND_SPARK, x, y,
                                math.cos(a) * speed, math.sin(a) * speed,
                                life=random.uniform(0.10, 0.20),
                                size=random.uniform(3, 6),
                                color=color, fade=True))
        # Soft smoke puff
        for _ in range(3):
            a = angle + random.uniform(-0.9, 0.9)
            speed = random.uniform(40, 100)
            self.spawn(Particle(KIND_SMOKE, x, y,
                                math.cos(a) * speed, math.sin(a) * speed - 20,
                                life=random.uniform(0.4, 0.8),
                                size=10, color=(180, 180, 180), gravity=-30))

    def spawn_shell(self, x, y, angle):
        for _ in range(1):
            base = angle + math.pi / 2 + random.uniform(-0.4, 0.4)
            speed = random.uniform(160, 240)
            self.spawn(Particle(KIND_SHELL, x, y,
                                math.cos(base) * speed, math.sin(base) * speed - 120,
                                life=0.8, size=4, color=(230, 200, 90),
                                gravity=900, fade=False))

    def spawn_blood(self, x, y, intensity=1.0):
        n = int(8 * intensity)
        for _ in range(n):
            a = random.uniform(0, math.tau)
            speed = random.uniform(80, 260) * intensity
            self.spawn(Particle(KIND_BLOOD, x, y,
                                math.cos(a) * speed, math.sin(a) * speed,
                                life=random.uniform(0.35, 0.7),
                                size=random.uniform(3, 6),
                                color=(150, 20, 25), gravity=400))

    def spawn_hit_spark(self, x, y):
        for _ in range(5):
            a = random.uniform(0, math.tau)
            speed = random.uniform(120, 300)
            self.spawn(Particle(KIND_SPARK, x, y,
                                math.cos(a) * speed, math.sin(a) * speed,
                                life=random.uniform(0.10, 0.20),
                                size=random.uniform(2, 4),
                                color=(255, 230, 120)))

    def spawn_explosion(self, x, y, color=(255, 140, 40), big=False):
        n = 28 if big else 14
        for _ in range(n):
            a = random.uniform(0, math.tau)
            speed = random.uniform(150, 520 if big else 320)
            self.spawn(Particle(KIND_SPARK, x, y,
                                math.cos(a) * speed, math.sin(a) * speed,
                                life=random.uniform(0.25, 0.55),
                                size=random.uniform(3, 7), color=color))
        for _ in range(8 if big else 4):
            a = random.uniform(0, math.tau)
            speed = random.uniform(40, 140)
            self.spawn(Particle(KIND_SMOKE, x, y,
                                math.cos(a) * speed, math.sin(a) * speed,
                                life=random.uniform(0.6, 1.2),
                                size=18, color=(70, 70, 80), gravity=-40))
        self.spawn(Particle(KIND_RING, x, y, 0, 0, life=0.35, size=8,
                            color=color, fade=True))

    def spawn_damage_number(self, x, y, amount: int, headshot=False,
                            is_crit: bool = False):
        if is_crit:
            color = (255, 215, 60)
            size = 34
            text = f"{amount} CRIT!"
        elif headshot:
            color = (255, 90, 90)
            size = 30
            text = f"{amount}!"
        else:
            color = (255, 220, 70)
            size = 22
            text = f"{amount}"
        self.spawn(Particle(KIND_NUMBER, x, y,
                            random.uniform(-20, 20), -120,
                            life=0.9 if is_crit else 0.8,
                            size=size, color=color, text=text))

    def spawn_explosion_light(self, x, y, color=(255, 180, 60),
                              radius: float = 260, duration: float = 0.3):
        """Big radial glow ring that fades out — simulates explosion lighting
        across the scene."""
        self.spawn(Particle(KIND_RING, x, y, 0, 0, life=duration,
                            size=int(radius * 0.35), color=color, fade=True))
        # An inner bright flash
        self.spawn(Particle(KIND_SPARK, x, y, 0, 0, life=duration * 0.5,
                            size=radius * 0.4, color=color))
