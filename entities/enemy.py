"""Enemy AI: momentum-based steering with dodge, strafe, separation, flinch+knockback."""

import math
import random

import pygame

from core import constants as C
from core.utils import (clamp, draw_circle_alpha, draw_glow_circle,
                        draw_rect_alpha, lerp)


class Enemy:
    STATE_SPAWNING = "spawning"
    STATE_APPROACH = "approach"
    STATE_TELEGRAPH = "telegraph"
    STATE_ATTACK = "attack"
    STATE_DEAD = "dead"

    def __init__(self, kind: str, x: float, y: float, difficulty_mul: float = 1.0):
        cfg = C.ENEMY_TYPES[kind]
        style = C.ENEMY_MOVE_STYLE.get(kind, C.ENEMY_MOVE_STYLE["zombie"])
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.size = cfg["size"]
        self.color = cfg["color"]
        self.max_health = cfg["health"] * difficulty_mul
        self.health = self.max_health
        self.speed = cfg["speed"]
        self.damage = cfg["damage"]
        self.score_value = cfg["score"]
        self.attack_range = cfg["attack_range"]
        self.ranged = cfg.get("ranged", False)
        self.projectile_speed = cfg.get("projectile_speed", 480)
        self.projectile_dmg = cfg.get("projectile_dmg", 14)

        self.style = style
        self._strafe_phase = random.uniform(0, math.tau)
        self._zigzag_phase = random.uniform(0, math.tau)

        # State machine
        self.state = Enemy.STATE_SPAWNING
        self.spawn_t = 0.0
        self.spawn_duration = 0.5
        self.death_t = 0.0
        self.death_duration = 0.55
        self.attack_cooldown = 0.0
        self.attack_period = self._compute_attack_period()

        self.telegraph_t = 0.0
        self.telegraph_duration = 0.55 if not self.is_boss else 0.85

        self._anim_t = 0.0
        self._wobble_phase = random.uniform(0, math.tau)
        self.facing = 0.0

        # Hit reaction
        self.flinch_t = 0.0
        self._hit_dir = (0.0, 0.0)

        # Boss
        self.boss_phase = 1
        self._boss_special_cd = 4.0

        # Pending events
        self.pending_projectiles: list = []
        self.pending_summons: int = 0
        self._melee_pending_this_attack = False

    @property
    def is_boss(self) -> bool:
        return self.kind in ("boss", "boss_summoner", "boss_berserker")

    @property
    def alive(self) -> bool:
        return self.state != Enemy.STATE_DEAD

    @property
    def is_dead_done(self) -> bool:
        return self.state == Enemy.STATE_DEAD and self.death_t >= self.death_duration

    def hitbox(self) -> pygame.Rect:
        r = int(self.size * 0.6)
        return pygame.Rect(int(self.x) - r // 2, int(self.y) - r // 2, r, r)

    def head_hitbox(self) -> pygame.Rect:
        r = max(14, int(self.size * 0.25))
        cy = int(self.y - self.size * 0.32)
        return pygame.Rect(int(self.x) - r // 2, cy - r // 2, r, r)

    def _compute_attack_period(self) -> float:
        return {
            "boss":           1.6,
            "boss_summoner":  1.9,
            "boss_berserker": 0.75,
            "soldier":        1.4,
            "fast":           0.7,
            "tank":           1.2,
            "zombie":         1.0,
        }.get(self.kind, 1.0)

    def update(self, dt: float, target_pos, neighbors=None, threats=None):
        """neighbors: iterable of other enemies (for separation steering).
           threats:   iterable of player bullets (for dodge behavior)."""
        self._anim_t += dt
        self.flinch_t = max(0.0, self.flinch_t - dt)

        if self.state == Enemy.STATE_SPAWNING:
            self.spawn_t += dt
            if self.spawn_t >= self.spawn_duration:
                self.state = Enemy.STATE_APPROACH
            return

        if self.state == Enemy.STATE_DEAD:
            self.death_t += dt
            self.x += self.vx * dt * 0.4
            self.y += self.vy * dt * 0.4
            self.vx *= max(0.0, 1.0 - 4 * dt)
            self.vy *= max(0.0, 1.0 - 4 * dt)
            return

        if self.state == Enemy.STATE_TELEGRAPH:
            self.telegraph_t += dt
            # subtle backstep wind-up
            dx = target_pos[0] - self.x
            dy = target_pos[1] - self.y
            d = math.hypot(dx, dy) + 1e-6
            self.vx += (-dx / d) * 60 * dt
            self.vy += (-dy / d) * 60 * dt
            self._integrate(dt, drag_mul=1.5)
            if self.telegraph_t >= self.telegraph_duration:
                self._fire_attack(target_pos)
                self.telegraph_t = 0.0
                self.state = Enemy.STATE_ATTACK
                self._melee_pending_this_attack = True
            return

        dx = target_pos[0] - self.x
        dy = target_pos[1] - self.y
        dist = math.hypot(dx, dy) + 1e-6
        to_target = (dx / dist, dy / dist)
        perp = (-to_target[1], to_target[0])

        if dist > self.attack_range:
            self.state = Enemy.STATE_APPROACH
            desired_x = to_target[0] * self.speed
            desired_y = to_target[1] * self.speed
        else:
            self.state = Enemy.STATE_ATTACK
            desired_x = perp[0] * self.speed * 0.6 * math.sin(self._anim_t * 1.6)
            desired_y = perp[1] * self.speed * 0.6 * math.sin(self._anim_t * 1.6)

        # Strafe
        strafe = self.style.get("strafe", 0.0)
        if strafe > 0.01:
            self._strafe_phase += dt * 2.2
            amp = math.sin(self._strafe_phase) * self.speed * strafe \
                * C.ENEMY_STRAFE_AMPLITUDE
            desired_x += perp[0] * amp
            desired_y += perp[1] * amp

        # Zig-zag
        zfreq = self.style.get("zigzag_freq", 0.0)
        zamp = self.style.get("zigzag_amp", 0.0)
        if zfreq > 0.01 and zamp > 0.01:
            self._zigzag_phase += dt * zfreq * 6.0
            wob = math.sin(self._zigzag_phase) * self.speed * zamp
            desired_x += perp[0] * wob
            desired_y += perp[1] * wob

        # Dodge
        dodge_weight = self.style.get("dodge", 0.0)
        if dodge_weight > 0.01 and threats:
            self._apply_dodge(perp, threats, dodge_weight, dt)

        # Separation
        if neighbors:
            sep_x, sep_y = 0.0, 0.0
            for n in neighbors:
                if n is self or not n.alive:
                    continue
                ex = self.x - n.x
                ey = self.y - n.y
                d = math.hypot(ex, ey)
                if d < 0.5 or d > C.ENEMY_SEPARATION_RADIUS:
                    continue
                weight = 1.0 - d / C.ENEMY_SEPARATION_RADIUS
                sep_x += (ex / d) * weight
                sep_y += (ey / d) * weight
            desired_x += sep_x * C.ENEMY_SEPARATION_WEIGHT
            desired_y += sep_y * C.ENEMY_SEPARATION_WEIGHT

        # Momentum integration
        accel = C.ENEMY_ACCEL
        if self.flinch_t > 0:
            accel *= 0.35
        self.vx += (desired_x - self.vx) * clamp(accel * dt, 0.0, 1.0)
        self.vy += (desired_y - self.vy) * clamp(accel * dt, 0.0, 1.0)
        self._integrate(dt)

        # Smooth facing toward velocity
        if abs(self.vx) + abs(self.vy) > 4:
            target_face = math.atan2(self.vy, self.vx)
            diff = (target_face - self.facing + math.pi) % (2 * math.pi) - math.pi
            self.facing += diff * clamp(dt * 6, 0, 1)

        # Attack timing
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.state == Enemy.STATE_ATTACK and self.attack_cooldown <= 0:
            self.telegraph_t = 0.0
            self.state = Enemy.STATE_TELEGRAPH
            self.attack_cooldown = self.attack_period

        # Boss phase transition
        if self.is_boss:
            self._boss_special_cd = max(0.0, self._boss_special_cd - dt)
            if self.health < self.max_health * 0.5 and self.boss_phase == 1:
                self.boss_phase = 2
                self.speed *= 1.25
                self.attack_period *= 0.7

    def _integrate(self, dt: float, drag_mul: float = 1.0):
        self.vx *= max(0.0, 1.0 - C.ENEMY_DRAG * drag_mul * dt)
        self.vy *= max(0.0, 1.0 - C.ENEMY_DRAG * drag_mul * dt)
        speed_cap = self.speed * 1.8
        v_mag = math.hypot(self.vx, self.vy)
        if v_mag > speed_cap:
            s = speed_cap / v_mag
            self.vx *= s
            self.vy *= s
        self.x += self.vx * dt
        self.y += self.vy * dt

    def _apply_dodge(self, perp, threats, weight: float, dt: float):
        for b in threats:
            ex = self.x - b.x
            ey = self.y - b.y
            v = math.hypot(b.vx, b.vy)
            if v < 1.0:
                continue
            vnx = b.vx / v
            vny = b.vy / v
            t_along = ex * vnx + ey * vny
            if t_along < 0:
                continue
            t_sec = t_along / v
            if t_sec > C.ENEMY_DODGE_LOOKAHEAD:
                continue
            mx = b.x + vnx * t_along - self.x
            my = b.y + vny * t_along - self.y
            perp_dist = math.hypot(mx, my)
            if perp_dist > C.ENEMY_DODGE_RADIUS:
                continue
            side = 1 if (perp[0] * (-vny) + perp[1] * vnx) > 0 else -1
            impulse = weight * 520
            self.vx += -vny * side * impulse * dt
            self.vy += vnx * side * impulse * dt
            break

    def _fire_attack(self, target_pos):
        if self.kind == "boss_summoner" and random.random() < 0.55:
            self.pending_summons += 2 if self.boss_phase == 1 else 3
            return
        if self.kind == "boss_berserker":
            return
        if self.ranged:
            shots = 1
            if self.kind == "boss":
                shots = 3 if self.boss_phase == 1 else 5
            elif self.kind == "boss_summoner":
                shots = 2
            base_angle = math.atan2(target_pos[1] - self.y,
                                    target_pos[0] - self.x)
            spread = 0.18
            for i in range(shots):
                if shots == 1:
                    a = base_angle
                else:
                    a = base_angle + (i / max(1, shots - 1) - 0.5) * spread * 2
                vx = math.cos(a) * self.projectile_speed
                vy = math.sin(a) * self.projectile_speed
                homing = self.is_boss and self.boss_phase == 2
                self.pending_projectiles.append((self.x, self.y, vx, vy,
                                                 self.projectile_dmg, homing))

    def consume_melee_strike(self) -> bool:
        if not self._melee_pending_this_attack:
            return False
        if self.ranged and self.kind not in ("boss_berserker",):
            self._melee_pending_this_attack = False
            return False
        self._melee_pending_this_attack = False
        return True

    def pull_pending_projectiles(self) -> list:
        proj = self.pending_projectiles
        self.pending_projectiles = []
        return proj

    def pull_pending_summons(self) -> int:
        n = self.pending_summons
        self.pending_summons = 0
        return n

    def damage_at(self, point, dmg, headshot_zone=False, headshot_only=False,
                  hit_dir=None, is_crit=False) -> tuple:
        if self.state == Enemy.STATE_DEAD:
            return (False, False, False)
        head = self.head_hitbox()
        body = self.hitbox()
        was_head = head.collidepoint(point)
        body_hit = body.collidepoint(point)
        if not was_head and not body_hit:
            return (False, False, False)
        if headshot_only and not was_head:
            return (True, False, False)

        crit_mult = C.CRIT_DAMAGE_MULT if is_crit else 1.0
        head_mult = C.HEADSHOT_BONUS if (was_head or headshot_zone) else 1.0
        self.health -= dmg * head_mult * crit_mult
        killed = self.health <= 0

        if hit_dir is not None:
            kb = C.ENEMY_KNOCKBACK_HEAD if was_head else C.ENEMY_KNOCKBACK
            if is_crit:
                kb *= 1.5
            if self.is_boss:
                kb *= 0.35
            elif self.kind == "tank":
                kb *= 0.5
            self.vx += hit_dir[0] * kb
            self.vy += hit_dir[1] * kb
            self._hit_dir = hit_dir

        if not self.is_boss:
            self.flinch_t = C.ENEMY_FLINCH_DURATION

        if killed:
            if hit_dir is not None:
                self.vx += hit_dir[0] * 240
                self.vy += hit_dir[1] * 240
            self.state = Enemy.STATE_DEAD
            self.death_t = 0.0
        return (True, was_head, killed)

    def draw(self, surface):
        if self.state == Enemy.STATE_SPAWNING:
            self._draw_spawn(surface)
            return
        if self.state == Enemy.STATE_DEAD:
            self._draw_death(surface)
            return

        wobble_x = 0
        wobble_y = 0
        if self.flinch_t > 0:
            ft = self.flinch_t / C.ENEMY_FLINCH_DURATION
            wobble_x = int(math.sin(self._anim_t * 60) * 4 * ft)
            wobble_y = int(math.cos(self._anim_t * 55) * 2 * ft)
        cx, cy = int(self.x) + wobble_x, int(self.y) + wobble_y

        v_mag = math.hypot(self.vx, self.vy)
        shadow_w = int(self.size * 0.55 + min(20, v_mag * 0.02))
        shadow_h = int(self.size * 0.25)
        shadow_rect = pygame.Rect(cx - shadow_w // 2,
                                   cy + int(self.size * 0.4),
                                   shadow_w, shadow_h)
        draw_rect_alpha(surface, (0, 0, 0, 110), shadow_rect, border_radius=shadow_h)

        if self.is_boss:
            aura_color = ((255, 80, 90) if self.kind == "boss"
                          else (180, 120, 240) if self.kind == "boss_summoner"
                          else (255, 140, 60))
            draw_glow_circle(surface, aura_color, (cx, cy), int(self.size * 0.7),
                             layers=4, alpha=140)
        elif self.kind == "fast":
            draw_glow_circle(surface, self.color, (cx, cy), int(self.size * 0.5),
                             layers=2, alpha=80)

        if self.state == Enemy.STATE_TELEGRAPH:
            self._draw_telegraph(surface, cx, cy)

        body_color = self.color
        if self.flinch_t > 0:
            ft = self.flinch_t / C.ENEMY_FLINCH_DURATION
            body_color = tuple(int(lerp(c, 255, ft * 0.55)) for c in self.color)
        torso_w = int(self.size * 0.55)
        torso_h = int(self.size * 0.7)
        torso_rect = pygame.Rect(cx - torso_w // 2, cy - torso_h // 3, torso_w, torso_h)
        pygame.draw.rect(surface, body_color, torso_rect, border_radius=8)
        head_r = max(12, int(self.size * 0.22))
        head_cy = cy - int(self.size * 0.32)
        pygame.draw.circle(surface, body_color, (cx, head_cy), head_r)
        pygame.draw.circle(surface, (0, 0, 0), (cx, head_cy), head_r, 2)
        eye_off = max(3, head_r // 3)
        eye_color = (255, 60, 60) if self.kind in ("zombie", "boss",
                                                    "boss_berserker") else (250, 250, 250)
        pygame.draw.circle(surface, eye_color, (cx - eye_off, head_cy - 2), 2)
        pygame.draw.circle(surface, eye_color, (cx + eye_off, head_cy - 2), 2)
        swing_freq = 4 + min(12, v_mag * 0.02)
        swing = math.sin(self._anim_t * swing_freq + self._wobble_phase) * (self.size * 0.15)
        arm_color = tuple(max(0, c - 30) for c in self.color)
        pygame.draw.line(surface, arm_color, (cx - torso_w // 2, cy - 5),
                         (cx - torso_w // 2 - 10, cy + int(self.size * 0.25) + int(swing)), 6)
        pygame.draw.line(surface, arm_color, (cx + torso_w // 2, cy - 5),
                         (cx + torso_w // 2 + 10, cy + int(self.size * 0.25) - int(swing)), 6)

        if self.ranged:
            gx = cx + math.cos(self.facing) * (torso_w // 2 + 6)
            gy = cy + math.sin(self.facing) * (torso_w // 2 + 6) - 4
            pygame.draw.line(surface, (40, 44, 52), (cx, cy - 4),
                             (int(gx), int(gy)), 4)

        self._draw_health_bar(surface, cx, head_cy - head_r - 14)

    def _draw_spawn(self, surface):
        t = self.spawn_t / self.spawn_duration
        alpha = int(255 * t)
        radius = int(lerp(self.size, self.size * 0.5, t))
        draw_circle_alpha(surface, (255, 60, 70, max(0, 200 - alpha)),
                          (self.x, self.y), radius)
        draw_circle_alpha(surface, (255, 255, 255, alpha // 2),
                          (self.x, self.y), max(4, int(self.size * 0.25 * t)))

    def _draw_death(self, surface):
        t = self.death_t / self.death_duration
        alpha = int(255 * (1 - t))
        if alpha <= 0:
            return
        size = int(self.size * (1 + 0.2 * t))
        offx = int(self._hit_dir[0] * 18 * t)
        offy = int(self._hit_dir[1] * 12 * t + size * 0.6 * t)
        rect = pygame.Rect(int(self.x) - size // 2 + offx,
                           int(self.y) - size // 4 + offy,
                           size, size // 2)
        draw_rect_alpha(surface, (*self.color, alpha), rect, border_radius=6)

    def _draw_telegraph(self, surface, cx, cy):
        t = self.telegraph_t / self.telegraph_duration
        radius = int(self.size * (0.55 + 0.5 * t))
        alpha = int(120 + 100 * (1 - t))
        col = (255, 70, 70) if not self.is_boss else (255, 150, 60)
        draw_circle_alpha(surface, (*col, alpha), (cx, cy), radius)
        pygame.draw.circle(surface, col, (cx, cy), radius, 2)

    def _draw_health_bar(self, surface, cx, top_y):
        pct = clamp(self.health / self.max_health, 0.0, 1.0)
        w = int(self.size * 0.9)
        h = 6 if not self.is_boss else 10
        bar_rect = pygame.Rect(cx - w // 2, top_y, w, h)
        draw_rect_alpha(surface, (0, 0, 0, 180), bar_rect, border_radius=3)
        fill_w = max(0, int((w - 2) * pct))
        col = (60, 220, 110) if pct > 0.5 else (240, 200, 70) if pct > 0.25 else (240, 70, 80)
        pygame.draw.rect(surface, col,
                         (bar_rect.x + 1, bar_rect.y + 1, fill_w, h - 2),
                         border_radius=2)
