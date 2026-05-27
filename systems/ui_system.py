"""UI / HUD: HUD, crosshair, menus, shop, kill feed, banners (procedurally drawn)."""

import math
import time

import pygame

from core import constants as C
from core.utils import (clamp, draw_circle_alpha, draw_glow_circle,
                        draw_rect_alpha, draw_text, resolve_color_name)


class KillFeedEntry:
    __slots__ = ("text", "born", "life")

    def __init__(self, text: str):
        self.text = text
        self.born = time.time()
        self.life = 3.0


class UISystem:
    def __init__(self, settings, save_data):
        self.settings = settings
        self.save = save_data
        self.font_xs = pygame.font.SysFont("consolas", 14)
        self.font_sm = pygame.font.SysFont("consolas", 18)
        self.font_md = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_lg = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_xl = pygame.font.SysFont("consolas", 64, bold=True)
        self.font_huge = pygame.font.SysFont("consolas", 96, bold=True)

        self.kill_feed: list[KillFeedEntry] = []
        self.popup_text: str | None = None
        self._popup_until: float = 0.0
        self._achv_popup: str | None = None
        self._achv_until: float = 0.0

        # Animations
        self._chair_pulse = 0.0
        self._wave_banner_t = 0.0
        self._wave_banner_text = ""
        self._multi_banner_t = 0.0
        self._multi_banner_text = ""

    def add_kill(self, text: str):
        self.kill_feed.append(KillFeedEntry(text))
        if len(self.kill_feed) > 5:
            self.kill_feed.pop(0)

    def popup(self, text: str, seconds: float = 1.2):
        self.popup_text = text
        self._popup_until = time.time() + seconds

    def show_achievement(self, name: str):
        self._achv_popup = name
        self._achv_until = time.time() + 3.5

    def show_wave_banner(self, text: str):
        self._wave_banner_text = text
        self._wave_banner_t = 1.8

    def show_multi_kill(self, text: str):
        self._multi_banner_text = text
        self._multi_banner_t = 1.4

    def draw_hud(self, surface, player, wave_director, fps: float, gesture,
                 recording_active: bool = False, recording_time: float = 0.0,
                 time_attack_remaining: float | None = None):
        w, h = surface.get_width(), surface.get_height()

        self._draw_bars(surface, player)
        self._draw_wave_panel(surface, wave_director, player,
                              time_attack_remaining=time_attack_remaining)
        self._draw_ammo_panel(surface, player)
        if player.combo >= 2:
            self._draw_combo(surface, player)
        if self.settings.show_minimap:
            self._draw_radar(surface, player, wave_director)
        self._draw_kill_feed(surface)
        self._draw_active_effects(surface, player)
        if self.settings.show_fps:
            draw_text(surface, f"FPS {int(fps)}", self.font_xs,
                      (180, 220, 200), (10, h - 22))
        self._draw_gesture_chip(surface, gesture)
        if recording_active:
            self._draw_recording_indicator(surface, recording_time)
        if self.settings.show_tutorial:
            self._draw_tutorial_strip(surface)
        if self._multi_banner_t > 0:
            self._draw_multi_kill_banner(surface)
        if self.popup_text and time.time() < self._popup_until:
            draw_text(surface, self.popup_text, self.font_lg,
                      C.NEON_CYAN, (w // 2, 110), center=True)
        if self._achv_popup and time.time() < self._achv_until:
            self._draw_achievement(surface, self._achv_popup)
        if self._wave_banner_t > 0:
            self._draw_wave_banner(surface)

    def update(self, dt: float):
        self._chair_pulse += dt * 4.0
        self._wave_banner_t = max(0.0, self._wave_banner_t - dt)
        self._multi_banner_t = max(0.0, self._multi_banner_t - dt)
        now = time.time()
        self.kill_feed = [k for k in self.kill_feed if (now - k.born) < k.life]

    def draw_crosshair(self, surface, target, spread_amount: float):
        x, y = int(target[0]), int(target[1])
        col = resolve_color_name(self.settings.crosshair_color)
        style = self.settings.crosshair_style
        if style == "dot":
            draw_glow_circle(surface, col, (x, y), 4, layers=2, alpha=160)
            pygame.draw.circle(surface, col, (x, y), 3)
            return
        if style == "circle":
            radius = 16 + int(spread_amount * 200)
            pygame.draw.circle(surface, col, (x, y), radius, 2)
            pygame.draw.circle(surface, (255, 255, 255), (x, y), 2)
            return
        if style == "cross":
            length = 14 + int(spread_amount * 200)
            pygame.draw.line(surface, col, (x - length, y), (x - 4, y), 2)
            pygame.draw.line(surface, col, (x + 4, y), (x + length, y), 2)
            pygame.draw.line(surface, col, (x, y - length), (x, y - 4), 2)
            pygame.draw.line(surface, col, (x, y + 4), (x, y + length), 2)
            pygame.draw.circle(surface, (255, 255, 255), (x, y), 2)
            return
        if style == "tactical":
            radius = 18 + int(spread_amount * 200)
            draw_glow_circle(surface, col, (x, y), 6, layers=2, alpha=110)
            pygame.draw.circle(surface, col, (x, y), radius, 1)
            pygame.draw.circle(surface, col, (x, y), 2)
            # Ranging dots
            for d in (-radius - 16, radius + 16):
                pygame.draw.circle(surface, col, (x + d, y), 2)
                pygame.draw.circle(surface, col, (x, y + d), 2)
            pygame.draw.line(surface, col, (x - radius - 10, y),
                             (x - radius - 4, y), 2)
            return
        # CLASSIC (default)
        radius = 14 + int(spread_amount * 200) + int(2 * math.sin(self._chair_pulse))
        draw_glow_circle(surface, col, (x, y), 6, layers=2, alpha=120)
        pygame.draw.circle(surface, col, (x, y), radius, 1)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            sx, sy = x + dx * (radius + 4), y + dy * (radius + 4)
            ex, ey = x + dx * (radius + 10), y + dy * (radius + 10)
            pygame.draw.line(surface, col, (sx, sy), (ex, ey), 2)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), 2)

    # HUD components
    def _draw_bars(self, surface, player):
        x, y = 18, 18
        draw_rect_alpha(surface, C.HUD_BG, (x, y, 280, 92), border_radius=10)
        pygame.draw.rect(surface, C.HUD_LINE, (x, y, 280, 92), 1, border_radius=10)

        # Smoothed display values so the bars animate instead of snapping
        disp_hp = getattr(player, "display_health", player.health)
        disp_armor = getattr(player, "display_armor", player.armor)

        pct = clamp(disp_hp / player.max_health, 0, 1)
        true_pct = clamp(player.health / player.max_health, 0, 1)
        health_color = (60, 220, 110) if pct > 0.5 else (240, 200, 70) if pct > 0.25 else (240, 70, 80)
        draw_text(surface, "HEALTH", self.font_xs, (180, 200, 220), (x + 14, y + 10))
        bar_w, bar_h = 240, 14
        draw_rect_alpha(surface, (0, 0, 0, 180), (x + 14, y + 28, bar_w, bar_h),
                        border_radius=4)
        # Lag fill (ghost) — shows the difference between true and displayed value
        if abs(true_pct - pct) > 0.01:
            ghost_color = (240, 240, 240) if true_pct < pct else (60, 220, 110)
            ghost_w = int((bar_w - 4) * abs(true_pct - pct))
            ghost_x = x + 16 + int((bar_w - 4) * min(true_pct, pct))
            pygame.draw.rect(surface, ghost_color,
                             (ghost_x, y + 30, ghost_w, bar_h - 4),
                             border_radius=3)
        pygame.draw.rect(surface, health_color,
                         (x + 16, y + 30, int((bar_w - 4) * pct), bar_h - 4),
                         border_radius=3)
        draw_text(surface, f"{int(disp_hp)} / {player.max_health}",
                  self.font_xs, (240, 240, 240), (x + bar_w + 4, y + 28))

        a_pct = clamp(disp_armor / player.max_armor, 0, 1)
        draw_text(surface, "ARMOR", self.font_xs, (180, 200, 220), (x + 14, y + 50))
        draw_rect_alpha(surface, (0, 0, 0, 180), (x + 14, y + 68, bar_w, bar_h),
                        border_radius=4)
        pygame.draw.rect(surface, (90, 160, 240),
                         (x + 16, y + 70, int((bar_w - 4) * a_pct), bar_h - 4),
                         border_radius=3)
        draw_text(surface, f"{int(disp_armor)}", self.font_xs,
                  (220, 230, 240), (x + bar_w + 4, y + 68))

    def _draw_wave_panel(self, surface, wave_director, player,
                         time_attack_remaining=None):
        w = 270
        x = C.SCREEN_WIDTH - w - 18
        y = 18
        draw_rect_alpha(surface, C.HUD_BG, (x, y, w, 92), border_radius=10)
        pygame.draw.rect(surface, C.HUD_LINE, (x, y, w, 92), 1, border_radius=10)

        if time_attack_remaining is not None:
            mm = int(time_attack_remaining) // 60
            ss = int(time_attack_remaining) % 60
            draw_text(surface, f"TIME  {mm:02d}:{ss:02d}", self.font_md,
                      C.NEON_CYAN, (x + 14, y + 8))
        else:
            phase_text = {
                "intro": "GET READY",
                "active": f"WAVE {wave_director.wave}",
                "break": f"WAVE {wave_director.wave} CLEAR",
                "ended": "TIME UP",
            }.get(wave_director.phase, "")
            draw_text(surface, phase_text, self.font_md, C.NEON_CYAN,
                      (x + 14, y + 8))

        disp_score = int(getattr(player, "display_score", player.score))
        disp_coins = int(getattr(player, "display_coins", player.coins))
        draw_text(surface, f"SCORE  {disp_score:,}", self.font_sm,
                  (240, 240, 240), (x + 14, y + 40))
        draw_text(surface, f"COINS  {disp_coins}", self.font_sm,
                  (240, 220, 80), (x + 14, y + 62))

    def _draw_ammo_panel(self, surface, player):
        w, h = 280, 80
        x = 18
        y = C.SCREEN_HEIGHT - h - 18
        draw_rect_alpha(surface, C.HUD_BG, (x, y, w, h), border_radius=10)
        pygame.draw.rect(surface, C.HUD_LINE, (x, y, w, h), 1, border_radius=10)

        weapon = player.weapon
        draw_text(surface, weapon.name, self.font_sm, (220, 230, 240),
                  (x + 12, y + 8))

        ammo_str = f"{weapon.ammo:>3} / {weapon.reserve}"
        color = (240, 220, 80) if weapon.ammo > 0 else (240, 70, 80)
        draw_text(surface, ammo_str, self.font_lg, color, (x + 12, y + 32))

        if weapon.is_reloading:
            p = weapon.reload_progress
            bar = pygame.Rect(x + 12, y + h - 12, w - 24, 4)
            draw_rect_alpha(surface, (60, 60, 70, 200), bar, border_radius=2)
            pygame.draw.rect(surface, C.NEON_CYAN,
                             (bar.x, bar.y, int(bar.width * p), bar.height),
                             border_radius=2)

        for i in range(4):
            cx = x + w + 18 + i * 38
            cy = y + h // 2
            box = pygame.Rect(cx - 14, cy - 14, 28, 28)
            draw_rect_alpha(surface, C.HUD_BG, box, border_radius=6)
            border = C.NEON_CYAN if i == player.weapon_index else (90, 100, 110)
            pygame.draw.rect(surface, border, box, 1, border_radius=6)
            draw_text(surface, str(i + 1), self.font_xs, (220, 230, 240),
                      box.center, center=True)

    def _draw_combo(self, surface, player):
        text = f"COMBO x{player.combo}"
        draw_text(surface, text, self.font_md, C.NEON_PINK,
                  (C.SCREEN_WIDTH // 2, 26), center=True)

    def _draw_radar(self, surface, player, wave_director):
        cx, cy = C.SCREEN_WIDTH // 2, 95
        r = 50
        draw_circle_alpha(surface, (10, 14, 20, 160), (cx, cy), r + 4)
        pygame.draw.circle(surface, C.HUD_LINE, (cx, cy), r, 1)
        sweep_a = (time.time() * 1.2) % (math.pi * 2)
        ex = cx + math.cos(sweep_a) * r
        ey = cy + math.sin(sweep_a) * r
        pygame.draw.line(surface, (0, 200, 220), (cx, cy), (ex, ey), 1)
        pygame.draw.circle(surface, (180, 220, 240), (cx, cy), 2)
        for e in wave_director.enemies:
            if not e.alive:
                continue
            dx = e.x - C.SCREEN_WIDTH / 2
            dy = e.y - C.SCREEN_HEIGHT / 2
            mag = math.hypot(dx, dy) or 1
            if mag > 600:
                dx = dx / mag * 600
                dy = dy / mag * 600
            rx = cx + dx * (r / 600)
            ry = cy + dy * (r / 600)
            col = (255, 80, 90) if e.is_boss else (255, 200, 80)
            pygame.draw.circle(surface, col, (int(rx), int(ry)), 2)

    def _draw_kill_feed(self, surface):
        y0 = 122
        for i, entry in enumerate(self.kill_feed[-5:]):
            alpha = clamp(1.0 - (time.time() - entry.born) / entry.life, 0, 1)
            shade = int(255 * alpha)
            draw_rect_alpha(surface, (10, 14, 20, int(160 * alpha)),
                            (C.SCREEN_WIDTH - 280, y0 + i * 22, 262, 20),
                            border_radius=4)
            draw_text(surface, entry.text, self.font_xs,
                      (240, 240, 240) if shade > 60 else (180, 180, 180),
                      (C.SCREEN_WIDTH - 270, y0 + i * 22 + 2))

    def _draw_gesture_chip(self, surface, gesture):
        labels = []
        if gesture and gesture.detected:
            if gesture.peace_sign:
                labels.append("PEACE")
            if gesture.fist_closed:
                labels.append("FIST -> RELOAD")
            if gesture.index_extended and gesture.pinch_distance < 0.08:
                labels.append("PINCH -> FIRE")
            elif gesture.index_extended:
                labels.append("AIM")
            if gesture.two_hands:
                labels.append("TWO HANDS -> SPECIAL")
        else:
            labels.append("NO HAND DETECTED")
        text = "  ".join(labels)
        if not text:
            return
        rect = self.font_xs.render(text, True, (240, 240, 240)).get_rect()
        cx = C.SCREEN_WIDTH // 2
        bg = pygame.Rect(cx - rect.width // 2 - 12, C.SCREEN_HEIGHT - 30,
                         rect.width + 24, 22)
        draw_rect_alpha(surface, (10, 14, 20, 180), bg, border_radius=10)
        pygame.draw.rect(surface, C.HUD_LINE, bg, 1, border_radius=10)
        draw_text(surface, text, self.font_xs, (220, 235, 245),
                  (cx, C.SCREEN_HEIGHT - 19), center=True)

    def _draw_active_effects(self, surface, player):
        effects = player.active_effects()
        if not effects:
            return
        x = 18
        y = 122
        for kind, remaining in effects.items():
            defn = C.PICKUP_DEFINITIONS.get(kind)
            if defn is None:
                continue
            box = pygame.Rect(x, y, 220, 26)
            draw_rect_alpha(surface, (10, 14, 20, 180), box, border_radius=6)
            pygame.draw.rect(surface, defn["color"], box, 1, border_radius=6)
            draw_text(surface, defn["label"], self.font_xs, (240, 240, 240),
                      (x + 8, y + 5))
            # Time bar
            pct = clamp(remaining / max(0.01, defn["duration"]), 0, 1)
            pygame.draw.rect(surface, defn["color"],
                             (x + 8, y + 20, int(204 * pct), 3), border_radius=1)
            y += 30

    def _draw_recording_indicator(self, surface, elapsed: float):
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
        r = 8
        cx, cy = C.SCREEN_WIDTH - 30, 130
        pygame.draw.circle(surface, (255, int(40 + 100 * pulse),
                                     int(60 + 80 * pulse)),
                           (cx, cy), r)
        mm = int(elapsed) // 60
        ss = int(elapsed) % 60
        draw_text(surface, f"REC {mm:02d}:{ss:02d}", self.font_xs,
                  (240, 240, 240), (cx - 80, cy - 7))

    def _draw_tutorial_strip(self, surface):
        """First-run helper at the bottom showing the gesture map."""
        steps = [
            "INDEX UP = AIM",
            "PINCH = FIRE",
            "FIST = RELOAD",
            "PEACE = GRENADE",
            "TWO HANDS = SPECIAL",
        ]
        y = C.SCREEN_HEIGHT - 60
        text = "   |   ".join(steps)
        w = self.font_xs.size(text)[0] + 32
        x = (C.SCREEN_WIDTH - w) // 2
        draw_rect_alpha(surface, (10, 14, 20, 200), (x, y, w, 22),
                        border_radius=10)
        pygame.draw.rect(surface, (180, 220, 250), (x, y, w, 22),
                         1, border_radius=10)
        draw_text(surface, text, self.font_xs, (220, 240, 250),
                  (C.SCREEN_WIDTH // 2, y + 11), center=True)
        draw_text(surface, "Press T to hide", self.font_xs,
                  (140, 160, 180), (C.SCREEN_WIDTH // 2, y + 30), center=True)

    def _draw_achievement(self, surface, name):
        w_box = 360
        x = C.SCREEN_WIDTH // 2 - w_box // 2
        y = 170
        draw_rect_alpha(surface, (10, 14, 20, 220), (x, y, w_box, 56),
                        border_radius=10)
        pygame.draw.rect(surface, C.NEON_YELLOW, (x, y, w_box, 56), 1,
                         border_radius=10)
        draw_text(surface, "ACHIEVEMENT", self.font_xs, (255, 220, 80),
                  (x + w_box // 2, y + 10), center=True)
        draw_text(surface, name, self.font_md, (240, 240, 240),
                  (x + w_box // 2, y + 32), center=True)

    def _draw_wave_banner(self, surface):
        t = self._wave_banner_t / 1.8
        alpha = int(255 * (1 - abs(t - 0.5) * 2))
        shape = pygame.Surface((C.SCREEN_WIDTH, 110), pygame.SRCALPHA)
        shape.fill((10, 14, 20, max(0, alpha // 2)))
        surface.blit(shape, (0, C.SCREEN_HEIGHT // 2 - 55))
        draw_text(surface, self._wave_banner_text, self.font_xl,
                  C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2),
                  center=True)

    def _draw_multi_kill_banner(self, surface):
        t = 1.0 - (self._multi_banner_t / 1.4)
        alpha = int(255 * (1.0 - t * 0.7))
        scale = 1.0 + 0.4 * (1.0 - t)
        font_size = int(64 * scale)
        font = pygame.font.SysFont("consolas", font_size, bold=True)
        rendered = font.render(self._multi_banner_text, True, C.NEON_PINK)
        rendered.set_alpha(alpha)
        rect = rendered.get_rect(center=(C.SCREEN_WIDTH // 2, 200))
        # Glow halo
        draw_glow_circle(surface, C.NEON_PINK, rect.center,
                         rect.width // 2, layers=3, alpha=int(120 * (1 - t)))
        surface.blit(rendered, rect)

    # Menus
    def draw_main_menu(self, surface, selected: int):
        self._draw_menu_bg(surface)
        # Big title — split so the lower line glows differently
        draw_text(surface, "SR-VR", self.font_huge, C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, 130), center=True)
        draw_text(surface, "VIRTUAL REALM", self.font_xl, C.NEON_PINK,
                  (C.SCREEN_WIDTH // 2, 200), center=True)
        draw_text(surface, "AI Gesture-Controlled FPS",
                  self.font_md, (200, 220, 230),
                  (C.SCREEN_WIDTH // 2, 250), center=True)
        items = ["PLAY", "SELECT MODE", "SETTINGS", "CALIBRATE", "QUIT"]
        self._draw_menu_items(surface, items, selected, top=340)
        draw_text(surface, "Up/Down navigate  |  Enter select  |  F12 screenshot  |  F9 record",
                  self.font_xs, (160, 180, 200),
                  (C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT - 28), center=True)
        draw_text(surface, f"High Score: {self.save.high_score:,}",
                  self.font_sm, (200, 220, 80),
                  (24, C.SCREEN_HEIGHT - 24))
        draw_text(surface, f"Mode: {self._mode_label(self.settings.chosen_mode)}",
                  self.font_sm, (180, 230, 240),
                  (C.SCREEN_WIDTH - 240, C.SCREEN_HEIGHT - 24))

    def _mode_label(self, mode_id: str) -> str:
        for mid, label, _ in C.GAME_MODES:
            if mid == mode_id:
                return label
        return mode_id

    def draw_mode_select(self, surface, selected: int):
        self._draw_menu_bg(surface)
        draw_text(surface, "SELECT MODE", self.font_xl, C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, 110), center=True)
        top = 220
        for i, (mid, label, desc) in enumerate(C.GAME_MODES):
            y = top + i * 80
            color = C.NEON_CYAN if i == selected else (200, 215, 230)
            box_x = C.SCREEN_WIDTH // 2 - 320
            box_w = 640
            if i == selected:
                draw_rect_alpha(surface, (0, 220, 245, 30),
                                (box_x, y - 8, box_w, 64), border_radius=10)
                pygame.draw.rect(surface, C.NEON_CYAN,
                                 (box_x, y - 8, box_w, 64), 1, border_radius=10)
            draw_text(surface, label, self.font_lg, color, (box_x + 24, y))
            draw_text(surface, desc, self.font_sm, (200, 215, 230),
                      (box_x + 24, y + 36))
        draw_text(surface, "Enter to confirm  |  ESC to back",
                  self.font_xs, (160, 180, 200),
                  (C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT - 28), center=True)

    def draw_pause_menu(self, surface, selected: int):
        draw_rect_alpha(surface, (0, 0, 0, 170),
                        (0, 0, C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        draw_text(surface, "PAUSED", self.font_xl, C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, 180), center=True)
        items = ["RESUME", "SETTINGS", "MAIN MENU"]
        self._draw_menu_items(surface, items, selected, top=300)

    def draw_settings_menu(self, surface, selected: int, items):
        self._draw_menu_bg(surface)
        draw_text(surface, "SETTINGS", self.font_xl, C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, 80), center=True)
        top = 150
        row_h = 32
        for i, (label, value) in enumerate(items):
            y = top + i * row_h
            color = C.NEON_CYAN if i == selected else (200, 215, 230)
            draw_text(surface, label, self.font_sm, color,
                      (C.SCREEN_WIDTH // 2 - 280, y))
            draw_text(surface, str(value), self.font_sm, (240, 240, 240),
                      (C.SCREEN_WIDTH // 2 + 280, y))
        draw_text(surface, "Left/Right change  |  ESC back",
                  self.font_xs, (160, 180, 200),
                  (C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT - 28), center=True)

    def draw_calibration(self, surface, gesture, sample_text: str):
        self._draw_menu_bg(surface)
        draw_text(surface, "GESTURE CALIBRATION", self.font_xl, C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, 90), center=True)
        draw_text(surface, sample_text, self.font_sm, (220, 230, 240),
                  (C.SCREEN_WIDTH // 2, 170), center=True)
        tips = [
            "Show your INDEX finger up        -> Aim cursor",
            "Pinch THUMB + INDEX               -> Fire",
            "Close your FIST                   -> Reload",
            "PEACE sign (index+middle)         -> Grenade",
            "Show TWO HANDS, both index up     -> Special",
            "Press ESC when ready.",
        ]
        for i, t in enumerate(tips):
            draw_text(surface, t, self.font_sm, (220, 230, 240),
                      (200, 250 + i * 32))
        if gesture and gesture.detected:
            cx, cy = int(gesture.aim[0]), int(gesture.aim[1])
            pygame.draw.circle(surface, C.NEON_PINK, (cx, cy), 8, 2)

    def draw_shop(self, surface, player, items_state, selected: int,
                  bought_in_run: set):
        """items_state: list of (item_dict, can_afford) pairs."""
        self._draw_menu_bg(surface)
        draw_text(surface, "ARMORY", self.font_xl, C.NEON_CYAN,
                  (C.SCREEN_WIDTH // 2, 70), center=True)
        draw_text(surface, f"COINS: {player.coins}", self.font_md,
                  C.NEON_YELLOW, (C.SCREEN_WIDTH // 2, 120), center=True)
        top = 170
        row_h = 44
        for i, (item, can_afford) in enumerate(items_state):
            y = top + i * row_h
            box_x = C.SCREEN_WIDTH // 2 - 360
            box_w = 720
            highlight = i == selected
            owned = item["id"] in bought_in_run and item["id"].startswith(
                ("max_", "fast_", "extra_", "unlock_"))
            if highlight:
                draw_rect_alpha(surface, (0, 220, 245, 30),
                                (box_x, y - 4, box_w, row_h - 6),
                                border_radius=8)
                pygame.draw.rect(surface, C.NEON_CYAN,
                                 (box_x, y - 4, box_w, row_h - 6),
                                 1, border_radius=8)
            name_col = (140, 150, 160) if owned else (
                C.NEON_CYAN if highlight else (220, 230, 240))
            draw_text(surface, item["name"], self.font_md, name_col,
                      (box_x + 16, y))
            desc_col = (160, 175, 190) if not owned else (110, 120, 130)
            draw_text(surface, item["desc"] % () if "%%" in item["desc"]
                      else item["desc"], self.font_xs, desc_col,
                      (box_x + 16, y + 26))
            cost_col = (140, 150, 160) if owned else (
                (255, 220, 80) if can_afford else (200, 80, 90))
            cost_str = "OWNED" if owned else f"{item['cost']}"
            draw_text(surface, cost_str, self.font_md, cost_col,
                      (box_x + box_w - 100, y), center=False)
        draw_text(surface, "Up/Down move  |  Enter buy  |  C continue to next wave",
                  self.font_xs, (160, 180, 200),
                  (C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT - 28), center=True)

    def draw_game_over(self, surface, player, wave: int, new_high: bool,
                       stats=None):
        draw_rect_alpha(surface, (0, 0, 0, 200),
                        (0, 0, C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        draw_text(surface, "MISSION FAILED", self.font_huge, (240, 80, 90),
                  (C.SCREEN_WIDTH // 2, 140), center=True)
        draw_text(surface, f"Score: {player.score:,}", self.font_lg,
                  (240, 240, 240), (C.SCREEN_WIDTH // 2, 240), center=True)
        draw_text(surface, f"Wave reached: {wave}", self.font_md,
                  (220, 230, 240), (C.SCREEN_WIDTH // 2, 290), center=True)
        if new_high:
            draw_text(surface, "*** NEW HIGH SCORE ***", self.font_md,
                      C.NEON_YELLOW, (C.SCREEN_WIDTH // 2, 330), center=True)
        if stats is not None:
            self._draw_stats_panel(surface, stats)
        draw_text(surface, "Press ENTER to retry  |  ESC for main menu",
                  self.font_sm, (200, 220, 230),
                  (C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT - 80), center=True)

    def _draw_stats_panel(self, surface, stats):
        x = C.SCREEN_WIDTH // 2 - 240
        y = 400
        w, h = 480, 170
        draw_rect_alpha(surface, (10, 14, 20, 200), (x, y, w, h),
                        border_radius=10)
        pygame.draw.rect(surface, C.HUD_LINE, (x, y, w, h), 1, border_radius=10)
        rows = [
            ("Kills", f"{stats.kills}"),
            ("Headshots", f"{stats.headshots}"),
            ("Accuracy", f"{stats.accuracy() * 100:.1f}%"),
            ("Best Combo", f"x{stats.best_combo}"),
            ("Best Multi-Kill", f"x{stats.best_multi_kill}"),
            ("Damage Taken", f"{int(stats.damage_taken)}"),
            ("Perfect Waves", f"{stats.perfect_waves}"),
        ]
        for i, (label, val) in enumerate(rows):
            yy = y + 14 + i * 22
            draw_text(surface, label, self.font_sm, (200, 215, 230),
                      (x + 18, yy))
            draw_text(surface, val, self.font_sm, (240, 240, 240),
                      (x + w - 18 - self.font_sm.size(val)[0], yy))

    def _draw_menu_bg(self, surface):
        surface.fill((6, 8, 14))
        t = time.time()
        for i in range(0, C.SCREEN_WIDTH + C.SCREEN_HEIGHT, 32):
            shift = int(t * 60) % 32
            x1 = i + shift
            pygame.draw.line(surface, (12, 18, 26), (x1, 0),
                             (x1 - C.SCREEN_HEIGHT, C.SCREEN_HEIGHT), 1)
        draw_rect_alpha(surface, (10, 14, 20, 200),
                        (0, 0, C.SCREEN_WIDTH, 48))
        draw_rect_alpha(surface, (10, 14, 20, 200),
                        (0, C.SCREEN_HEIGHT - 48, C.SCREEN_WIDTH, 48))
        pygame.draw.line(surface, C.HUD_LINE, (0, 48), (C.SCREEN_WIDTH, 48), 1)
        pygame.draw.line(surface, C.HUD_LINE,
                         (0, C.SCREEN_HEIGHT - 48),
                         (C.SCREEN_WIDTH, C.SCREEN_HEIGHT - 48), 1)

    def _draw_menu_items(self, surface, items, selected, top):
        for i, label in enumerate(items):
            y = top + i * 56
            color = C.NEON_CYAN if i == selected else (200, 215, 230)
            if i == selected:
                draw_rect_alpha(surface, (0, 220, 245, 30),
                                (C.SCREEN_WIDTH // 2 - 180, y - 20, 360, 44),
                                border_radius=10)
                draw_text(surface, ">", self.font_lg, C.NEON_CYAN,
                          (C.SCREEN_WIDTH // 2 - 150, y), center=True)
            draw_text(surface, label, self.font_lg, color,
                      (C.SCREEN_WIDTH // 2, y), center=True)
