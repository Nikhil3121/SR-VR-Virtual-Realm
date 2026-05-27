"""Pickup manager — drops, lifetime, crosshair-radius collection."""

import random

import pygame

from core import constants as C
from entities.pickup import Pickup


class PickupSystem:
    def __init__(self, audio):
        self.audio = audio
        self.pickups: list[Pickup] = []
        self._weights = self._build_weight_table()
        self._font = None  # lazy

    def _build_weight_table(self):
        table = []
        for kind, defn in C.PICKUP_DEFINITIONS.items():
            table.extend([kind] * int(defn["drop_weight"]))
        return table

    def maybe_drop(self, x: float, y: float, is_boss: bool = False):
        if is_boss:
            for _ in range(C.PICKUP_BOSS_DROPS):
                kind = random.choice(self._weights)
                jitter = (random.uniform(-50, 50), random.uniform(-50, 50))
                self.pickups.append(Pickup(kind, x + jitter[0], y + jitter[1]))
            return
        if random.random() <= C.PICKUP_DROP_CHANCE:
            kind = random.choice(self._weights)
            self.pickups.append(Pickup(kind, x, y))

    def force_drop(self, kind: str, x: float, y: float):
        self.pickups.append(Pickup(kind, x, y))

    def update(self, dt: float, player_aim, player, on_collect):
        for p in self.pickups:
            p.update(dt)
        # Collect when crosshair within radius
        ax, ay = player_aim
        kept = []
        for p in self.pickups:
            if not p.alive:
                continue
            dx = p.x - ax
            dy = p.y - ay
            if (dx * dx + dy * dy) <= C.PICKUP_COLLECT_RADIUS ** 2:
                label = player.apply_pickup(p.kind)
                self.audio.play("powerup" if p.kind != C.PICKUP_AMMO else "ammo_pickup",
                                volume=0.9)
                p.collected = True
                p.alive = False
                on_collect(p.kind, label)
                continue
            kept.append(p)
        self.pickups = kept

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 14, bold=True)
        for p in self.pickups:
            p.draw(surface, self._font)

    def clear(self):
        self.pickups.clear()
