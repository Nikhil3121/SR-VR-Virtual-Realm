"""Screen-level effects: shake, flash, slow-mo, hit-stop, bloom, vignette, etc."""

import math
import random
import time

import pygame

from core import constants as C
from core.utils import apply_bloom, clamp, draw_circle_alpha, draw_rect_alpha


class EffectsSystem:
    def __init__(self, settings):
        self.settings = settings
        self._shake_amount = 0.0
        self._shake_dir = (1.0, 0.0)         # unit vector — directional bias
        self._shake_dir_weight = 0.0          # 0 = isotropic, 1 = fully directional
        self._flash_color = (255, 0, 0)
        self._flash_t = 0.0
        self._slowmo_until = 0.0
        self._slowmo_factor = C.SLOWMO_FACTOR
        self._hit_stop_until = 0.0
        self._hit_marker_t = 0.0
        self._hit_marker_was_kill = False
        self.low_health_pulse = 0.0

        # Explosion lighting layer — list of (x, y, color, born_t, duration, radius)
        self._explosion_lights: list = []

        # Cinematic boss entrance
        self._boss_intro_until: float = 0.0
        self._boss_intro_duration: float = 0.0

        # Menu fade
        self._fade_t: float = 0.0          # counts up to MENU_FADE_TIME on transition
        self._fade_duration: float = 0.0

    def shake(self, amount: float):
        """Isotropic random shake."""
        self._shake_amount = min(60.0, self._shake_amount + amount)
        self._shake_dir_weight = max(self._shake_dir_weight * 0.7, 0.0)

    def directional_shake(self, amount: float, angle: float):
        """Shake biased toward a direction (e.g. recoil up = angle -pi/2)."""
        self._shake_amount = min(60.0, self._shake_amount + amount)
        self._shake_dir = (math.cos(angle), math.sin(angle))
        self._shake_dir_weight = 0.85

    def flash(self, color=(255, 30, 30), duration=C.DAMAGE_FLASH_TIME):
        self._flash_color = color
        self._flash_t = duration

    def slowmo(self, duration=C.SLOWMO_DURATION, factor: float = C.SLOWMO_FACTOR):
        self._slowmo_until = max(self._slowmo_until, time.time() + duration)
        self._slowmo_factor = min(self._slowmo_factor, factor)

    def hit_stop(self, duration: float = C.HIT_STOP_DURATION):
        self._hit_stop_until = max(self._hit_stop_until, time.time() + duration)

    def hit_marker(self, killed=False):
        self._hit_marker_t = 0.22
        self._hit_marker_was_kill = killed

    def explosion_light(self, x, y, color=(255, 180, 60),
                        duration: float = 0.32, radius: float = 260):
        """Adds a radial glow that lights up the scene briefly."""
        self._explosion_lights.append({
            "x": x, "y": y, "color": color,
            "born": time.time(), "duration": duration, "radius": radius,
        })
        # Cap so a chain of grenades never blows the buffer
        if len(self._explosion_lights) > 16:
            self._explosion_lights.pop(0)

    def boss_intro(self, duration: float = C.BOSS_ENTRANCE_SLOWMO):
        """Cinematic dim + slow-mo when a boss appears."""
        self._boss_intro_duration = duration
        self._boss_intro_until = time.time() + duration
        self.slowmo(duration, factor=0.20)
        self.shake(18)
        self.flash(color=(180, 40, 50), duration=0.22)

    def start_fade(self, duration: float = C.MENU_FADE_TIME):
        """Begin a fade-in for a state transition."""
        self._fade_duration = duration
        self._fade_t = duration

    def update(self, dt: float):
        self._shake_amount = max(0.0, self._shake_amount - C.SCREEN_SHAKE_DECAY * dt)
        self._shake_dir_weight = max(0.0, self._shake_dir_weight - 4 * dt)
        self._flash_t = max(0.0, self._flash_t - dt)
        self._hit_marker_t = max(0.0, self._hit_marker_t - dt)
        self._fade_t = max(0.0, self._fade_t - dt)
        # Drop expired explosion lights
        now = time.time()
        self._explosion_lights = [e for e in self._explosion_lights
                                   if (now - e["born"]) < e["duration"]]
        # Recover slowmo strength toward default after a slow segment ends
        if time.time() >= self._slowmo_until:
            self._slowmo_factor = min(1.0, self._slowmo_factor + dt * 2.0)
            if self._slowmo_factor > 0.99:
                self._slowmo_factor = C.SLOWMO_FACTOR

    @property
    def time_scale(self) -> float:
        now = time.time()
        if now < self._hit_stop_until:
            return 0.0
        if now < self._slowmo_until:
            return self._slowmo_factor
        return 1.0

    def shake_offset(self) -> tuple:
        if self._shake_amount < 0.1:
            return (0, 0)
        rx = random.uniform(-self._shake_amount, self._shake_amount)
        ry = random.uniform(-self._shake_amount, self._shake_amount)
        w = self._shake_dir_weight
        if w > 0:
            rx = rx * (1 - w) + self._shake_dir[0] * self._shake_amount * w
            ry = ry * (1 - w) + self._shake_dir[1] * self._shake_amount * w
        return (rx, ry)

    def draw_overlays(self, surface, low_health_intensity: float,
                      damage_dir, dt: float, slowmo_powerup_on: bool = False,
                      sniper_zoom: float = 0.0):
        w, h = surface.get_width(), surface.get_height()

        # Explosion lighting underlay — drawn first so it tints the whole frame
        self._draw_explosion_lights(surface)

        # Sniper zoom vignette (darken periphery + crosshair-centered circle)
        if sniper_zoom > 0.01:
            self._draw_sniper_zoom(surface, sniper_zoom)

        # Boss intro overlay (heavy dim + red rim)
        if time.time() < self._boss_intro_until:
            self._draw_boss_intro(surface)

        # Vignette
        self._draw_vignette(surface, low_health_intensity > 0)

        # Flash
        if self._flash_t > 0:
            a = int(160 * (self._flash_t / C.DAMAGE_FLASH_TIME))
            draw_rect_alpha(surface, (*self._flash_color, a), (0, 0, w, h))

        # Slow-mo tint
        if time.time() < self._slowmo_until or slowmo_powerup_on:
            draw_rect_alpha(surface, (40, 120, 220, 40), (0, 0, w, h))

        # Damage direction arc
        if damage_dir is not None:
            self._draw_damage_direction(surface, damage_dir)

        # Hit marker
        if self._hit_marker_t > 0:
            self._draw_hit_marker(surface, w // 2, h // 2)

        # Menu fade (drawn under bloom so it darkens the bloom too)
        if self._fade_t > 0:
            alpha = int(255 * (self._fade_t / max(0.01, self._fade_duration)))
            draw_rect_alpha(surface, (0, 0, 0, alpha), (0, 0, w, h))

        # Bloom — always last, additive
        if self.settings.bloom:
            apply_bloom(surface, strength=0.28)

    def _draw_explosion_lights(self, surface):
        now = time.time()
        for ex in self._explosion_lights:
            age = now - ex["born"]
            t = clamp(age / max(0.01, ex["duration"]), 0, 1)
            alpha = int(180 * (1.0 - t) ** 1.5)
            if alpha <= 4:
                continue
            r = int(ex["radius"] * (0.6 + 0.6 * t))
            col = ex["color"]
            draw_circle_alpha(surface, (*col, alpha // 2), (ex["x"], ex["y"]), r)
            draw_circle_alpha(surface, (*col, alpha), (ex["x"], ex["y"]), int(r * 0.55))
            pygame.draw.circle(surface, col, (int(ex["x"]), int(ex["y"])),
                               int(r * 1.05), 2)

    def _draw_sniper_zoom(self, surface, intensity: float):
        w, h = surface.get_width(), surface.get_height()
        # Darken peripheral area while keeping a soft circle in the middle clear
        alpha = int(C.SNIPER_ZOOM_DARKEN * intensity)
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        layer.fill((0, 0, 0, alpha))
        radius = int(min(w, h) * 0.32)
        pygame.draw.circle(layer, (0, 0, 0, 0), (w // 2, h // 2), radius)
        # Inner ring outline
        pygame.draw.circle(layer, (220, 240, 255, int(140 * intensity)),
                           (w // 2, h // 2), radius, 1)
        # Tactical crosshair lines
        pygame.draw.line(layer, (220, 240, 255, int(80 * intensity)),
                         (0, h // 2), (w, h // 2), 1)
        pygame.draw.line(layer, (220, 240, 255, int(80 * intensity)),
                         (w // 2, 0), (w // 2, h), 1)
        surface.blit(layer, (0, 0))

    def _draw_boss_intro(self, surface):
        remaining = self._boss_intro_until - time.time()
        if remaining <= 0 or self._boss_intro_duration <= 0:
            return
        t = 1.0 - (remaining / self._boss_intro_duration)
        # Pulse from full-dim to mostly-clear
        alpha = int(190 * (1.0 - t) ** 0.8)
        w, h = surface.get_width(), surface.get_height()
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        # Heavy bottom-up gradient via stacked rects
        for i in range(8):
            band_a = max(0, int(alpha * (1 - i / 8.0) * 0.5))
            layer.fill((20, 0, 8, band_a),
                        rect=(0, int(h * i / 8), w, int(h / 8) + 1))
        # Red rim
        pygame.draw.rect(layer, (255, 40, 60, int(alpha * 0.6)), (0, 0, w, 14))
        pygame.draw.rect(layer, (255, 40, 60, int(alpha * 0.6)), (0, h - 14, w, 14))
        surface.blit(layer, (0, 0))

    def _draw_vignette(self, surface, low_health: bool):
        w, h = surface.get_width(), surface.get_height()
        base_alpha = 110 if low_health else 70
        if low_health:
            self.low_health_pulse += 0.045
            pulse = (math.sin(self.low_health_pulse) + 1) * 0.5
            base_alpha = int(base_alpha + 50 * pulse)
        shape = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(shape, (0, 0, 0, base_alpha), (0, 0, w, h))
        pygame.draw.rect(shape, (0, 0, 0, 0), (40, 40, w - 80, h - 80),
                         border_radius=80)
        surface.blit(shape, (0, 0))
        if low_health:
            ring = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(ring, (255, 30, 40, 50), (0, 0, w, h))
            pygame.draw.rect(ring, (0, 0, 0, 0),
                             (40, 40, w - 80, h - 80), border_radius=120)
            surface.blit(ring, (0, 0))

    def _draw_damage_direction(self, surface, damage_dir):
        dx, dy, born = damage_dir
        age = time.time() - born
        if age > 1.2:
            return
        alpha = int(220 * (1.0 - age / 1.2))
        cx, cy = surface.get_width() // 2, surface.get_height() // 2
        radius = 120
        angle = math.atan2(dy, dx)
        sweep = 0.5
        pts = []
        for k in range(8):
            t = -sweep / 2 + (k / 7) * sweep
            ang = angle + t
            pts.append((cx + math.cos(ang) * radius, cy + math.sin(ang) * radius))
        for k in range(7, -1, -1):
            t = -sweep / 2 + (k / 7) * sweep
            ang = angle + t
            pts.append((cx + math.cos(ang) * (radius - 14),
                        cy + math.sin(ang) * (radius - 14)))
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(layer, (255, 60, 70, alpha), pts)
        surface.blit(layer, (0, 0))

    def _draw_hit_marker(self, surface, cx, cy):
        color = (255, 90, 90) if self._hit_marker_was_kill else (255, 230, 230)
        size = 14
        gap = 6
        thick = 3
        for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            start = (cx + sx * gap, cy + sy * gap)
            end = (cx + sx * (gap + size), cy + sy * (gap + size))
            pygame.draw.line(surface, color, start, end, thick)
