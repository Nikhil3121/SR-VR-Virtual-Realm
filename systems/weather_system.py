"""
Weather overlay — rain streaks, fog layer, storm (rain + lightning + fog).
Procedural, lightweight (capped at ~250 active particles).
"""

import math
import random

import pygame

from core import constants as C
from core.utils import draw_rect_alpha


class WeatherSystem:
    MAX_RAIN = 220

    def __init__(self, settings):
        self.settings = settings
        self._drops: list = []
        self._fog_phase = 0.0
        self._lightning_t = 0.0
        self._next_lightning = random.uniform(4.0, 12.0)
        self._init_drops()

    def _init_drops(self):
        self._drops.clear()
        if self.settings.weather in (C.WEATHER_RAIN, C.WEATHER_STORM):
            count = self.MAX_RAIN if self.settings.weather == C.WEATHER_STORM else 150
            for _ in range(count):
                self._drops.append([
                    random.uniform(0, C.SCREEN_WIDTH),
                    random.uniform(0, C.SCREEN_HEIGHT),
                    random.uniform(540, 920),
                ])

    def reload(self):
        self._init_drops()

    def update(self, dt: float):
        if self.settings.weather == C.WEATHER_NONE:
            return
        if self.settings.weather in (C.WEATHER_RAIN, C.WEATHER_STORM):
            wind = 90 if self.settings.weather == C.WEATHER_RAIN else 180
            for d in self._drops:
                d[0] += wind * dt
                d[1] += d[2] * dt
                if d[1] > C.SCREEN_HEIGHT:
                    d[1] = -10
                    d[0] = random.uniform(-50, C.SCREEN_WIDTH)
                if d[0] > C.SCREEN_WIDTH + 50:
                    d[0] -= C.SCREEN_WIDTH + 100
        if self.settings.weather in (C.WEATHER_FOG, C.WEATHER_STORM):
            self._fog_phase += dt * 0.08
        if self.settings.weather == C.WEATHER_STORM:
            self._next_lightning -= dt
            if self._next_lightning <= 0:
                self._lightning_t = 0.18
                self._next_lightning = random.uniform(5.0, 14.0)
            self._lightning_t = max(0.0, self._lightning_t - dt)

    def draw_background(self, surface):
        """Fog layer goes behind enemies, painted on the webcam BG."""
        if self.settings.weather in (C.WEATHER_FOG, C.WEATHER_STORM):
            phase = self._fog_phase
            for i in range(4):
                y = int(120 + 140 * math.sin(phase + i * 0.7)) + i * 100
                draw_rect_alpha(surface, (200, 210, 220, 28),
                                (0, max(0, y), C.SCREEN_WIDTH, 120))

    def draw_foreground(self, surface):
        """Rain + lightning go on top of enemies for the immersive look."""
        if self.settings.weather in (C.WEATHER_RAIN, C.WEATHER_STORM):
            for d in self._drops:
                x, y, speed = d
                length = max(6, int(speed * 0.012))
                col = (180, 210, 240, 130) if self.settings.weather == C.WEATHER_RAIN \
                    else (170, 200, 235, 150)
                # Cheap line — pygame.draw.line doesn't support alpha; use small surface
                line_surf = pygame.Surface((4, length + 4), pygame.SRCALPHA)
                pygame.draw.line(line_surf, col, (2, 1), (2, length + 2), 1)
                surface.blit(line_surf, (int(x), int(y)))

        if self._lightning_t > 0:
            a = int(170 * (self._lightning_t / 0.18))
            draw_rect_alpha(surface, (255, 255, 255, a),
                            (0, 0, C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
