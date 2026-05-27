"""
Persisted user settings + savegame + run-stats. JSON-backed, fault tolerant.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Dict, List

from core.constants import (CROSSHAIR_STYLES, MODE_SURVIVAL, SAVE_FILE,
                             SETTINGS_FILE, STATS_FILE, WEATHER_NONE,
                             WEATHER_OPTIONS)


@dataclass
class Settings:
    master_volume: float = 0.8
    music_volume: float = 0.5
    sfx_volume: float = 0.85
    fullscreen: bool = False
    show_fps: bool = True
    show_minimap: bool = True
    show_webcam: bool = True
    invert_x: bool = True
    aim_assist: float = 0.18
    smoothing_alpha: float = 0.55
    difficulty: str = "normal"
    crosshair_style: str = "classic"
    crosshair_color: str = "cyan"        # cyan | green | pink | yellow | red | white
    bloom: bool = True
    weather: str = WEATHER_NONE
    spatial_audio: bool = True
    voice_announcer: bool = True
    show_tutorial: bool = True           # auto-flips off after first run
    ar_occlusion: bool = False
    chosen_mode: str = MODE_SURVIVAL

    def clamp(self):
        self.master_volume = max(0.0, min(1.0, self.master_volume))
        self.music_volume = max(0.0, min(1.0, self.music_volume))
        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume))
        self.aim_assist = max(0.0, min(1.0, self.aim_assist))
        self.smoothing_alpha = max(0.1, min(0.95, self.smoothing_alpha))
        if self.difficulty not in ("easy", "normal", "hard"):
            self.difficulty = "normal"
        if self.crosshair_style not in CROSSHAIR_STYLES:
            self.crosshair_style = "classic"
        if self.crosshair_color not in ("cyan", "green", "pink", "yellow", "red", "white"):
            self.crosshair_color = "cyan"
        if self.weather not in WEATHER_OPTIONS:
            self.weather = WEATHER_NONE


@dataclass
class SaveData:
    high_score: int = 0
    highest_wave: int = 0
    total_kills: int = 0
    total_headshots: int = 0
    total_coins: int = 0
    total_shots_fired: int = 0
    total_shots_hit: int = 0
    games_played: int = 0
    best_killstreak: int = 0
    boss_kills: int = 0
    unlocked_weapons: List[int] = field(default_factory=lambda: [0, 1])
    achievements: Dict[str, bool] = field(default_factory=dict)
    last_daily_seed: int = 0
    daily_high_score: int = 0


@dataclass
class RunStats:
    """Per-run aggregate, reset on new game."""
    shots_fired: int = 0
    shots_hit: int = 0
    headshots: int = 0
    kills: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    coins_earned: int = 0
    coins_spent: int = 0
    best_combo: int = 0
    best_multi_kill: int = 0
    perfect_waves: int = 0
    wave_damage_taken: float = 0.0      # resets per wave; used to track perfect

    def accuracy(self) -> float:
        if self.shots_fired <= 0:
            return 0.0
        return self.shots_hit / self.shots_fired


def load_settings() -> Settings:
    try:
        if SETTINGS_FILE.is_file():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            s = Settings(**{k: v for k, v in data.items() if k in Settings.__annotations__})
            s.clamp()
            return s
    except Exception:
        pass
    return Settings()


def save_settings(settings: Settings) -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    except Exception:
        pass


def load_save() -> SaveData:
    try:
        if SAVE_FILE.is_file():
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            allowed = {k: v for k, v in data.items() if k in SaveData.__annotations__}
            return SaveData(**allowed)
    except Exception:
        pass
    return SaveData()


def save_save(data: SaveData) -> None:
    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SAVE_FILE.write_text(json.dumps(asdict(data), indent=2), encoding="utf-8")
    except Exception:
        pass


def save_stats_snapshot(stats: RunStats) -> None:
    """Append-style save of last-run stats (for the post-game screen)."""
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(asdict(stats), indent=2), encoding="utf-8")
    except Exception:
        pass
