"""
Math / drawing / asset helpers. Pure-functional where possible.
"""

import math
import os
import random
from typing import Tuple

import numpy as np
import pygame


Vec2 = Tuple[float, float]


# Math
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_vec(a: Vec2, b: Vec2, t: float) -> Vec2:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def distance(a: Vec2, b: Vec2) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_between(a: Vec2, b: Vec2) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def vector_from_angle(angle: float, magnitude: float = 1.0) -> Vec2:
    return (math.cos(angle) * magnitude, math.sin(angle) * magnitude)


def normalize(v: Vec2) -> Vec2:
    m = math.hypot(v[0], v[1])
    if m < 1e-9:
        return (0.0, 0.0)
    return (v[0] / m, v[1] / m)


def ease_out_quad(t: float) -> float:
    return 1 - (1 - t) * (1 - t)


def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def stereo_pan(x_screen: float, screen_w: int) -> tuple:
    """Returns (left_vol, right_vol) for a sound at screen-x. Sum is constant."""
    t = clamp(x_screen / max(1, screen_w), 0.0, 1.0)
    left = math.cos(t * math.pi / 2)
    right = math.sin(t * math.pi / 2)
    return (left, right)


# Color helpers
COLOR_NAMES = {
    "cyan":   (0, 240, 255),
    "green":  (80, 255, 140),
    "pink":   (255, 60, 170),
    "yellow": (255, 220, 60),
    "red":    (255, 60, 70),
    "white":  (240, 240, 240),
}


def resolve_color_name(name: str) -> tuple:
    return COLOR_NAMES.get(name, COLOR_NAMES["cyan"])


# Drawing
def draw_text(surface, text, font, color, pos, center=False, shadow=True):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        rect = s.get_rect()
        if center:
            rect.center = (pos[0] + 2, pos[1] + 2)
        else:
            rect.topleft = (pos[0] + 2, pos[1] + 2)
        surface.blit(s, rect)
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(rendered, rect)
    return rect


def draw_rect_alpha(surface, color_rgba, rect, border_radius=0):
    shape = pygame.Surface((int(rect[2]), int(rect[3])), pygame.SRCALPHA)
    pygame.draw.rect(shape, color_rgba, shape.get_rect(), border_radius=border_radius)
    surface.blit(shape, (rect[0], rect[1]))


def draw_circle_alpha(surface, color_rgba, center, radius):
    size = int(radius * 2 + 2)
    if size <= 0:
        return
    shape = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(shape, color_rgba, (size // 2, size // 2), int(radius))
    surface.blit(shape, (int(center[0] - size // 2), int(center[1] - size // 2)))


def draw_glow_circle(surface, color_rgb, center, radius, layers=4, alpha=120):
    for i in range(layers, 0, -1):
        a = max(8, int(alpha * (i / layers) * 0.4))
        r = int(radius * (1 + i * 0.35))
        draw_circle_alpha(surface, (*color_rgb, a), center, r)


def draw_line_glow_safe(surface, color_rgba, start, end, width=2):
    """
    Cheap alpha line for many-per-frame use (bullet trails).
    Builds a small SRCALPHA surface only as large as the line's bbox.
    """
    sx, sy = start
    ex, ey = end
    x0, y0 = min(sx, ex), min(sy, ey)
    bw = max(2, int(abs(ex - sx)) + width * 2 + 2)
    bh = max(2, int(abs(ey - sy)) + width * 2 + 2)
    surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.line(
        surf, color_rgba,
        (sx - x0 + width, sy - y0 + width),
        (ex - x0 + width, ey - y0 + width),
        width,
    )
    surface.blit(surf, (x0 - width, y0 - width))


# Cheap bloom approximation
def apply_bloom(surface: pygame.Surface, strength: float = 0.35) -> None:
    """
    Downscale → upscale → additive blit. Cheap pseudo-bloom that brightens
    highlights and gives the cinematic glow look. Mutates `surface` in place.
    """
    w, h = surface.get_size()
    if w < 32 or h < 32:
        return
    # 1/4 size pass
    small = pygame.transform.smoothscale(surface, (w // 4, h // 4))
    # 1/8 size pass blurs further
    smaller = pygame.transform.smoothscale(small, (w // 8, h // 8))
    blur = pygame.transform.smoothscale(smaller, (w, h))
    blur.set_alpha(int(255 * clamp(strength, 0.0, 1.0)))
    surface.blit(blur, (0, 0), special_flags=pygame.BLEND_ADD)


# OpenCV <-> Pygame
def cv2_frame_to_surface(frame_bgr: np.ndarray) -> pygame.Surface:
    """Convert a BGR cv2 frame (HxWx3 uint8) to a pygame Surface."""
    rgb = frame_bgr[:, :, ::-1]
    return pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))


# Procedural audio (used when no .wav assets are present)
def _envelope(n: int, attack=0.005, decay=0.25, sample_rate=22050) -> np.ndarray:
    a = max(1, int(attack * sample_rate))
    d = max(1, int(decay * sample_rate))
    env = np.ones(n, dtype=np.float32)
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    if d < n:
        env[-d:] = np.linspace(1.0, 0.0, d, dtype=np.float32)
    else:
        env = np.linspace(1.0, 0.0, n, dtype=np.float32)
    return env


def _to_stereo_int16(samples: np.ndarray) -> np.ndarray:
    samples = np.clip(samples, -1.0, 1.0)
    s16 = (samples * 32767).astype(np.int16)
    return np.ascontiguousarray(np.column_stack([s16, s16]))


def synth_gunshot(duration=0.18, sample_rate=22050, body_freq=80, brightness=0.9):
    n = int(duration * sample_rate)
    noise = np.random.uniform(-1, 1, n).astype(np.float32) * brightness
    t = np.arange(n) / sample_rate
    body = np.sin(2 * np.pi * body_freq * t) * np.exp(-t * 28)
    env = _envelope(n, attack=0.002, decay=duration * 0.9, sample_rate=sample_rate)
    samples = (noise * 0.7 + body * 0.9) * env
    return _to_stereo_int16(samples)


def synth_reload(duration=0.12, sample_rate=22050, freq=1200):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    click = np.sign(np.sin(2 * np.pi * freq * t)) * np.exp(-t * 40) * 0.5
    return _to_stereo_int16(click)


def synth_reload_pump(sample_rate=22050):
    """Shotgun pump: two distinct clicks."""
    n = int(0.32 * sample_rate)
    t = np.arange(n) / sample_rate
    out = np.zeros(n, dtype=np.float32)
    for offset in (0.0, 0.14):
        idx = int(offset * sample_rate)
        if idx >= n:
            continue
        chunk_n = n - idx
        tt = np.arange(chunk_n) / sample_rate
        body = (np.random.uniform(-1, 1, chunk_n).astype(np.float32) * 0.6 +
                np.sin(2 * np.pi * 220 * tt) * 0.4)
        env = np.exp(-tt * 28)
        out[idx:] += body * env
    return _to_stereo_int16(out * 0.55)


def synth_reload_bolt(sample_rate=22050):
    """Sniper bolt action: scrape then chamber click."""
    n = int(0.45 * sample_rate)
    t = np.arange(n) / sample_rate
    scrape = np.random.uniform(-1, 1, n).astype(np.float32) * 0.4
    scrape *= np.linspace(1.0, 0.2, n) * (np.sin(2 * np.pi * 320 * t) * 0.5 + 0.5)
    click_idx = int(0.30 * sample_rate)
    if click_idx < n:
        tt = np.arange(n - click_idx) / sample_rate
        scrape[click_idx:] += np.sin(2 * np.pi * 900 * tt) * np.exp(-tt * 60) * 0.8
    return _to_stereo_int16(scrape * 0.55)


def synth_explosion(duration=0.55, sample_rate=22050):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    noise = np.random.uniform(-1, 1, n).astype(np.float32)
    rumble = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 4)
    env = np.exp(-t * 3)
    samples = (noise * 0.6 + rumble) * env
    return _to_stereo_int16(samples)


def synth_hit(duration=0.08, sample_rate=22050, freq=900):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    tone = np.sin(2 * np.pi * freq * t) * np.exp(-t * 35)
    return _to_stereo_int16(tone * 0.5)


def synth_gunshot_layered(weapon_kind: str, sample_rate=22050):
    """3-layer gunshot: sub-bass thump + mid crack + high tail.

    Sounds significantly more present than a single noise burst. Each weapon
    gets a different layer balance so they're distinct without sounding cheap.
    """
    profiles = {
        "pistol":  {"dur": 0.18, "boom_f": 95,  "boom_a": 0.55, "crack_a": 0.65, "tail_a": 0.35, "decay": 30},
        "rifle":   {"dur": 0.14, "boom_f": 80,  "boom_a": 0.45, "crack_a": 0.75, "tail_a": 0.50, "decay": 28},
        "shotgun": {"dur": 0.35, "boom_f": 50,  "boom_a": 0.95, "crack_a": 0.70, "tail_a": 0.65, "decay": 12},
        "sniper":  {"dur": 0.45, "boom_f": 40,  "boom_a": 1.0,  "crack_a": 0.55, "tail_a": 0.50, "decay": 9},
    }
    p = profiles.get(weapon_kind, profiles["pistol"])
    dur = p["dur"]
    n = int(dur * sample_rate)
    t = np.arange(n) / sample_rate
    # Sub-bass thump
    boom = np.sin(2 * np.pi * p["boom_f"] * t) * np.exp(-t * p["decay"]) * p["boom_a"]
    # Mid crack — filtered-noise-ish via shaped white noise
    noise = np.random.uniform(-1, 1, n).astype(np.float32)
    crack_env = np.exp(-t * (p["decay"] * 2.2))
    crack = noise * crack_env * p["crack_a"]
    # High tail — fast click that fades to a hiss
    tail = (np.random.uniform(-1, 1, n).astype(np.float32) * 0.5
            * np.exp(-t * (p["decay"] * 0.8)) * p["tail_a"]
            * (1 - np.exp(-t * 200)))
    samples = (boom + crack + tail) * _envelope(n, attack=0.001, decay=dur * 0.9,
                                                 sample_rate=sample_rate)
    # Soft clip for warmth
    samples = np.tanh(samples * 1.2) * 0.9
    return _to_stereo_int16(samples)


def synth_bass_thump(sample_rate=22050):
    """Low rumble — layered on top of big hits (boss damage, explosions)."""
    dur = 0.32
    n = int(dur * sample_rate)
    t = np.arange(n) / sample_rate
    pitch = np.exp(-t * 4) * 90 + 35    # pitch falls from 125Hz to 35Hz
    body = np.sin(2 * np.pi * pitch * t)
    env = np.exp(-t * 5)
    return _to_stereo_int16(body * env * 0.75)


def synth_crit_hit(sample_rate=22050):
    """Bright metallic ding for critical hits."""
    dur = 0.18
    n = int(dur * sample_rate)
    t = np.arange(n) / sample_rate
    # Two tones a perfect fifth apart, both decaying
    a = np.sin(2 * np.pi * 1320 * t) * 0.55
    b = np.sin(2 * np.pi * 1980 * t) * 0.45
    env = np.exp(-t * 14)
    return _to_stereo_int16((a + b) * env * 0.6)


def synth_boss_roar(sample_rate=22050):
    """Boss arrival roar — long, dissonant, terrifying."""
    dur = 1.4
    n = int(dur * sample_rate)
    t = np.arange(n) / sample_rate
    pitch = 60 + 25 * np.sin(2 * np.pi * 3.5 * t)
    growl = np.sin(2 * np.pi * pitch * t)
    second = np.sin(2 * np.pi * (pitch * 1.5) * t) * 0.4
    noise = np.random.uniform(-1, 1, n).astype(np.float32) * 0.5
    fade_in = np.minimum(1.0, t * 3.0)
    fade_out = np.exp(-(t - dur * 0.6) * 3.0)
    fade_out = np.where(t < dur * 0.6, 1.0, fade_out)
    env = fade_in * fade_out
    return _to_stereo_int16((growl + second + noise) * env * 0.55)


def synth_click(duration=0.05, sample_rate=22050):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    s = np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 70) * 0.35
    return _to_stereo_int16(s)


def synth_enemy_growl(duration=0.45, sample_rate=22050):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    base = np.sin(2 * np.pi * (70 + 30 * np.sin(2 * np.pi * 6 * t)) * t)
    noise = np.random.uniform(-1, 1, n).astype(np.float32) * 0.35
    env = np.exp(-t * 3.5)
    return _to_stereo_int16((base + noise) * env * 0.6)


def synth_enemy_death(duration=0.5, sample_rate=22050):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    pitch = np.exp(-t * 1.8) * 220
    tone = np.sin(2 * np.pi * pitch * t)
    noise = np.random.uniform(-1, 1, n).astype(np.float32) * 0.4
    env = np.exp(-t * 2.4)
    return _to_stereo_int16((tone + noise) * env * 0.6)


def synth_heartbeat(duration=0.9, sample_rate=22050, intensity=1.0):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    pulse = np.zeros_like(t)
    for offset in (0.0, 0.18):
        idx = int(offset * sample_rate)
        if idx < n:
            tt = np.arange(n - idx) / sample_rate
            pulse[idx:] += np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 25) * 0.8
    return _to_stereo_int16(pulse * intensity)


def synth_powerup(sample_rate=22050):
    n = int(0.35 * sample_rate)
    t = np.arange(n) / sample_rate
    sweep = np.sin(2 * np.pi * (400 + 1400 * t) * t)
    env = np.exp(-t * 6) + np.exp(-t * 2) * 0.4
    return _to_stereo_int16(sweep * env * 0.5)


def synth_ammo_pickup(sample_rate=22050):
    n = int(0.18 * sample_rate)
    t = np.arange(n) / sample_rate
    s = np.sin(2 * np.pi * 880 * t) + 0.5 * np.sin(2 * np.pi * 1320 * t)
    env = np.exp(-t * 18)
    return _to_stereo_int16(s * env * 0.4)


def synth_shop_buy(sample_rate=22050):
    n = int(0.25 * sample_rate)
    t = np.arange(n) / sample_rate
    s = (np.sin(2 * np.pi * 700 * t) + np.sin(2 * np.pi * 1050 * t)) * 0.5
    env = np.exp(-t * 12)
    return _to_stereo_int16(s * env * 0.5)


def synth_ambient_loop(duration=4.0, sample_rate=22050):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    base = (
        np.sin(2 * np.pi * 55 * t) * 0.35
        + np.sin(2 * np.pi * 82.4 * t) * 0.22
        + np.sin(2 * np.pi * 110 * t) * 0.18
    )
    shimmer = np.sin(2 * np.pi * 440 * t) * 0.04 * np.sin(2 * np.pi * 0.25 * t)
    samples = (base + shimmer) * 0.5
    fade = min(int(0.4 * sample_rate), n // 2)
    env = np.ones(n, dtype=np.float32)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    return _to_stereo_int16(samples * env)


def synth_boss_loop(duration=6.0, sample_rate=22050):
    """Heavier, more dissonant pad for boss fights."""
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    base = (
        np.sin(2 * np.pi * 41 * t) * 0.4
        + np.sin(2 * np.pi * 49 * t) * 0.3
        + np.sin(2 * np.pi * 73 * t) * 0.2
    )
    pulse = (np.sin(2 * np.pi * 1.2 * t) * 0.5 + 0.5)
    samples = base * pulse * 0.55
    fade = min(int(0.4 * sample_rate), n // 2)
    env = np.ones(n, dtype=np.float32)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    return _to_stereo_int16(samples * env)


# Asset loading (graceful fallback when file missing)
def safe_load_image(path, fallback_size=(64, 64), fallback_color=(80, 80, 100)):
    if os.path.isfile(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            pass
    surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
    surf.fill((*fallback_color, 255))
    return surf


def safe_load_sound(path):
    if os.path.isfile(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None
    return None


def find_sound_file(directory: str, name: str) -> str | None:
    """Look for `name.wav`, then `name.mp3`, then `name.ogg`. Returns the first
    existing path, or None. Lets users drop in any common audio format."""
    for ext in (".wav", ".mp3", ".ogg"):
        candidate = os.path.join(directory, f"{name}{ext}")
        if os.path.isfile(candidate):
            return candidate
    return None


def jitter(value, amount):
    return value + random.uniform(-amount, amount)


# Tweening helpers (animated UI numbers, bars)
def tween(current: float, target: float, rate: float, dt: float) -> float:
    """Exponential approach. rate ~ how fast (higher = quicker)."""
    if dt <= 0:
        return current
    k = 1.0 - math.exp(-rate * dt)
    return current + (target - current) * k


def apply_sensitivity_curve(speed: float, gain: float, max_speed: float = 4500.0) -> float:
    """Returns a multiplier that's 1.0 at zero speed and grows quadratically
    with speed, capped. Used to make small motions precise and big motions snappy."""
    s = clamp(speed / max_speed, 0.0, 1.0)
    return 1.0 + gain * (s * s)
