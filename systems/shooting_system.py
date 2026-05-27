"""Shooting system — bullets, fire/grenade/special, collision, crits, knockback."""

import math
import random

from core import constants as C
from core.utils import angle_between, distance
from entities.bullet import Bullet
from entities.weapons import spread_angle


class ShootingSystem:
    def __init__(self, particles, effects, audio):
        self.particles = particles
        self.effects = effects
        self.audio = audio
        self.bullets: list[Bullet] = []
        self.muzzle_origin = (C.SCREEN_WIDTH - 170, C.SCREEN_HEIGHT - 110)

    def try_fire(self, player, target_pos, enemies, on_fire=None) -> bool:
        weapon = player.weapon
        if not weapon.shoot():
            return False
        aim = self._apply_aim_assist(target_pos, enemies,
                                     strength=player.settings.aim_assist)
        origin = self._muzzle_position_for(weapon, player)
        base_angle = angle_between(origin, aim)

        for _ in range(weapon.bullets_per_shot):
            angle = spread_angle(base_angle, weapon.spread)
            self.bullets.append(Bullet(
                origin[0], origin[1], angle,
                weapon.bullet_speed, weapon.effective_damage,
                weapon.trail_color, pierce=weapon.pierce,
            ))

        self.particles.spawn_muzzle_flash(origin[0], origin[1], base_angle,
                                          weapon.muzzle_color)
        self.particles.spawn_shell(origin[0] - 10, origin[1] - 18, base_angle)
        # Directional shake biased toward recoil
        self.effects.directional_shake(weapon.recoil * 0.55, angle=-math.pi / 2)
        # New 2D recoil + per-weapon pattern
        player.apply_recoil(weapon)
        self.audio.play_shoot(weapon.kind)
        if on_fire is not None:
            on_fire(weapon)
        return True

    def reload(self, player) -> bool:
        if player.weapon.start_reload():
            self.audio.play_reload(player.weapon.kind)
            return True
        return False

    def grenade(self, player, target_pos, enemies) -> int:
        x, y = target_pos
        self.particles.spawn_explosion(x, y, color=(255, 140, 40), big=True)
        self.effects.shake(18)
        self.effects.flash(color=(255, 180, 60), duration=0.18)
        self.effects.explosion_light(x, y, color=(255, 180, 60), duration=0.32,
                                      radius=260)
        self.audio.play_at("explosion", x)
        self.audio.play("bass_thump", volume=0.85)
        radius = 180
        killed_total = 0
        for enemy in enemies:
            if not enemy.alive:
                continue
            d = distance((enemy.x, enemy.y), (x, y))
            if d <= radius:
                # Push enemy outward from blast
                dx = enemy.x - x
                dy = enemy.y - y
                if d > 1e-3:
                    nx, ny = dx / d, dy / d
                else:
                    a = random.uniform(0, math.tau)
                    nx, ny = math.cos(a), math.sin(a)
                took, head, killed = enemy.damage_at(
                    (enemy.x, enemy.y), 240, hit_dir=(nx, ny))
                if killed:
                    killed_total += 1
        return killed_total

    def special(self, player, target_pos, enemies) -> int:
        cx, cy = target_pos
        self.particles.spawn_explosion(cx, cy, color=(120, 200, 255), big=True)
        self.particles.spawn(self._mk_big_ring(cx, cy))
        self.effects.shake(26)
        self.effects.flash(color=(120, 200, 255), duration=0.22)
        self.effects.slowmo(0.55)
        self.effects.explosion_light(cx, cy, color=(120, 200, 255),
                                      duration=0.45, radius=420)
        self.audio.play("explosion", volume=1.1)
        self.audio.play("bass_thump", volume=1.0)
        killed_total = 0
        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - cx
            dy = enemy.y - cy
            d = math.hypot(dx, dy) + 1e-6
            enemy.damage_at((enemy.x, enemy.y), 320,
                            hit_dir=(dx / d, dy / d))
            if not enemy.alive:
                killed_total += 1
        return killed_total

    def update(self, dt: float, enemies, player, on_hit, on_kill,
               headshot_only: bool = False):
        for b in self.bullets:
            b.update(dt, C.SCREEN_WIDTH, C.SCREEN_HEIGHT)

        for b in self.bullets:
            if not b.alive:
                continue
            for enemy in enemies:
                if not enemy.alive:
                    continue
                eid = id(enemy)
                if eid in b.hit_ids:
                    continue

                # Critical hit roll — small chance for big damage
                is_crit = random.random() < C.CRIT_CHANCE

                # Hit direction (bullet velocity, normalized)
                v_mag = math.hypot(b.vx, b.vy) + 1e-6
                hit_dir = (b.vx / v_mag, b.vy / v_mag)

                took, head, killed = enemy.damage_at(
                    (b.x, b.y), b.damage,
                    headshot_only=headshot_only,
                    hit_dir=hit_dir,
                    is_crit=is_crit,
                )
                if not took:
                    continue

                # FX
                self.particles.spawn_hit_spark(b.x, b.y)
                blood_amt = 1.4 if head else 0.7
                if is_crit:
                    blood_amt *= 1.4
                self.particles.spawn_blood(b.x, b.y, intensity=blood_amt)
                # Damage number — show crit prominently
                dmg_shown = int(b.damage *
                                (C.HEADSHOT_BONUS if head else 1.0) *
                                (C.CRIT_DAMAGE_MULT if is_crit else 1.0))
                self.particles.spawn_damage_number(b.x, b.y - 20, dmg_shown,
                                                    headshot=head, is_crit=is_crit)
                self.effects.hit_marker(killed=killed)
                self.effects.hit_stop(0.04 if not killed else 0.09)
                # Layered hit audio: pan + bass on crits/headshots
                self.audio.play_at("hit", enemy.x,
                                   volume=0.6 if not head else 1.0)
                if is_crit:
                    self.audio.play_at("crit", enemy.x, volume=0.95)
                if head or is_crit:
                    self.audio.play("bass_thump", volume=0.45)
                if head:
                    self.effects.slowmo(0.25)

                on_hit(enemy, head, killed, is_crit=is_crit)
                if killed:
                    on_kill(enemy, head)
                if not b.register_hit(eid):
                    b.alive = False
                    break

        self.bullets = [b for b in self.bullets if b.alive]

    def draw(self, surface):
        for b in self.bullets:
            b.draw(surface)

    def _muzzle_position_for(self, weapon, player) -> tuple:
        ox, oy = self.muzzle_origin
        oy -= player.recoil_y
        ox += player.recoil_x
        bx, by = player.bob_offset()
        return (ox + bx, oy + by)

    def _apply_aim_assist(self, target, enemies, strength: float) -> tuple:
        if strength <= 0.01:
            return target
        best = None
        best_d = 130
        for e in enemies:
            if not e.alive:
                continue
            d = distance(target, (e.x, e.y))
            if d < best_d:
                best_d = d
                best = e
        if best is None:
            return target
        return (target[0] + (best.x - target[0]) * strength,
                target[1] + (best.y - target[1]) * strength)

    def _mk_big_ring(self, x, y):
        from systems.particle_system import KIND_RING, Particle
        return Particle(KIND_RING, x, y, 0, 0, life=0.7, size=20,
                        color=(120, 220, 255), fade=True)
