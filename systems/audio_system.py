"""
Audio system — procedural fallback synthesis, spatial stereo panning,
weapon-specific reload variants, dynamic music swap (calm vs boss).
"""

import os
import threading
import time

import pygame

from core import constants as C
from core.utils import (find_sound_file, safe_load_sound, stereo_pan,
                        synth_ambient_loop, synth_ammo_pickup, synth_bass_thump,
                        synth_boss_loop, synth_boss_roar, synth_click,
                        synth_crit_hit, synth_enemy_death, synth_enemy_growl,
                        synth_explosion, synth_gunshot_layered, synth_heartbeat,
                        synth_hit, synth_powerup, synth_reload,
                        synth_reload_bolt, synth_reload_pump, synth_shop_buy)


class AudioSystem:
    NUM_CHANNELS = 24

    def __init__(self, settings):
        self.settings = settings
        self._sounds: dict = {}
        self._music_channel = None
        self._music_calm = None
        self._music_boss = None
        self._music_mode: str = "calm"   # "calm" or "boss"
        self._last_heartbeat = 0.0
        self._init_ok = False

        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.quit()
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(self.NUM_CHANNELS)
            self._init_ok = True
        except Exception:
            self._init_ok = False
            return

        self._build_sound_bank()
        self._start_music()

    def _make_sound(self, name: str, synth_callable):
        # Look for assets/sounds/{name}.{wav|mp3|ogg} first; synthesize otherwise.
        sounds_dir = os.path.join(C.ASSETS_DIR, "sounds")
        path = find_sound_file(sounds_dir, name)
        snd = safe_load_sound(path) if path else None
        if snd is None:
            try:
                arr = synth_callable()
                snd = pygame.sndarray.make_sound(arr)
            except Exception:
                snd = None
        self._sounds[name] = snd

    def _build_sound_bank(self):
        # Layered gunshots — much fuller than single-noise bursts
        self._make_sound("shoot_pistol",  lambda: synth_gunshot_layered("pistol"))
        self._make_sound("shoot_rifle",   lambda: synth_gunshot_layered("rifle"))
        self._make_sound("shoot_shotgun", lambda: synth_gunshot_layered("shotgun"))
        self._make_sound("shoot_sniper",  lambda: synth_gunshot_layered("sniper"))
        # Weapon-specific reloads
        self._make_sound("reload_pistol", lambda: synth_reload(0.16, freq=1300))
        self._make_sound("reload_rifle",  lambda: synth_reload(0.20, freq=900))
        self._make_sound("reload_shotgun", synth_reload_pump)
        self._make_sound("reload_sniper",  synth_reload_bolt)
        # Generic
        self._make_sound("hit", synth_hit)
        self._make_sound("crit", synth_crit_hit)
        self._make_sound("bass_thump", synth_bass_thump)
        self._make_sound("boss_roar", synth_boss_roar)
        self._make_sound("explosion", synth_explosion)
        self._make_sound("click", synth_click)
        self._make_sound("enemy", synth_enemy_growl)
        self._make_sound("enemy_death", synth_enemy_death)
        self._make_sound("heartbeat", synth_heartbeat)
        self._make_sound("powerup", synth_powerup)
        self._make_sound("ammo_pickup", synth_ammo_pickup)
        self._make_sound("shop_buy", synth_shop_buy)

    def _start_music(self):
        threading.Thread(target=self._music_worker, daemon=True).start()

    def _music_worker(self):
        try:
            self._music_calm = pygame.sndarray.make_sound(synth_ambient_loop(6.0))
            self._music_boss = pygame.sndarray.make_sound(synth_boss_loop(6.0))
            self._music_channel = pygame.mixer.Channel(self.NUM_CHANNELS - 1)
            self._music_channel.set_volume(self.settings.master_volume *
                                            self.settings.music_volume)
            self._music_channel.play(self._music_calm, loops=-1)
        except Exception:
            self._music_channel = None

    @property
    def ready(self) -> bool:
        return self._init_ok

    def play(self, name: str, volume: float = 1.0, pan_x: float = 0.5):
        if not self._init_ok:
            return
        snd = self._sounds.get(name)
        if snd is None:
            return
        try:
            base = self.settings.master_volume * self.settings.sfx_volume * volume
            ch = pygame.mixer.find_channel(force=True)
            if ch is None:
                return
            if self.settings.spatial_audio:
                left = max(0.0, min(1.0, (1.0 - pan_x))) * base
                right = max(0.0, min(1.0, pan_x)) * base
                ch.set_volume(left, right)
            else:
                ch.set_volume(base)
            ch.play(snd)
        except Exception:
            pass

    def play_at(self, name: str, screen_x: float, volume: float = 1.0):
        """Spatial pan based on x position on the game window."""
        left, right = stereo_pan(screen_x, C.SCREEN_WIDTH)
        # Convert to "pan_x" (0=left, 1=right)
        pan_x = right
        self.play(name, volume=volume, pan_x=pan_x)

    def play_shoot(self, weapon_kind: str):
        mapping = {"pistol": "shoot_pistol", "rifle": "shoot_rifle",
                   "shotgun": "shoot_shotgun", "sniper": "shoot_sniper"}
        self.play(mapping.get(weapon_kind, "shoot_pistol"))

    def play_reload(self, weapon_kind: str):
        mapping = {"pistol": "reload_pistol", "rifle": "reload_rifle",
                   "shotgun": "reload_shotgun", "sniper": "reload_sniper"}
        self.play(mapping.get(weapon_kind, "reload_pistol"))

    def play_heartbeat(self, intensity: float = 1.0):
        now = time.time()
        interval = max(0.35, 0.85 - intensity * 0.5)
        if (now - self._last_heartbeat) < interval:
            return
        self._last_heartbeat = now
        self.play("heartbeat", volume=0.6 + intensity * 0.4)

    def set_music_mode(self, mode: str):
        """mode: 'calm' or 'boss'. Crossfades by replacing the loop."""
        if mode == self._music_mode or self._music_channel is None:
            return
        target = self._music_boss if mode == "boss" else self._music_calm
        if target is None:
            return
        try:
            self._music_channel.fadeout(400)
            # Schedule the replacement after fadeout — done synchronously via
            # a brief delay thread so we don't sleep in the main loop.
            threading.Thread(target=self._delayed_play, args=(target,),
                             daemon=True).start()
            self._music_mode = mode
        except Exception:
            pass

    def _delayed_play(self, sound):
        try:
            time.sleep(0.45)
            self._music_channel.set_volume(self.settings.master_volume *
                                            self.settings.music_volume)
            self._music_channel.play(sound, loops=-1)
        except Exception:
            pass

    def update_music_volume(self):
        if self._music_channel is not None:
            try:
                self._music_channel.set_volume(
                    self.settings.master_volume * self.settings.music_volume
                )
            except Exception:
                pass

    def shutdown(self):
        try:
            pygame.mixer.stop()
            pygame.mixer.quit()
        except Exception:
            pass
