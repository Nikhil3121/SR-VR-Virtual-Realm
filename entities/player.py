"""
Player state — health, armor, ammo wallet, score/combo, weapon switching.
Tracks active power-ups + per-weapon recoil curve + animated UI display values.
"""

import math
import random
import time

from core import constants as C
from core.utils import clamp, tween


class Player:
    def __init__(self, weapons: list, settings):
        self.weapons = weapons
        self.weapon_index = 0
        self.settings = settings

        self.max_health = C.PLAYER_MAX_HEALTH
        self.health = float(self.max_health)
        self.max_armor = C.PLAYER_MAX_ARMOR
        self.armor = 50.0

        self.aim_x = C.SCREEN_WIDTH / 2
        self.aim_y = C.SCREEN_HEIGHT / 2
        # 2D recoil: vertical kick up, horizontal drift (left/right alternating)
        self.recoil_y = 0.0
        self.recoil_x = 0.0
        self.view_kick_y = 0.0     # screen-shake-like camera kick on fire
        self.view_kick_x = 0.0
        self._recoil_h_sign = 1     # alternates each shot for "spray pattern" feel
        self.bob_phase = 0.0

        # Smoothed display values for animated UI numbers
        self.display_health = float(self.health)
        self.display_armor = float(self.armor)
        self.display_score = 0.0
        self.display_coins = 0.0

        self.score = 0
        self.coins = 0
        self.kills = 0
        self.headshots = 0
        self.combo = 0
        self.killstreak = 0
        self._last_kill_time = 0.0
        self._invuln_until = 0.0

        # Multi-kill tracking
        self.multi_kill_count = 0
        self._multi_kill_window_end = 0.0
        self.last_multi_kill_tier = 0  # for callouts

        # Active power-up effects: each maps to a timestamp until which it's active.
        self._effects: dict = {}

        # Direction of most-recent damage (for indicator). dx, dy normalized.
        self.last_damage_dir = None

    @property
    def weapon(self):
        return self.weapons[self.weapon_index]

    def switch_weapon(self, index: int, unlocked: set) -> bool:
        if index < 0 or index >= len(self.weapons):
            return False
        if index not in unlocked:
            return False
        if index == self.weapon_index:
            return False
        self.weapons[self.weapon_index].cancel_reload()
        self.weapon_index = index
        return True

    def next_weapon(self, unlocked: set):
        n = len(self.weapons)
        for step in range(1, n):
            idx = (self.weapon_index + step) % n
            if idx in unlocked:
                self.switch_weapon(idx, unlocked)
                return

    def take_damage(self, dmg: float, source_pos=None) -> bool:
        if time.time() < self._invuln_until:
            return False
        # Shield power-up absorbs all damage
        if self.is_effect_active(C.PICKUP_SHIELD):
            return False
        if self.armor > 0:
            absorbed = min(self.armor, dmg * 0.6)
            self.armor -= absorbed
            dmg -= absorbed
        self.health = max(0.0, self.health - dmg)
        self._invuln_until = time.time() + C.PLAYER_INVULN_TIME
        self.combo = 0
        self.killstreak = 0
        # Compute damage direction from source
        if source_pos is not None:
            dx = source_pos[0] - C.SCREEN_WIDTH / 2
            dy = source_pos[1] - C.SCREEN_HEIGHT / 2
            mag = math.hypot(dx, dy)
            if mag > 1e-3:
                self.last_damage_dir = (dx / mag, dy / mag, time.time())
        return True

    def damage_multiplier(self) -> float:
        return 2.0 if self.is_effect_active(C.PICKUP_DOUBLE_DAMAGE) else 1.0

    def add_score(self, base: int, headshot=False) -> int:
        mult = 1.0 + self.killstreak * C.KILLSTREAK_MULTIPLIER_STEP
        if headshot:
            mult *= C.HEADSHOT_BONUS
        gained = int(base * mult)
        self.score += gained
        return gained

    def register_kill(self, headshot=False) -> int:
        now = time.time()
        if (now - self._last_kill_time) < C.COMBO_DECAY_TIME:
            self.combo += 1
        else:
            self.combo = 1
        self.killstreak += 1
        self._last_kill_time = now
        self.kills += 1
        if headshot:
            self.headshots += 1
        self.coins += C.COIN_PER_KILL

        # Multi-kill window
        if now < self._multi_kill_window_end:
            self.multi_kill_count += 1
        else:
            self.multi_kill_count = 1
        self._multi_kill_window_end = now + C.MULTI_KILL_WINDOW
        # Highest tier the multi-kill has reached so far
        for threshold in sorted(C.MULTI_KILL_TIERS.keys()):
            if self.multi_kill_count >= threshold:
                self.last_multi_kill_tier = threshold
        return self.combo

    def consume_multi_kill_callout(self) -> str | None:
        """Returns the tier label to announce, or None. Self-clears."""
        if self.last_multi_kill_tier <= 0:
            return None
        tier = self.last_multi_kill_tier
        # Reset to 0 so we only announce once per crossed threshold
        self.last_multi_kill_tier = 0
        return C.MULTI_KILL_TIERS.get(tier)

    def heal(self, amount: float):
        self.health = min(self.max_health, self.health + amount)

    def heal_full(self):
        self.health = self.max_health

    def add_armor(self, amount: float):
        self.armor = min(self.max_armor, self.armor + amount)

    def armor_full(self):
        self.armor = self.max_armor

    def increase_max_health(self, amount: int):
        self.max_health += amount
        self.health += amount

    def increase_max_armor(self, amount: int):
        self.max_armor += amount
        self.armor += amount

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

    @property
    def is_low_health(self) -> bool:
        return self.health <= C.PLAYER_LOW_HEALTH

    @property
    def low_health_intensity(self) -> float:
        if not self.is_low_health:
            return 0.0
        return clamp(1.0 - (self.health / C.PLAYER_LOW_HEALTH), 0.2, 1.0)

    def apply_pickup(self, kind: str) -> str:
        """Applies the pickup's effect immediately and/or starts a timed buff.
        Returns the label string to feed into the UI / announcer."""
        defn = C.PICKUP_DEFINITIONS.get(kind)
        if defn is None:
            return ""
        if kind == C.PICKUP_HEALTH:
            self.heal(25)
            return defn["label"]
        if kind == C.PICKUP_ARMOR:
            self.add_armor(30)
            return defn["label"]
        if kind == C.PICKUP_AMMO:
            for w in self.weapons:
                w.add_reserve(w.cfg["reserve"] // 2)
            return defn["label"]
        # Timed buffs
        duration = defn["duration"]
        self._effects[kind] = time.time() + duration
        return defn["label"]

    def is_effect_active(self, kind: str) -> bool:
        end = self._effects.get(kind)
        return end is not None and time.time() < end

    def active_effects(self) -> dict:
        now = time.time()
        return {k: end - now for k, end in self._effects.items() if end > now}

    def fire_rate_multiplier(self) -> float:
        return 1.6 if self.is_effect_active(C.PICKUP_FIRE_RATE) else 1.0

    def update(self, dt: float):
        if (time.time() - self._last_kill_time) > C.COMBO_DECAY_TIME:
            self.combo = 0
        if time.time() > self._multi_kill_window_end:
            self.multi_kill_count = 0

        # Per-weapon recoil recovery (decays back to zero over time)
        recovery = self.weapon.recoil_pattern["recovery"]
        self.recoil_y = max(0.0, self.recoil_y - recovery * 8 * dt)
        # Horizontal drift swings back through zero (damped)
        self.recoil_x *= max(0.0, 1.0 - 6 * dt)
        self.view_kick_y = max(0.0, self.view_kick_y - recovery * 10 * dt)
        self.view_kick_x *= max(0.0, 1.0 - 8 * dt)

        self.bob_phase += dt
        if self.last_damage_dir and time.time() - self.last_damage_dir[2] > 1.2:
            self.last_damage_dir = None

        # Animated display values for HUD
        self.display_health = tween(self.display_health, self.health,
                                     C.UI_TWEEN_RATE, dt)
        self.display_armor = tween(self.display_armor, self.armor,
                                    C.UI_TWEEN_RATE, dt)
        self.display_score = tween(self.display_score, self.score,
                                    C.UI_TWEEN_RATE * 0.8, dt)
        self.display_coins = tween(self.display_coins, self.coins,
                                    C.UI_TWEEN_RATE * 0.8, dt)

        # Compose weapon mods = persistent shop multipliers * timed power-up boosts.
        rapid = self.is_effect_active(C.PICKUP_FIRE_RATE)
        ddmg = self.is_effect_active(C.PICKUP_DOUBLE_DAMAGE)
        for w in self.weapons:
            base_dmg = getattr(w, "_shop_dmg_mul", 1.0)
            base_fr = getattr(w, "_shop_fire_rate_mul", 1.0)
            base_rl = getattr(w, "_shop_reload_mul", 1.0)
            w.damage_mul = base_dmg * (2.0 if ddmg else 1.0)
            w.fire_rate_mul = base_fr * (1.6 if rapid else 1.0)
            w.reload_mul = base_rl
            w.update()

    def bob_offset(self) -> tuple:
        """Idle breathing sway — slower & more organic than constant sine."""
        return (math.sin(self.bob_phase * 1.1) * C.WEAPON_SWAY_AMPLITUDE * 0.45
                + math.sin(self.bob_phase * 0.43) * 2.0,
                math.cos(self.bob_phase * 1.5) * 2.6
                + math.sin(self.bob_phase * 0.32) * 1.4)

    def reload_dip(self) -> float:
        """0..1 dip animation during reload — ease-in-out so the gun smoothly
        drops and recovers."""
        w = self.weapon
        if not w.is_reloading:
            return 0.0
        p = w.reload_progress
        # bell curve peaking at progress=0.5
        return math.sin(p * math.pi)

    def apply_recoil(self, weapon=None):
        """Apply a recoil impulse using the active weapon's recoil pattern.
        - Vertical: pushes gun up
        - Horizontal: drift alternates left/right each shot (spray pattern)
        - View kick: pushes the HUD/world view briefly
        """
        if weapon is None:
            weapon = self.weapon
        pattern = weapon.recoil_pattern
        v_kick = pattern["v"]
        h_drift = pattern["h"]
        view = pattern["view_kick"]
        self.recoil_y = clamp(self.recoil_y + v_kick, 0.0, 60.0)
        # Alternate sign + slight randomness for organic spray
        self._recoil_h_sign *= -1
        self.recoil_x += self._recoil_h_sign * (h_drift + random.uniform(-0.5, 0.5))
        self.recoil_x = clamp(self.recoil_x, -20.0, 20.0)
        self.view_kick_y = clamp(self.view_kick_y + view * 0.35, 0.0, 28.0)
        self.view_kick_x += self._recoil_h_sign * view * 0.18

    def view_offset(self) -> tuple:
        """Camera offset to apply to the rendered world layer (recoil push)."""
        return (self.view_kick_x, -self.view_kick_y)
