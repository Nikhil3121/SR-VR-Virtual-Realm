"""
Weapon classes. Encapsulates ammo, fire-rate gating, reload state, recoil.
"""

import math
import random
import time

import pygame

from core import constants as C
from core.utils import clamp, draw_circle_alpha


class Weapon:
    """A weapon with state. Stateless config comes from constants."""

    def __init__(self, config: dict):
        self.cfg = config
        self.name: str = config["name"]
        self.kind: str = config["kind"]
        self.damage: float = config["damage"]
        self.fire_rate: float = config["fire_rate"]
        self.magazine_size: int = config["magazine"]
        self.reserve: int = config["reserve"]
        self.reload_time: float = config["reload_time"]
        self.recoil: float = config["recoil"]
        self.spread: float = config["spread"]
        self.bullet_speed: float = config["bullet_speed"]
        self.bullets_per_shot: int = config["bullets_per_shot"]
        self.muzzle_color = config["muzzle_color"]
        self.trail_color = config["trail_color"]
        self.pierce: int = config.get("pierce", 0)

        self.ammo: int = self.magazine_size
        self._last_shot_time: float = 0.0
        self._reload_start: float | None = None

        # Run-time modifiers (shop upgrades)
        self.damage_mul: float = 1.0
        self.fire_rate_mul: float = 1.0
        self.reload_mul: float = 1.0

    @property
    def effective_damage(self) -> float:
        return self.damage * self.damage_mul

    @property
    def effective_fire_rate(self) -> float:
        return self.fire_rate * self.fire_rate_mul

    @property
    def effective_reload_time(self) -> float:
        return self.reload_time * self.reload_mul

    @property
    def recoil_pattern(self) -> dict:
        """Per-weapon recoil curve (vertical kick + horizontal drift + recovery)."""
        return C.WEAPON_RECOIL_PATTERN.get(self.kind,
                                          C.WEAPON_RECOIL_PATTERN["pistol"])

    @property
    def is_reloading(self) -> bool:
        return self._reload_start is not None

    @property
    def reload_progress(self) -> float:
        if not self.is_reloading:
            return 1.0
        return clamp((time.time() - self._reload_start) / self.effective_reload_time,
                     0.0, 1.0)

    def can_shoot(self) -> bool:
        if self.is_reloading or self.ammo <= 0:
            return False
        return (time.time() - self._last_shot_time) >= (1.0 / self.effective_fire_rate)

    def shoot(self) -> bool:
        if not self.can_shoot():
            return False
        self.ammo -= 1
        self._last_shot_time = time.time()
        if self.ammo == 0 and self.reserve > 0:
            self.start_reload()
        return True

    def start_reload(self) -> bool:
        if self.is_reloading or self.ammo == self.magazine_size or self.reserve <= 0:
            return False
        self._reload_start = time.time()
        return True

    def update(self):
        if self._reload_start is not None:
            if (time.time() - self._reload_start) >= self.effective_reload_time:
                needed = self.magazine_size - self.ammo
                taken = min(needed, self.reserve)
                self.ammo += taken
                self.reserve -= taken
                self._reload_start = None

    def cancel_reload(self):
        self._reload_start = None

    def add_reserve(self, amount: int):
        self.reserve += amount

    def refill_full(self):
        self.ammo = self.magazine_size
        self.reserve = self.cfg["reserve"]

    def draw_first_person(self, surface, recoil_y: float, recoil_x: float,
                          bob_offset: tuple, reload_dip: float = 0.0,
                          tilt: float = 0.0):
        """Procedural first-person gun render.
        - recoil_y / recoil_x — view kick offsets in px
        - bob_offset — idle breathing sway (px, px)
        - reload_dip — 0..1 dip animation during reload
        - tilt — radians of side tilt (unused currently, kept for future)
        """
        w, h = surface.get_width(), surface.get_height()
        # During reload the gun dips downward and slightly off-center
        dip_y = int(reload_dip * C.RELOAD_DIP_DEPTH)
        dip_x = int(math.sin(reload_dip * math.pi * 2) * 6)
        base_x = w - 240 + int(bob_offset[0]) + int(recoil_x) + dip_x
        base_y = (h - 110 + int(bob_offset[1]) - int(recoil_y) + dip_y)

        draw_circle_alpha(surface, (0, 0, 0, 110), (base_x + 60, h - 24), 110)

        if self.kind == "pistol":
            self._draw_pistol(surface, base_x, base_y)
        elif self.kind == "rifle":
            self._draw_rifle(surface, base_x, base_y)
        elif self.kind == "shotgun":
            self._draw_shotgun(surface, base_x, base_y)
        elif self.kind == "sniper":
            self._draw_sniper(surface, base_x, base_y)

    def _draw_pistol(self, surf, x, y):
        body = (40, 44, 52)
        slide = (60, 66, 78)
        accent = self.muzzle_color
        pygame.draw.rect(surf, body, (x, y + 30, 160, 40), border_radius=6)
        pygame.draw.rect(surf, slide, (x + 20, y + 10, 130, 30), border_radius=4)
        pygame.draw.rect(surf, body, (x + 60, y + 60, 30, 90), border_radius=4)
        pygame.draw.rect(surf, accent, (x + 145, y + 22, 8, 6))
        pygame.draw.line(surf, (180, 190, 200), (x + 30, y + 18), (x + 140, y + 18), 2)

    def _draw_rifle(self, surf, x, y):
        body = (30, 34, 40)
        wood = (95, 60, 35)
        pygame.draw.rect(surf, body, (x - 30, y + 30, 260, 26), border_radius=4)
        pygame.draw.rect(surf, body, (x + 60, y + 56, 60, 50), border_radius=4)
        pygame.draw.polygon(surf, wood, [(x - 30, y + 56), (x - 30, y + 90),
                                          (x + 80, y + 90), (x + 80, y + 56)])
        pygame.draw.rect(surf, (50, 56, 64), (x + 180, y + 18, 40, 50), border_radius=3)
        pygame.draw.rect(surf, self.muzzle_color, (x + 220, y + 34, 16, 18))
        for i in range(5):
            pygame.draw.line(surf, (140, 145, 155), (x + 40 + i * 30, y + 24),
                             (x + 50 + i * 30, y + 24), 2)

    def _draw_shotgun(self, surf, x, y):
        body = (45, 32, 28)
        metal = (70, 76, 82)
        pygame.draw.rect(surf, metal, (x - 40, y + 30, 290, 24), border_radius=4)
        pygame.draw.rect(surf, metal, (x - 40, y + 50, 290, 14), border_radius=3)
        pygame.draw.rect(surf, body, (x + 50, y + 64, 80, 50), border_radius=5)
        pygame.draw.polygon(surf, body, [(x + 130, y + 56), (x + 240, y + 56),
                                          (x + 220, y + 110), (x + 130, y + 110)])
        pygame.draw.rect(surf, self.muzzle_color, (x + 240, y + 32, 18, 22))

    def _draw_sniper(self, surf, x, y):
        body = (28, 32, 38)
        metal = (60, 66, 76)
        pygame.draw.rect(surf, body, (x - 60, y + 32, 340, 20), border_radius=4)
        pygame.draw.rect(surf, body, (x + 60, y + 60, 80, 50), border_radius=4)
        pygame.draw.rect(surf, metal, (x + 30, y + 12, 180, 24), border_radius=10)
        pygame.draw.circle(surf, self.muzzle_color, (x + 220, y + 24), 8)
        pygame.draw.rect(surf, self.muzzle_color, (x + 270, y + 36, 18, 12))


def build_loadout() -> list:
    return [Weapon(cfg) for cfg in C.WEAPONS]


def spread_angle(base_angle: float, spread: float) -> float:
    return base_angle + random.uniform(-spread, spread)


def angle_to_target(origin, target) -> float:
    return math.atan2(target[1] - origin[1], target[0] - origin[0])
