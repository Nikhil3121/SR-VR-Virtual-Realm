"""
Game-wide constants. Tunable parameters live here so other modules stay clean.
Values are chosen for a cinematic 1280x720 arcade FPS feel at 60 FPS.
"""

from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
SAVE_DIR = ROOT_DIR / "saves"
SAVE_FILE = SAVE_DIR / "savegame.json"
SETTINGS_FILE = SAVE_DIR / "settings.json"
STATS_FILE = SAVE_DIR / "stats.json"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
RECORDING_DIR = ROOT_DIR / "recordings"

# Display
WINDOW_TITLE = "SR-VR Virtual Realm  -  AI Gesture FPS"
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TARGET_FPS = 60
WEBCAM_WIDTH = 640
WEBCAM_HEIGHT = 480

# Colors (R, G, B)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NEAR_BLACK = (8, 10, 14)
DIM = (28, 32, 40)
GREY = (90, 96, 108)
LIGHT_GREY = (180, 188, 200)

NEON_CYAN = (0, 240, 255)
NEON_PINK = (255, 60, 170)
NEON_GREEN = (80, 255, 140)
NEON_YELLOW = (255, 220, 60)
NEON_RED = (255, 60, 70)
NEON_ORANGE = (255, 140, 40)
NEON_PURPLE = (180, 80, 255)

BLOOD_RED = (140, 18, 24)
HUD_BG = (10, 14, 20, 180)  # RGBA
HUD_LINE = (0, 220, 245)

# Player
PLAYER_MAX_HEALTH = 100
PLAYER_MAX_ARMOR = 100
PLAYER_LOW_HEALTH = 30
PLAYER_INVULN_TIME = 0.45
MULTI_KILL_WINDOW = 1.4  # seconds — kills inside this gap chain

# Weapons
WEAPON_PISTOL = {
    "name": "M9 Phantom",
    "kind": "pistol",
    "damage": 28,
    "fire_rate": 6.0,
    "magazine": 12,
    "reserve": 96,
    "reload_time": 1.1,
    "recoil": 4.5,
    "spread": 0.012,
    "bullet_speed": 2400,
    "bullets_per_shot": 1,
    "muzzle_color": NEON_YELLOW,
    "trail_color": NEON_YELLOW,
    "pierce": 0,
}
WEAPON_AK47 = {
    "name": "AK-47 Reaper",
    "kind": "rifle",
    "damage": 22,
    "fire_rate": 11.0,
    "magazine": 30,
    "reserve": 180,
    "reload_time": 1.8,
    "recoil": 7.0,
    "spread": 0.025,
    "bullet_speed": 2800,
    "bullets_per_shot": 1,
    "muzzle_color": NEON_ORANGE,
    "trail_color": NEON_ORANGE,
    "pierce": 0,
}
WEAPON_SHOTGUN = {
    "name": "SPAS Riot",
    "kind": "shotgun",
    "damage": 14,
    "fire_rate": 1.6,
    "magazine": 6,
    "reserve": 30,
    "reload_time": 2.4,
    "recoil": 16.0,
    "spread": 0.09,
    "bullet_speed": 2000,
    "bullets_per_shot": 8,
    "muzzle_color": NEON_RED,
    "trail_color": NEON_ORANGE,
    "pierce": 0,
}
WEAPON_SNIPER = {
    "name": "AWM Specter",
    "kind": "sniper",
    "damage": 140,
    "fire_rate": 0.9,
    "magazine": 5,
    "reserve": 25,
    "reload_time": 2.8,
    "recoil": 22.0,
    "spread": 0.0,
    "bullet_speed": 4200,
    "bullets_per_shot": 1,
    "muzzle_color": NEON_CYAN,
    "trail_color": NEON_CYAN,
    "pierce": 2,  # punches through up to 2 enemies
}
WEAPONS = [WEAPON_PISTOL, WEAPON_AK47, WEAPON_SHOTGUN, WEAPON_SNIPER]
WEAPON_UNLOCK_SCORE = {0: 0, 1: 0, 2: 2500, 3: 6000}

# Enemies
ENEMY_TYPES = {
    "zombie": {
        "health": 60, "speed": 70, "damage": 12, "score": 100,
        "color": (110, 180, 90), "size": 70, "attack_range": 90,
        "ranged": False,
    },
    "soldier": {
        "health": 110, "speed": 95, "damage": 18, "score": 220,
        "color": (200, 170, 110), "size": 72, "attack_range": 380,
        "ranged": True, "projectile_speed": 520, "projectile_dmg": 14,
    },
    "fast": {
        "health": 45, "speed": 180, "damage": 10, "score": 180,
        "color": (255, 90, 160), "size": 56, "attack_range": 80,
        "ranged": False,
    },
    "tank": {
        "health": 360, "speed": 45, "damage": 28, "score": 500,
        "color": (90, 110, 160), "size": 110, "attack_range": 90,
        "ranged": False,
    },
    "boss": {
        "health": 1800, "speed": 60, "damage": 35, "score": 3500,
        "color": (210, 60, 70), "size": 180, "attack_range": 420,
        "ranged": True, "projectile_speed": 480, "projectile_dmg": 22,
    },
    "boss_summoner": {
        "health": 1400, "speed": 50, "damage": 25, "score": 4000,
        "color": (160, 80, 220), "size": 170, "attack_range": 500,
        "ranged": True, "projectile_speed": 460, "projectile_dmg": 18,
    },
    "boss_berserker": {
        "health": 1600, "speed": 95, "damage": 38, "score": 4200,
        "color": (255, 120, 40), "size": 165, "attack_range": 110,
        "ranged": False,
    },
}

# Waves / gameplay
WAVE_BASE_ENEMIES = 6
WAVE_GROWTH = 3
WAVE_BREAK_TIME = 5.0
BOSS_EVERY_N_WAVES = 5

HEADSHOT_BONUS = 1.6
COMBO_DECAY_TIME = 2.2
KILLSTREAK_MULTIPLIER_STEP = 0.1
COIN_PER_KILL = 10

# Multi-kill tier labels (kills within MULTI_KILL_WINDOW)
MULTI_KILL_TIERS = {
    2: "DOUBLE KILL",
    3: "TRIPLE KILL",
    4: "QUAD KILL",
    5: "OVERKILL",
    6: "RAMPAGE",
    8: "UNSTOPPABLE",
    10: "GODLIKE",
}

# Game modes
MODE_SURVIVAL = "survival"
MODE_BOSS_RUSH = "boss_rush"
MODE_TIME_ATTACK = "time_attack"
MODE_HEADSHOT_ONLY = "headshot_only"

GAME_MODES = [
    (MODE_SURVIVAL, "SURVIVAL", "Endless waves, scaling difficulty"),
    (MODE_BOSS_RUSH, "BOSS RUSH", "Bosses only, back to back"),
    (MODE_TIME_ATTACK, "TIME ATTACK", "Max kills in 90 seconds"),
    (MODE_HEADSHOT_ONLY, "HEADHUNTER", "Body shots do zero damage"),
]
TIME_ATTACK_SECONDS = 90

# Pickups
PICKUP_HEALTH = "health"
PICKUP_ARMOR = "armor"
PICKUP_AMMO = "ammo"
PICKUP_SHIELD = "shield"
PICKUP_DOUBLE_DAMAGE = "double_damage"
PICKUP_SLOWMO = "slowmo"
PICKUP_FIRE_RATE = "fire_rate"

PICKUP_DEFINITIONS = {
    PICKUP_HEALTH:        {"color": (90, 230, 130),  "label": "+25 HP",       "duration": 0,    "drop_weight": 22},
    PICKUP_ARMOR:         {"color": (90, 170, 255),  "label": "+30 ARMOR",    "duration": 0,    "drop_weight": 14},
    PICKUP_AMMO:          {"color": (255, 220, 80),  "label": "+AMMO",        "duration": 0,    "drop_weight": 18},
    PICKUP_SHIELD:        {"color": (120, 200, 255), "label": "SHIELD 4s",    "duration": 4.0,  "drop_weight": 7},
    PICKUP_DOUBLE_DAMAGE: {"color": (255, 90, 90),   "label": "2x DMG 10s",   "duration": 10.0, "drop_weight": 9},
    PICKUP_SLOWMO:        {"color": (180, 120, 255), "label": "BULLET TIME",  "duration": 4.0,  "drop_weight": 5},
    PICKUP_FIRE_RATE:     {"color": (255, 180, 60),  "label": "RAPID FIRE",   "duration": 8.0,  "drop_weight": 8},
}
PICKUP_DROP_CHANCE = 0.30  # chance an enemy drops a pickup on death
PICKUP_BOSS_DROPS = 4      # bosses guarantee N drops
PICKUP_LIFETIME = 12.0     # seconds before pickup despawns
PICKUP_COLLECT_RADIUS = 60 # crosshair within this distance collects

# Shop
SHOP_ITEMS = [
    {"id": "heal_full",    "name": "Full Heal",          "cost": 80,  "desc": "Restore all health"},
    {"id": "armor_full",   "name": "Full Armor",         "cost": 90,  "desc": "Restore all armor"},
    {"id": "ammo_refill",  "name": "Refill All Ammo",    "cost": 60,  "desc": "All weapons to full reserve"},
    {"id": "max_hp",       "name": "+25 Max HP",         "cost": 200, "desc": "Permanent for this run"},
    {"id": "max_armor",    "name": "+25 Max Armor",      "cost": 200, "desc": "Permanent for this run"},
    {"id": "fast_reload",  "name": "Quick Hands",        "cost": 250, "desc": "30%% faster reload (run)"},
    {"id": "extra_dmg",    "name": "Hollow Points",      "cost": 280, "desc": "+15%% damage (run)"},
    {"id": "fast_fire",    "name": "Trigger Discipline", "cost": 260, "desc": "+15%% fire rate (run)"},
    {"id": "unlock_shotgun", "name": "Unlock Shotgun",   "cost": 400, "desc": "Add SPAS Riot to loadout"},
    {"id": "unlock_sniper",  "name": "Unlock Sniper",    "cost": 700, "desc": "Add AWM Specter to loadout"},
]

# Effects
SCREEN_SHAKE_DECAY = 9.0
MAX_PARTICLES = 700
SLOWMO_FACTOR = 0.35
SLOWMO_DURATION = 0.5
DAMAGE_FLASH_TIME = 0.18
HIT_STOP_DURATION = 0.06    # freeze frames on impact

# Crosshair styles
CROSSHAIR_STYLES = ["classic", "dot", "circle", "cross", "tactical"]

# Gestures
GESTURE_PINCH_THRESHOLD = 0.055
GESTURE_FIST_THRESHOLD = 0.085
GESTURE_DEBOUNCE_TIME = 0.18
SMOOTHING_ALPHA = 0.55

# Weather
WEATHER_NONE = "none"
WEATHER_RAIN = "rain"
WEATHER_FOG = "fog"
WEATHER_STORM = "storm"
WEATHER_OPTIONS = [WEATHER_NONE, WEATHER_RAIN, WEATHER_FOG, WEATHER_STORM]

# Recording
RECORDING_FPS = 30
RECORDING_MAX_SECONDS = 60

# Achievements
ACHIEVEMENTS = {
    "first_blood": "First Blood",
    "headhunter": "Headhunter (10 headshots)",
    "unstoppable": "Unstoppable (15 kill streak)",
    "wave_master": "Wave Master (reach wave 10)",
    "boss_slayer": "Boss Slayer",
    "arsenal": "Full Arsenal (unlock every gun)",
    "godlike": "Godlike (10 kills in a row, fast)",
    "rich": "Big Spender (3,000 coins earned)",
    "survivor": "Survivor (no damage on a full wave)",
    "perfect_aim": "Perfect Aim (85%+ accuracy in a run)",
}

# Enemy movement (organic / momentum-based)
ENEMY_ACCEL = 9.0            # how snappy velocity follows desired direction
ENEMY_DRAG  = 2.4            # air friction (per second)
ENEMY_SEPARATION_RADIUS = 78  # px — enemies push apart inside this distance
ENEMY_SEPARATION_WEIGHT = 320  # px/s of steer force at zero distance
ENEMY_STRAFE_AMPLITUDE  = 0.55  # 0..1 — how strong the side-to-side is
ENEMY_DODGE_LOOKAHEAD = 0.45   # seconds — only react to bullets that arrive in
ENEMY_DODGE_RADIUS = 60        # px perpendicular trip-wire
ENEMY_KNOCKBACK = 320          # px/s impulse on hit
ENEMY_KNOCKBACK_HEAD = 480
ENEMY_FLINCH_DURATION = 0.18

# Per-type movement style tweaks ---------------------------------------------
ENEMY_MOVE_STYLE = {
    "zombie":        {"strafe": 0.20, "zigzag_freq": 0.0, "zigzag_amp": 0.0, "dodge": 0.0},
    "soldier":       {"strafe": 0.85, "zigzag_freq": 0.6, "zigzag_amp": 0.4, "dodge": 0.45},
    "fast":          {"strafe": 0.55, "zigzag_freq": 2.4, "zigzag_amp": 0.9, "dodge": 0.85},
    "tank":          {"strafe": 0.05, "zigzag_freq": 0.0, "zigzag_amp": 0.0, "dodge": 0.0},
    "boss":          {"strafe": 0.45, "zigzag_freq": 0.3, "zigzag_amp": 0.3, "dodge": 0.20},
    "boss_summoner": {"strafe": 0.65, "zigzag_freq": 0.8, "zigzag_amp": 0.5, "dodge": 0.55},
    "boss_berserker":{"strafe": 0.25, "zigzag_freq": 0.0, "zigzag_amp": 0.0, "dodge": 0.0},
}

# Critical hits + weapon recoil patterns
CRIT_CHANCE = 0.08            # base crit chance
CRIT_DAMAGE_MULT = 2.0

# Recoil patterns: (vertical_kick, horizontal_drift_amplitude, recovery_speed)
# Vertical kick adds to a pushback offset that bounces the gun & view up.
# Horizontal drift swings the view subtly side to side as the gun fires.
WEAPON_RECOIL_PATTERN = {
    "pistol":  {"v": 6.0,  "h": 1.2,  "recovery": 7.0,  "view_kick": 3.0},
    "rifle":   {"v": 5.5,  "h": 3.5,  "recovery": 4.5,  "view_kick": 4.5},
    "shotgun": {"v": 22.0, "h": 6.0,  "recovery": 3.2,  "view_kick": 10.0},
    "sniper":  {"v": 28.0, "h": 1.0,  "recovery": 2.0,  "view_kick": 14.0},
}

# Hand tracking (One Euro Filter + sensitivity curve)
ONE_EURO_MIN_CUTOFF = 1.2     # Hz — bigger = more responsive when still
ONE_EURO_BETA       = 0.020   # slope vs. speed — bigger = snappier on motion
SENSITIVITY_CURVE_GAIN = 0.45 # 0 = linear; > 0 = accel on fast motion

# Pacing (calm / surprise rushes / mini-bosses)
SURPRISE_RUSH_CHANCE = 0.40       # per wave — sudden cluster of fast enemies
SURPRISE_RUSH_COUNT_MIN = 4
SURPRISE_RUSH_COUNT_MAX = 7
MINI_BOSS_EVERY = 3               # every Nth non-boss wave gets a Tank mini-boss
BOSS_ENTRANCE_SLOWMO = 1.0        # seconds of slow-mo + cinematic darken on boss arrival

# Camera / sway / sniper zoom
WEAPON_SWAY_AMPLITUDE = 6.0
WEAPON_SWAY_SPEED = 1.4
RELOAD_DIP_DEPTH = 28.0           # px the gun dips down when reloading
SNIPER_ZOOM_DARKEN = 200          # peripheral darkness when sniper equipped + steady

# UI smoothing (animated bars / counters)
UI_TWEEN_RATE = 8.0               # higher = quicker catch-up
MENU_FADE_TIME = 0.28             # seconds for menu transitions
