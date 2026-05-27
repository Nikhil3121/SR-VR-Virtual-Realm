"""Game engine — main loop, state machine, and system wiring."""

from __future__ import annotations

import datetime
import math
import random
import time
from datetime import datetime as _dt

import cv2
import pygame

from core import constants as C
from core.settings import (RunStats, SaveData, Settings, load_save,
                           load_settings, save_save, save_settings,
                           save_stats_snapshot)
from core.utils import clamp, cv2_frame_to_surface
from entities.enemy_bullet import EnemyBullet
from entities.player import Player
from entities.weapons import build_loadout
from systems.announcer import Announcer
from systems.ar_mask import ARMaskSystem
from systems.audio_system import AudioSystem
from systems.effects_system import EffectsSystem
from systems.enemy_system import WaveDirector
from systems.hand_tracking import HandTracker
from systems.particle_system import ParticleSystem
from systems.pickup_system import PickupSystem
from systems.recording_system import RecordingSystem
from systems.shooting_system import ShootingSystem
from systems.ui_system import UISystem
from systems.weather_system import WeatherSystem


STATE_MENU = "menu"
STATE_MODE_SELECT = "mode_select"
STATE_SETTINGS = "settings"
STATE_CALIBRATE = "calibrate"
STATE_PLAYING = "playing"
STATE_PAUSE = "pause"
STATE_SHOP = "shop"
STATE_GAME_OVER = "game_over"


class Engine:
    def __init__(self):
        pygame.init()
        self.settings: Settings = load_settings()
        self.save: SaveData = load_save()

        flags = pygame.FULLSCREEN if self.settings.fullscreen else pygame.SHOWN
        self.screen = pygame.display.set_mode(
            (C.SCREEN_WIDTH, C.SCREEN_HEIGHT), flags
        )
        pygame.display.set_caption(C.WINDOW_TITLE)
        self.clock = pygame.time.Clock()

        # Systems
        self.audio = AudioSystem(self.settings)
        self.particles = ParticleSystem()
        self.effects = EffectsSystem(self.settings)
        self.tracker = HandTracker(self.settings, src=0)
        self.shooting = ShootingSystem(self.particles, self.effects, self.audio)
        self.pickups = PickupSystem(self.audio)
        self.weather = WeatherSystem(self.settings)
        self.recorder = RecordingSystem()
        self.announcer = Announcer(self.settings)
        self.ar_mask = ARMaskSystem(self.settings)

        # Gameplay state
        self.weapons = build_loadout()
        self.player = Player(self.weapons, self.settings)
        self.waves = WaveDirector(self.particles, self.effects, self.audio,
                                  self.settings, mode=self.settings.chosen_mode)
        self.ui = UISystem(self.settings, self.save)
        self.enemy_bullets: list[EnemyBullet] = []
        self.stats: RunStats = RunStats()
        self._shop_bought: set = set()

        # State
        self.state = STATE_MENU
        self.menu_selected = 0
        self.pause_selected = 0
        self.settings_selected = 0
        self.mode_selected = 0
        self.shop_selected = 0
        self._settings_from_pause = False
        self._game_over_high = False
        self._wave_announced_for = 0
        self.running = True

        self._fps_smoothed = 60.0
        self._last_gesture = None
        # Boss-music tracking
        self._boss_alive_seen = False

    # Main loop
    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(C.TARGET_FPS) / 1000.0
                dt = min(dt, 1 / 20)
                self._fps_smoothed = self._fps_smoothed * 0.92 + (1.0 / max(dt, 1e-3)) * 0.08

                self._handle_events()
                gesture = self.tracker.poll()
                self._last_gesture = gesture
                # Forward latest frame to AR mask system on its own thread
                self.ar_mask.request(self.tracker.get_last_frame_bgr())

                if self.state == STATE_MENU:
                    self.ui.draw_main_menu(self.screen, self.menu_selected)
                elif self.state == STATE_MODE_SELECT:
                    self.ui.draw_mode_select(self.screen, self.mode_selected)
                elif self.state == STATE_SETTINGS:
                    self.ui.draw_settings_menu(self.screen, self.settings_selected,
                                               self._settings_items())
                elif self.state == STATE_CALIBRATE:
                    self._render_webcam_background(self.screen, opacity=180)
                    self.ui.draw_calibration(self.screen, gesture,
                                             self._calibration_text(gesture))
                elif self.state == STATE_PLAYING:
                    self._tick_playing(dt, gesture)
                elif self.state == STATE_PAUSE:
                    self._render_play_frame(0, gesture, frozen=True)
                    self.ui.draw_pause_menu(self.screen, self.pause_selected)
                elif self.state == STATE_SHOP:
                    self._render_play_frame(0, gesture, frozen=True)
                    self._draw_shop_overlay()
                elif self.state == STATE_GAME_OVER:
                    self._render_play_frame(0, gesture, frozen=True)
                    self.ui.draw_game_over(self.screen, self.player,
                                           self.waves.wave, self._game_over_high,
                                           stats=self.stats)

                self.recorder.capture(self.screen)
                pygame.display.flip()
        finally:
            self.shutdown()

    # State: PLAYING
    def _tick_playing(self, dt: float, gesture):
        sim_dt = dt * self.effects.time_scale

        if gesture and gesture.detected:
            self.player.aim_x = gesture.aim[0]
            self.player.aim_y = gesture.aim[1]
            if gesture.shoot_event:
                if self.shooting.try_fire(self.player,
                                          (self.player.aim_x, self.player.aim_y),
                                          self.waves.enemies,
                                          on_fire=self._on_fire):
                    self.stats.shots_fired += 1
                    self.save.total_shots_fired += 1
            if gesture.reload_event:
                self.shooting.reload(self.player)
            if gesture.grenade_event:
                self._on_grenade_kills(self.shooting.grenade(
                    self.player, (self.player.aim_x, self.player.aim_y),
                    self.waves.enemies))
            if gesture.special_event:
                self._on_grenade_kills(self.shooting.special(
                    self.player, (self.player.aim_x, self.player.aim_y),
                    self.waves.enemies))

        # Sim
        self.player.update(sim_dt)
        target_pos = (C.SCREEN_WIDTH / 2, C.SCREEN_HEIGHT / 2)
        # Pass live player bullets as "threats" so enemies can dodge them
        self.waves.update(sim_dt, target_pos, threats=self.shooting.bullets)
        # Boss arrival? — trigger cinematic intro + announcer roar
        if self.waves.consume_boss_entrance():
            self.effects.boss_intro()
            self.audio.play("boss_roar", volume=1.0)
            self.audio.play("bass_thump", volume=1.0)
            self.ui.show_wave_banner("BOSS INCOMING")
            self.announcer.say("Boss incoming")
        self.shooting.update(sim_dt, self.waves.enemies, self.player,
                             on_hit=self._on_hit, on_kill=self._on_kill,
                             headshot_only=(self.waves.mode == C.MODE_HEADSHOT_ONLY))
        self.particles.update(sim_dt)
        self.weather.update(dt)
        self.effects.update(dt)
        self.ui.update(dt)
        self._update_enemy_attacks(sim_dt, target_pos)
        self._update_enemy_bullets(sim_dt)
        self.pickups.update(sim_dt, (self.player.aim_x, self.player.aim_y),
                            self.player, on_collect=self._on_pickup)

        # Phase-based callouts
        if self.waves.phase == self.waves.PHASE_ACTIVE and self.waves.wave > 0:
            self._maybe_announce_wave()

        # Shop trigger at end of wave (skip in time-attack / boss rush -> next)
        if (self.waves.phase == self.waves.PHASE_BREAK
                and not self.waves.shop_open
                and self.waves.mode not in (C.MODE_TIME_ATTACK,)):
            self._open_shop()

        # Low-health heartbeat (intensity scales with how low)
        if self.player.is_low_health and not self.player.is_dead:
            self.audio.play_heartbeat(intensity=self.player.low_health_intensity)

        # Dynamic music
        boss_alive = any(e.is_boss and e.alive for e in self.waves.enemies)
        if boss_alive and not self._boss_alive_seen:
            self.audio.set_music_mode("boss")
            self._boss_alive_seen = True
        elif not boss_alive and self._boss_alive_seen:
            self.audio.set_music_mode("calm")
            self._boss_alive_seen = False

        # Multi-kill announce
        callout = self.player.consume_multi_kill_callout()
        if callout:
            self.ui.show_multi_kill(callout)
            self.announcer.say(callout.title())
            self.stats.best_multi_kill = max(self.stats.best_multi_kill,
                                              self.player.multi_kill_count)

        if self.player.is_dead:
            self._enter_game_over()
        if (self.waves.mode == C.MODE_TIME_ATTACK
                and self.waves.phase == self.waves.PHASE_ENDED):
            self._enter_game_over()

        self._render_play_frame(dt, gesture)

    # Enemy melee + ranged
    def _update_enemy_attacks(self, dt: float, target_pos):
        for e in self.waves.enemies:
            if not e.alive:
                continue
            # Process pending projectiles produced this frame
            for x, y, vx, vy, dmg, homing in e.pull_pending_projectiles():
                self.enemy_bullets.append(EnemyBullet(x, y, vx, vy, dmg,
                                                       homing=homing))
                self.audio.play_at("hit", x, volume=0.4)
            # Process pending summons (boss_summoner)
            n = e.pull_pending_summons()
            for _ in range(n):
                self.waves.add_summoned(e.x, e.y)
            # Melee impact when berserker / zombie / fast / tank attack
            if not e.ranged and e.state == e.STATE_ATTACK and not e.is_boss:
                # Damage applied if very close at end of telegraph
                # This handles only one trigger per attack period because
                # telegraph -> attack -> next telegraph cycle.
                if (e.attack_cooldown >= (e.attack_period - 0.05)
                        and self._distance_to_player(e) < e.attack_range * 0.9):
                    self._enemy_hits_player(e, e.damage)
            if e.kind == "boss_berserker" and e.state == e.STATE_ATTACK:
                if (e.attack_cooldown >= (e.attack_period - 0.05)
                        and self._distance_to_player(e) < e.attack_range * 0.95):
                    self._enemy_hits_player(e, e.damage)

    def _update_enemy_bullets(self, dt: float):
        center = (C.SCREEN_WIDTH / 2, C.SCREEN_HEIGHT / 2)
        player_rect = pygame.Rect(int(center[0]) - 50, int(center[1]) - 50,
                                   100, 100)
        for b in self.enemy_bullets:
            b.update(dt, center)
            if not b.alive:
                continue
            if b.x < -40 or b.x > C.SCREEN_WIDTH + 40:
                b.alive = False
                continue
            if b.y < -40 or b.y > C.SCREEN_HEIGHT + 40:
                b.alive = False
                continue
            if b.hit_test_target_box(player_rect):
                if self.player.take_damage(b.damage, source_pos=(b.x, b.y)):
                    self.effects.shake(6)
                    self.effects.flash(color=(220, 30, 30),
                                       duration=C.DAMAGE_FLASH_TIME)
                    self.stats.damage_taken += b.damage
                    self.stats.wave_damage_taken += b.damage
                    self.audio.play("hit", volume=0.7)
                b.alive = False
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

    def _enemy_hits_player(self, enemy, dmg: float):
        if self.player.take_damage(dmg, source_pos=(enemy.x, enemy.y)):
            self.effects.shake(7 + dmg * 0.15)
            self.effects.flash(color=(220, 30, 30),
                               duration=C.DAMAGE_FLASH_TIME)
            self.particles.spawn_explosion(C.SCREEN_WIDTH / 2,
                                            C.SCREEN_HEIGHT / 2,
                                            color=(255, 60, 80))
            self.stats.damage_taken += dmg
            self.stats.wave_damage_taken += dmg
        # Prevent multi-hit on same attack period
        enemy.attack_cooldown = enemy.attack_period * 0.8

    @staticmethod
    def _distance_to_player(enemy) -> float:
        dx = enemy.x - C.SCREEN_WIDTH / 2
        dy = enemy.y - C.SCREEN_HEIGHT / 2
        return math.hypot(dx, dy)

    # Rendering
    def _render_play_frame(self, dt: float, gesture, frozen: bool = False):
        # 1) Webcam background
        self._render_webcam_background(self.screen)
        # 2) AR mask darkens the player silhouette area (so enemies look behind)
        if self.settings.ar_occlusion and self.state == STATE_PLAYING:
            self.ar_mask.darken_inside_mask(self.screen)
        # 3) Weather BG
        self.weather.draw_background(self.screen)

        shake = self.effects.shake_offset()
        layer = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)

        # 4) Enemies
        self.waves.draw(layer)
        # 5) Pickups (between enemies and bullets so they shimmer in front)
        self.pickups.draw(layer)
        # 6) Bullets (player + enemy)
        self.shooting.draw(layer)
        for eb in self.enemy_bullets:
            eb.draw(layer)
        # 7) Particles
        self.particles.draw(layer)
        # 8) Weapon FP — 2D recoil + reload dip
        self.player.weapon.draw_first_person(
            layer,
            recoil_y=self.player.recoil_y,
            recoil_x=self.player.recoil_x,
            bob_offset=self.player.bob_offset(),
            reload_dip=self.player.reload_dip(),
        )
        # 9) Crosshair (spread now includes recoil)
        spread = self.player.weapon.spread + self.player.recoil_y * 0.0015
        target = (self.player.aim_x, self.player.aim_y)
        self.ui.draw_crosshair(layer, target, spread)
        # 10) Weather FG (rain/lightning)
        self.weather.draw_foreground(layer)

        # View kick (camera punch) — applied to the world layer as a small
        # additional offset on top of the random shake
        vkx, vky = self.player.view_offset()
        self.screen.blit(layer, (shake[0] + vkx, shake[1] + vky))

        # 11) HUD
        time_attack_remaining = None
        if self.waves.mode == C.MODE_TIME_ATTACK and self.state == STATE_PLAYING:
            time_attack_remaining = self.waves._time_attack_remaining
        self.ui.draw_hud(self.screen, self.player, self.waves,
                         self._fps_smoothed, gesture,
                         recording_active=self.recorder.recording,
                         recording_time=self.recorder.elapsed_seconds(),
                         time_attack_remaining=time_attack_remaining)

        # 12) Post effects
        slowmo_pwr = self.player.is_effect_active(C.PICKUP_SLOWMO)
        # Sniper zoom: ramps in when sniper is equipped + the gun isn't kicking
        sniper_zoom = 0.0
        if (self.state == STATE_PLAYING
                and self.player.weapon.kind == "sniper"
                and self.player.recoil_y < 3.0):
            sniper_zoom = 1.0
        self.effects.draw_overlays(self.screen, self.player.low_health_intensity,
                                   self.player.last_damage_dir, dt,
                                   slowmo_powerup_on=slowmo_pwr,
                                   sniper_zoom=sniper_zoom)

    # Webcam background
    def _render_webcam_background(self, target: pygame.Surface, opacity: int = 255):
        frame = self.tracker.get_last_frame_bgr()
        if frame is None or not self.settings.show_webcam:
            target.fill((10, 14, 20))
            return
        try:
            resized = cv2.resize(frame, (C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        except Exception:
            target.fill((10, 14, 20))
            return
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        blended = cv2.addWeighted(resized, 0.55, gray_bgr, 0.45, -20)
        surf = cv2_frame_to_surface(blended)
        if opacity < 255:
            surf.set_alpha(opacity)
        target.blit(surf, (0, 0))

    # Events
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type != pygame.KEYDOWN:
                continue

            # Global hotkeys (work in any state)
            if event.key == pygame.K_F12:
                self._take_screenshot()
                continue
            if event.key == pygame.K_F9:
                path = self.recorder.toggle()
                if path:
                    self.ui.popup(f"Saved: {path}", seconds=2.5)
                else:
                    self.ui.popup("Recording started (F9 to stop)", seconds=2.0)
                continue
            if event.key == pygame.K_t and self.state == STATE_PLAYING:
                self.settings.show_tutorial = False
                save_settings(self.settings)
                continue

            if self.state == STATE_MENU:
                self._menu_keys(event)
            elif self.state == STATE_MODE_SELECT:
                self._mode_select_keys(event)
            elif self.state == STATE_SETTINGS:
                self._settings_keys(event)
            elif self.state == STATE_CALIBRATE:
                if event.key == pygame.K_ESCAPE:
                    self.state = STATE_MENU
                    self.audio.play("click")
            elif self.state == STATE_PLAYING:
                self._playing_keys(event)
            elif self.state == STATE_PAUSE:
                self._pause_keys(event)
            elif self.state == STATE_SHOP:
                self._shop_keys(event)
            elif self.state == STATE_GAME_OVER:
                if event.key == pygame.K_RETURN:
                    self._start_game()
                elif event.key == pygame.K_ESCAPE:
                    self.state = STATE_MENU
                    self.audio.play("click")

    def _menu_keys(self, event):
        items_count = 5
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_selected = (self.menu_selected + 1) % items_count
            self.audio.play("click")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.menu_selected = (self.menu_selected - 1) % items_count
            self.audio.play("click")
        elif event.key == pygame.K_RETURN:
            self.audio.play("click")
            if self.menu_selected == 0:
                self._start_game()
            elif self.menu_selected == 1:
                self.state = STATE_MODE_SELECT
                # initialize selection to current
                for i, (mid, _, _) in enumerate(C.GAME_MODES):
                    if mid == self.settings.chosen_mode:
                        self.mode_selected = i
                        break
            elif self.menu_selected == 2:
                self.state = STATE_SETTINGS
                self.settings_selected = 0
                self._settings_from_pause = False
            elif self.menu_selected == 3:
                self.state = STATE_CALIBRATE
            elif self.menu_selected == 4:
                self.running = False
        elif event.key == pygame.K_ESCAPE:
            self.running = False

    def _mode_select_keys(self, event):
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.mode_selected = (self.mode_selected + 1) % len(C.GAME_MODES)
            self.audio.play("click")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.mode_selected = (self.mode_selected - 1) % len(C.GAME_MODES)
            self.audio.play("click")
        elif event.key == pygame.K_RETURN:
            self.settings.chosen_mode = C.GAME_MODES[self.mode_selected][0]
            save_settings(self.settings)
            self.audio.play("click")
            self.state = STATE_MENU
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_MENU
            self.audio.play("click")

    def _settings_keys(self, event):
        items = self._settings_items()
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.settings_selected = (self.settings_selected + 1) % len(items)
            self.audio.play("click")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.settings_selected = (self.settings_selected - 1) % len(items)
            self.audio.play("click")
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._change_setting(self.settings_selected, -1)
            self.audio.play("click")
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._change_setting(self.settings_selected, +1)
            self.audio.play("click")
        elif event.key == pygame.K_ESCAPE:
            save_settings(self.settings)
            self.audio.update_music_volume()
            self.weather.reload()
            self.state = STATE_PAUSE if self._settings_from_pause else STATE_MENU
            self.audio.play("click")

    def _playing_keys(self, event):
        if event.key == pygame.K_ESCAPE:
            self.state = STATE_PAUSE
            self.pause_selected = 0
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            idx = int(event.unicode) - 1
            if self.player.switch_weapon(idx, set(self.save.unlocked_weapons)):
                self.audio.play("click")
            else:
                self.audio.play("click", volume=0.4)
        elif event.key == pygame.K_q:
            self.player.next_weapon(set(self.save.unlocked_weapons))
            self.audio.play("click")
        elif event.key == pygame.K_r:
            self.shooting.reload(self.player)
        elif event.key == pygame.K_SPACE:
            if self.shooting.try_fire(self.player,
                                      (self.player.aim_x, self.player.aim_y),
                                      self.waves.enemies,
                                      on_fire=self._on_fire):
                self.stats.shots_fired += 1
                self.save.total_shots_fired += 1
        elif event.key == pygame.K_g:
            self._on_grenade_kills(self.shooting.grenade(
                self.player, (self.player.aim_x, self.player.aim_y),
                self.waves.enemies))
        elif event.key == pygame.K_e:
            self._on_grenade_kills(self.shooting.special(
                self.player, (self.player.aim_x, self.player.aim_y),
                self.waves.enemies))

    def _pause_keys(self, event):
        items = ["RESUME", "SETTINGS", "MAIN MENU"]
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.pause_selected = (self.pause_selected + 1) % len(items)
            self.audio.play("click")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.pause_selected = (self.pause_selected - 1) % len(items)
            self.audio.play("click")
        elif event.key == pygame.K_RETURN:
            self.audio.play("click")
            if self.pause_selected == 0:
                self.state = STATE_PLAYING
            elif self.pause_selected == 1:
                self.state = STATE_SETTINGS
                self.settings_selected = 0
                self._settings_from_pause = True
            elif self.pause_selected == 2:
                save_save(self.save)
                self.state = STATE_MENU
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_PLAYING

    def _shop_keys(self, event):
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.shop_selected = (self.shop_selected + 1) % len(C.SHOP_ITEMS)
            self.audio.play("click")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.shop_selected = (self.shop_selected - 1) % len(C.SHOP_ITEMS)
            self.audio.play("click")
        elif event.key == pygame.K_RETURN:
            self._buy_shop_item(C.SHOP_ITEMS[self.shop_selected])
        elif event.key in (pygame.K_c, pygame.K_ESCAPE):
            self._close_shop()

    # Settings
    def _settings_items(self):
        s = self.settings
        return [
            ("Master Volume",   f"{int(s.master_volume * 100)}%"),
            ("Music Volume",    f"{int(s.music_volume * 100)}%"),
            ("SFX Volume",      f"{int(s.sfx_volume * 100)}%"),
            ("Fullscreen",      "ON" if s.fullscreen else "OFF"),
            ("Show FPS",        "ON" if s.show_fps else "OFF"),
            ("Show Minimap",    "ON" if s.show_minimap else "OFF"),
            ("Show Webcam",     "ON" if s.show_webcam else "OFF"),
            ("Mirror Camera",   "ON" if s.invert_x else "OFF"),
            ("Aim Assist",      f"{int(s.aim_assist * 100)}%"),
            ("Hand Smoothing",  f"{int(s.smoothing_alpha * 100)}%"),
            ("Difficulty",      s.difficulty.upper()),
            ("Crosshair Style", s.crosshair_style.upper()),
            ("Crosshair Color", s.crosshair_color.upper()),
            ("Weather",         s.weather.upper()),
            ("Bloom",           "ON" if s.bloom else "OFF"),
            ("Spatial Audio",   "ON" if s.spatial_audio else "OFF"),
            ("Voice Announcer", ("ON" if s.voice_announcer else "OFF")
                                + ("" if self.announcer.available else "  (pyttsx3 not installed)")),
            ("AR Body Occlusion", ("ON" if s.ar_occlusion else "OFF")
                                  + ("" if self.ar_mask.available else "  (unavailable)")),
            ("Show Tutorial",   "ON" if s.show_tutorial else "OFF"),
        ]

    def _change_setting(self, idx: int, direction: int):
        s = self.settings
        step = 0.05
        if idx == 0:
            s.master_volume = clamp(s.master_volume + direction * step, 0, 1)
        elif idx == 1:
            s.music_volume = clamp(s.music_volume + direction * step, 0, 1)
        elif idx == 2:
            s.sfx_volume = clamp(s.sfx_volume + direction * step, 0, 1)
        elif idx == 3:
            s.fullscreen = not s.fullscreen
            flags = pygame.FULLSCREEN if s.fullscreen else pygame.SHOWN
            self.screen = pygame.display.set_mode(
                (C.SCREEN_WIDTH, C.SCREEN_HEIGHT), flags)
        elif idx == 4:
            s.show_fps = not s.show_fps
        elif idx == 5:
            s.show_minimap = not s.show_minimap
        elif idx == 6:
            s.show_webcam = not s.show_webcam
        elif idx == 7:
            s.invert_x = not s.invert_x
        elif idx == 8:
            s.aim_assist = clamp(s.aim_assist + direction * step, 0, 1)
        elif idx == 9:
            s.smoothing_alpha = clamp(s.smoothing_alpha + direction * step, 0.1, 0.95)
        elif idx == 10:
            order = ["easy", "normal", "hard"]
            cur = order.index(s.difficulty) if s.difficulty in order else 1
            s.difficulty = order[(cur + direction) % len(order)]
        elif idx == 11:
            cur = C.CROSSHAIR_STYLES.index(s.crosshair_style) \
                if s.crosshair_style in C.CROSSHAIR_STYLES else 0
            s.crosshair_style = C.CROSSHAIR_STYLES[(cur + direction) % len(C.CROSSHAIR_STYLES)]
        elif idx == 12:
            colors = ["cyan", "green", "pink", "yellow", "red", "white"]
            cur = colors.index(s.crosshair_color) if s.crosshair_color in colors else 0
            s.crosshair_color = colors[(cur + direction) % len(colors)]
        elif idx == 13:
            cur = C.WEATHER_OPTIONS.index(s.weather) \
                if s.weather in C.WEATHER_OPTIONS else 0
            s.weather = C.WEATHER_OPTIONS[(cur + direction) % len(C.WEATHER_OPTIONS)]
        elif idx == 14:
            s.bloom = not s.bloom
        elif idx == 15:
            s.spatial_audio = not s.spatial_audio
        elif idx == 16:
            s.voice_announcer = not s.voice_announcer
        elif idx == 17:
            s.ar_occlusion = not s.ar_occlusion
        elif idx == 18:
            s.show_tutorial = not s.show_tutorial
        s.clamp()
        self.audio.update_music_volume()
        self.weather.reload()

    # Game flow
    def _enter_state(self, new_state: str):
        """State transition with a brief fade so it feels cinematic."""
        if new_state != self.state:
            self.effects.start_fade()
        self.state = new_state

    def _start_game(self):
        # Daily challenge seed: deterministic when today's date hasn't been
        # used yet, otherwise random.
        today_seed = int(_dt.now().strftime("%Y%m%d"))
        if self.save.last_daily_seed != today_seed:
            random.seed(today_seed)
            self.save.last_daily_seed = today_seed
            self.ui.popup("DAILY CHALLENGE: deterministic seed", seconds=2.5)
        else:
            random.seed()  # back to OS randomness for replays today

        self.weapons = build_loadout()
        self.player = Player(self.weapons, self.settings)
        if 1 not in self.save.unlocked_weapons:
            self.save.unlocked_weapons.append(1)
        self.waves = WaveDirector(self.particles, self.effects, self.audio,
                                  self.settings, mode=self.settings.chosen_mode)
        self.waves.start()
        self.particles.particles.clear()
        self.shooting.bullets.clear()
        self.enemy_bullets.clear()
        self.pickups.clear()
        self.stats = RunStats()
        self._shop_bought = set()
        self._enter_state(STATE_PLAYING)
        self.ui.show_wave_banner("INCOMING...")
        self._wave_announced_for = 0
        self._game_over_high = False
        self._boss_alive_seen = False
        self.save.games_played += 1
        save_save(self.save)
        if self.settings.chosen_mode != C.MODE_SURVIVAL:
            mode_label = self.ui._mode_label(self.settings.chosen_mode)
            self.announcer.say(mode_label.lower())

    def _maybe_announce_wave(self):
        if self.waves.wave != self._wave_announced_for:
            self._wave_announced_for = self.waves.wave
            self.ui.show_wave_banner(f"WAVE {self.waves.wave}")
            self.announcer.say(f"Wave {self.waves.wave}")
            if self.waves.is_boss_wave:
                self.ui.show_wave_banner(f"WAVE {self.waves.wave} - BOSS")
                self.announcer.say("Boss incoming")
            # Reset wave-perfect tracker
            self.stats.wave_damage_taken = 0.0

    def _open_shop(self):
        self.waves.shop_open = True
        self.state = STATE_SHOP
        self.shop_selected = 0

    def _close_shop(self):
        # Award perfect-wave bonus if no damage taken this wave
        if self.stats.wave_damage_taken <= 0.0:
            self.stats.perfect_waves += 1
            self.player.coins += 50
            self.ui.popup("PERFECT WAVE  +50", seconds=1.8)
        self.stats.wave_damage_taken = 0.0
        self.waves.close_shop()
        self.state = STATE_PLAYING

    def _draw_shop_overlay(self):
        items_state = []
        for item in C.SHOP_ITEMS:
            owned = item["id"] in self._shop_bought and item["id"].startswith(
                ("max_", "fast_", "extra_", "unlock_"))
            can = self.player.coins >= item["cost"] and not owned
            items_state.append((item, can))
        self.ui.draw_shop(self.screen, self.player, items_state,
                          self.shop_selected, self._shop_bought)

    def _buy_shop_item(self, item):
        if item["id"] in self._shop_bought and item["id"].startswith(
                ("max_", "fast_", "extra_", "unlock_")):
            self.audio.play("click", volume=0.4)
            return
        if self.player.coins < item["cost"]:
            self.audio.play("click", volume=0.4)
            return
        self.player.coins -= item["cost"]
        self.stats.coins_spent += item["cost"]
        self._shop_bought.add(item["id"])
        self.audio.play("shop_buy")
        iid = item["id"]
        if iid == "heal_full":
            self.player.heal_full()
        elif iid == "armor_full":
            self.player.armor_full()
        elif iid == "ammo_refill":
            for w in self.player.weapons:
                w.refill_full()
        elif iid == "max_hp":
            self.player.increase_max_health(25)
        elif iid == "max_armor":
            self.player.increase_max_armor(25)
        elif iid == "fast_reload":
            for w in self.player.weapons:
                cur = getattr(w, "_shop_reload_mul", 1.0)
                w._shop_reload_mul = cur * 0.7
        elif iid == "extra_dmg":
            for w in self.player.weapons:
                cur = getattr(w, "_shop_dmg_mul", 1.0)
                w._shop_dmg_mul = cur * 1.15
        elif iid == "fast_fire":
            for w in self.player.weapons:
                cur = getattr(w, "_shop_fire_rate_mul", 1.0)
                w._shop_fire_rate_mul = cur * 1.15
        elif iid == "unlock_shotgun":
            if 2 not in self.save.unlocked_weapons:
                self.save.unlocked_weapons.append(2)
                self.ui.popup(f"UNLOCKED: {self.weapons[2].name}", seconds=2.0)
        elif iid == "unlock_sniper":
            if 3 not in self.save.unlocked_weapons:
                self.save.unlocked_weapons.append(3)
                self.ui.popup(f"UNLOCKED: {self.weapons[3].name}", seconds=2.0)

    # ----- on_* callbacks -----
    def _on_fire(self, weapon):
        # placeholder for per-shot stat tracking (already counted in stats)
        pass

    def _on_hit(self, enemy, headshot: bool, killed: bool, is_crit: bool = False):
        self.stats.shots_hit += 1
        self.save.total_shots_hit += 1
        self.stats.damage_dealt += int(enemy.score_value * 0.05)
        if is_crit:
            # Tiny gold flash to sell the crit
            self.effects.flash(color=(255, 220, 80), duration=0.08)

    def _on_kill(self, enemy, headshot: bool):
        # Apply player damage multiplier reflected in weapon already, but
        # score still uses the base + multipliers in Player.add_score.
        gained = self.player.add_score(enemy.score_value, headshot=headshot)
        self.player.register_kill(headshot=headshot)
        self.waves.notify_kill()
        self.stats.kills += 1
        if headshot:
            self.stats.headshots += 1
            self.save.total_headshots += 1
        self.stats.best_combo = max(self.stats.best_combo, self.player.combo)
        self.stats.coins_earned += C.COIN_PER_KILL
        self.save.best_killstreak = max(self.save.best_killstreak,
                                         self.player.killstreak)
        kind = enemy.kind.upper().replace("_", " ")
        suffix = "  HEADSHOT" if headshot else ""
        self.ui.add_kill(f"+{gained}  -  {kind}{suffix}")
        # FX
        self.particles.spawn_explosion(enemy.x, enemy.y,
                                        color=enemy.color, big=enemy.is_boss)
        self.audio.play_at("enemy_death", enemy.x, volume=0.7)
        # Drops
        self.pickups.maybe_drop(enemy.x, enemy.y, is_boss=enemy.is_boss)
        if enemy.is_boss:
            self.effects.shake(20)
            self.effects.slowmo(0.6)
            self.audio.play("explosion", volume=1.0)
            self.ui.show_wave_banner("BOSS DOWN")
            self.announcer.say("Boss eliminated")
            self.save.boss_kills += 1
        # Unlock weapons by score milestones
        for idx, threshold in C.WEAPON_UNLOCK_SCORE.items():
            if (idx not in self.save.unlocked_weapons
                    and self.player.score >= threshold):
                self.save.unlocked_weapons.append(idx)
                self.ui.popup(f"UNLOCKED: {self.weapons[idx].name}", seconds=2.0)
        self._check_achievements(killed_boss=enemy.is_boss,
                                 was_headshot=headshot)

    def _on_grenade_kills(self, n: int):
        if n <= 0:
            return
        for _ in range(n):
            self.player.add_score(150)
            self.player.register_kill(headshot=False)
            self.waves.notify_kill()
            self.stats.kills += 1
        self.ui.add_kill(f"+{n}  -  AREA CLEAR")

    def _on_pickup(self, kind: str, label: str):
        self.ui.popup(label, seconds=1.2)
        if kind in (C.PICKUP_HEALTH, C.PICKUP_ARMOR):
            self.announcer.say("Refilled")
        elif kind == C.PICKUP_DOUBLE_DAMAGE:
            self.announcer.say("Double damage")
        elif kind == C.PICKUP_SHIELD:
            self.announcer.say("Shield")
        elif kind == C.PICKUP_SLOWMO:
            self.announcer.say("Bullet time")
        elif kind == C.PICKUP_FIRE_RATE:
            self.announcer.say("Rapid fire")

    def _check_achievements(self, killed_boss=False, was_headshot=False):
        a = self.save.achievements
        if "first_blood" not in a:
            a["first_blood"] = True
            self.ui.show_achievement("First Blood")
        if was_headshot and self.player.headshots >= 10 and "headhunter" not in a:
            a["headhunter"] = True
            self.ui.show_achievement("Headhunter")
        if self.player.killstreak >= 15 and "unstoppable" not in a:
            a["unstoppable"] = True
            self.ui.show_achievement("Unstoppable")
        if self.waves.wave >= 10 and "wave_master" not in a:
            a["wave_master"] = True
            self.ui.show_achievement("Wave Master")
        if killed_boss and "boss_slayer" not in a:
            a["boss_slayer"] = True
            self.ui.show_achievement("Boss Slayer")
        if len(set(self.save.unlocked_weapons)) >= 4 and "arsenal" not in a:
            a["arsenal"] = True
            self.ui.show_achievement("Full Arsenal")
        if self.player.multi_kill_count >= 10 and "godlike" not in a:
            a["godlike"] = True
            self.ui.show_achievement("Godlike")
        if self.stats.coins_earned >= 3000 and "rich" not in a:
            a["rich"] = True
            self.ui.show_achievement("Big Spender")
        if (self.stats.perfect_waves >= 1 and "survivor" not in a):
            a["survivor"] = True
            self.ui.show_achievement("Survivor")
        if (self.stats.shots_fired >= 50
                and self.stats.accuracy() >= 0.85
                and "perfect_aim" not in a):
            a["perfect_aim"] = True
            self.ui.show_achievement("Perfect Aim")

    def _enter_game_over(self):
        self._game_over_high = self.player.score > self.save.high_score
        if self._game_over_high:
            self.save.high_score = self.player.score
        today_seed = int(_dt.now().strftime("%Y%m%d"))
        if self.save.last_daily_seed == today_seed:
            self.save.daily_high_score = max(self.save.daily_high_score,
                                              self.player.score)
        self.save.highest_wave = max(self.save.highest_wave, self.waves.wave)
        self.save.total_kills += self.player.kills
        self.save.total_coins += self.player.coins
        save_save(self.save)
        save_stats_snapshot(self.stats)
        self._enter_state(STATE_GAME_OVER)

    # Misc
    def _take_screenshot(self):
        C.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        path = C.SCREENSHOT_DIR / f"phantom_strike_{stamp}.png"
        try:
            pygame.image.save(self.screen, str(path))
            self.ui.popup(f"Screenshot: {path.name}", seconds=2.0)
        except Exception:
            self.ui.popup("Screenshot failed", seconds=1.5)

    def _calibration_text(self, gesture) -> str:
        if not gesture or not gesture.detected:
            return "No hand detected. Place your hand in front of the camera."
        return (f"Pinch: {gesture.pinch_distance:.3f}    "
                f"Fist: {'YES' if gesture.fist_closed else 'no'}    "
                f"Peace: {'YES' if gesture.peace_sign else 'no'}    "
                f"Two hands: {'YES' if gesture.two_hands else 'no'}")

    def shutdown(self):
        try:
            save_settings(self.settings)
            save_save(self.save)
        except Exception:
            pass
        try:
            if self.recorder.recording:
                self.recorder.stop()
        except Exception:
            pass
        try:
            self.ar_mask.shutdown()
        except Exception:
            pass
        try:
            self.announcer.shutdown()
        except Exception:
            pass
        try:
            self.tracker.release()
        except Exception:
            pass
        try:
            self.audio.shutdown()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
