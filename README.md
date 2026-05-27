# PHANTOM STRIKE — AI Gesture-Controlled FPS

A cinematic, webcam-controlled first-person arcade shooter built in pure Python.
Your **hand is your gun**. Point with your index finger, pinch to fire, close
your fist to reload, throw a peace sign for a grenade, and raise **both hands**
for a screen-clearing special.

Built with **OpenCV + MediaPipe + Pygame + NumPy**. No external assets required —
every visual is drawn procedurally and every sound is synthesized at startup.
Drop in your own `.wav` files (or images later) to override anything.

---

## Highlights

### Gameplay
- **4 game modes**: Survival, Boss Rush, Time Attack (90s), Headhunter (HS only)
- **4 weapons** with distinct stats, FX, reload sounds — Pistol, AK-47, Shotgun,
  Sniper. Sniper rounds *pierce up to 2 enemies*.
- **7 enemy types**: Zombie, Soldier (ranged), Fast, Tank, Boss, **Summoner Boss**
  (spawns minions), **Berserker Boss** (melee, speeds up at half HP).
- **Wave director** with scaling difficulty + boss every 5 waves.
- **7 power-up drops**: Health, Armor, Ammo, Shield, 2x Damage, Bullet Time, Rapid Fire.
- **Between-wave shop** (10 items: heals, refills, permanent stat buffs, weapon unlocks).
- **Headshot detection**, combo + killstreak multipliers, kill-feed, coins.
- **Multi-kill callouts**: Double / Triple / Quad / Overkill / Rampage / Unstoppable / Godlike.
- **10 achievements**, persistent save (high score, total kills, best streak, accuracy).
- **Daily challenge** seed (same enemy spawn order for everyone today).

### Hand tracking
- Threaded webcam capture (always-fresh frames).
- MediaPipe Hands at low complexity, EMA smoothing on aim, edge-triggered gestures.
- 5-gesture vocabulary including two-hand special.

### Cinematic feel
- Hit-stop / freeze frames on impact, slow-motion on headshots, pulsing crosshair.
- Screen shake, damage flash, hit markers, **damage direction arc**.
- Procedural muzzle flash, shell ejection, hit-sparks, blood, smoke, damage numbers,
  expanding shockwave rings, explosion particles.
- Animated vignette + red heartbeat pulse at low HP (heartbeat audio intensity scales).
- **Cheap bloom** (downscale/upscale additive blit) — toggle in settings.
- **Weather overlays**: rain, fog, storm (rain + lightning + fog).

### UI / UX
- Animated main menu with mode chip and high score, mode-select screen,
  pause, settings, calibration, shop, and game-over screens.
- HUD: health/armor, ammo, reload bar, weapon slots, score, combo, wave panel,
  kill feed, radar mini-map, FPS, **active-effects bar**, gesture chip,
  **REC indicator**, tutorial strip.
- **5 crosshair styles** × **6 colors**, all live-switchable in settings.

### Audio
- Procedural gunshot / explosion / reload / hit / click / growl / heartbeat /
  power-up / shop / ammo / enemy-death synthesis (numpy → `pygame.sndarray`).
- **Weapon-specific reload sounds** (pistol click, rifle slap, shotgun pump,
  sniper bolt-action).
- **Spatial audio** (stereo pan based on enemy x-coordinate).
- **Dynamic music** — calm ambient pad switches to heavier boss loop when a boss
  is alive, fades back when the boss dies.
- **Optional voice announcer** via `pyttsx3` — calls out waves, multi-kills,
  bosses, power-ups. Gracefully no-ops if `pyttsx3` isn't installed.

### Portfolio features
- **F12 — Screenshot** to `screenshots/`.
- **F9 — Toggle MP4 recording** to `recordings/` (background-thread encoder, OpenCV `VideoWriter`).
- **AR body-occlusion** mode using MediaPipe Selfie Segmentation — enemies are
  dimmed wherever your real silhouette covers them, so they look like they're
  *behind you in your room*. (Toggle in Settings → "AR Body Occlusion".)

---

## Setup

```powershell
# Python 3.11 (or 3.12) is required. MediaPipe doesn't support 3.13+ yet.
py -3.11 -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# Optional: enable voice announcer
pip install pyttsx3

python main.py
```

> Requires a working webcam. On Windows, MediaPipe takes ~2 seconds to warm up
> on first launch.

---

## Controls

### Gesture
| Action          | Gesture                              |
|-----------------|--------------------------------------|
| Aim             | Point with your **index finger**     |
| Fire            | **Pinch** thumb + index              |
| Reload          | Close your **fist**                  |
| Grenade         | **Peace sign** (index + middle up)   |
| Special nova    | Show **both hands**                  |
| Pick up power-up | Aim cursor near the pickup          |

### Keyboard
| Key | Action |
|---|---|
| `Space` | Fire (backup) |
| `R` | Reload (backup) |
| `G` | Grenade (backup) |
| `E` | Special (backup) |
| `1`–`4` | Select weapon |
| `Q` | Cycle weapon |
| `T` | Hide tutorial strip |
| `Esc` | Pause |
| `Enter` | Confirm in menus / shop / retry |
| `↑↓` | Navigate menus / shop |
| `←→` | Change setting value |
| `F9` | Toggle screen recording |
| `F12` | Save screenshot |

---

## Project layout

```
AI-FPS-Game/
├── main.py
├── requirements.txt
├── README.md
│
├── core/
│   ├── constants.py            # tunables (weapons, enemies, modes, shop, pickups...)
│   ├── settings.py             # persisted settings, save data, run stats
│   ├── utils.py                # math, drawing, OpenCV↔Pygame, all sound synthesis, bloom
│   └── engine.py               # main loop + state machine + system wiring
│
├── entities/
│   ├── weapons.py              # Weapon class, persistent shop multipliers
│   ├── bullet.py               # player bullet w/ trail and pierce
│   ├── enemy_bullet.py         # enemy projectile (homing for boss phase 2)
│   ├── enemy.py                # Enemy AI w/ telegraphs + 2 new boss types
│   ├── pickup.py               # power-up drop entity
│   └── player.py               # HP, ammo, score, combo, multi-kill, power-ups
│
├── systems/
│   ├── hand_tracking.py        # threaded webcam + MediaPipe + gestures
│   ├── shooting_system.py      # bullets, fire/grenade/special, collisions, hit-stop
│   ├── enemy_system.py         # wave director + game-mode logic
│   ├── particle_system.py      # pooled sparks/smoke/blood/shells/numbers/rings
│   ├── ui_system.py            # HUD, crosshair, menus, shop, banners
│   ├── audio_system.py         # procedural SFX + dynamic music + spatial pan
│   ├── effects_system.py       # shake/flash/slowmo/hit-stop/vignette/damage-dir/bloom
│   ├── pickup_system.py        # drops + crosshair-based collection
│   ├── weather_system.py       # rain / fog / storm overlay
│   ├── recording_system.py     # background-thread MP4 encoder
│   ├── announcer.py            # optional pyttsx3 voice
│   └── ar_mask.py              # MediaPipe Selfie Segmentation for AR occlusion
│
├── assets/                     # optional drop-in overrides
├── saves/                      # auto-generated (settings.json, savegame.json, stats.json)
├── screenshots/                # F12 outputs
└── recordings/                 # F9 outputs (.mp4)
```

---

## Performance notes

- **Hand tracking is the hot path.** MediaPipe Hands runs at `model_complexity=0`,
  `max_num_hands=2`. Webcam thread keeps `BUFFERSIZE=1` so we always read the
  freshest frame.
- **AR mask is opt-in.** When on, MediaPipe Selfie Segmentation runs on a
  background thread — only the latest mask is kept. Costs ~3–8 ms per inference
  on a modest CPU.
- **Bullet trails** reuse a tiny per-line `SRCALPHA` surface (bounding-box sized)
  instead of a full-screen alpha surface — keeps frame time stable under heavy
  fire.
- **Bloom** is a downscale → upscale → additive blit. Cheap enough to leave on
  by default; toggle off in Settings if you want max FPS.
- **Particles** are pooled and capped at `MAX_PARTICLES = 700`; oldest get
  culled first.
- **Recording** runs the H.264 (mp4v) encoder on a background thread; if the
  queue is full we drop frames instead of blocking the game loop.
- `cv2.resize` is faster than `pygame.transform.scale` for the webcam → window
  step, so the background uses it.
- `dt` is clamped to `1/20s` so a long stall can't teleport enemies through you.

---

## Replacing the procedural assets

Every system loads from `assets/` first and falls back to procedural if missing:

| Folder            | Drop in to override |
|-------------------|---------------------|
| `assets/sounds/`  | `shoot_pistol.wav` `shoot_rifle.wav` `shoot_shotgun.wav` `shoot_sniper.wav` `reload_pistol.wav` `reload_rifle.wav` `reload_shotgun.wav` `reload_sniper.wav` `hit.wav` `explosion.wav` `click.wav` `enemy.wav` `enemy_death.wav` `heartbeat.wav` `powerup.wav` `ammo_pickup.wav` `shop_buy.wav` |
| `assets/guns/`    | Wire into `entities/weapons.py` via `safe_load_image()` |
| `assets/enemies/` | Wire into `entities/enemy.py` similarly |

Recommended free sources: [Freesound](https://freesound.org/),
[OpenGameArt](https://opengameart.org/), [Kenney.nl](https://kenney.nl/assets).

---

## Deployment notes

### Local distribution

Bundle with **PyInstaller**:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --add-data "assets;assets" main.py
```

Output lands in `dist/main/` as a runnable folder. Ship that folder.

### Web / browser version (architecture)

This game is built for the desktop. To take it online, the right split is:

1. **Browser-side**: capture webcam with `getUserMedia`, run **MediaPipe Hands /
   Selfie Segmentation Tasks** in the browser (no upload).
2. **Render** the game in **HTML Canvas / WebGL** (Three.js for free glow,
   shadows). Reuse the rules here as the design spec.
3. **Backend (FastAPI / Flask + WebSocket)**: leaderboard, daily seed,
   achievements only. Works fine on Vercel/Render.
4. **WebRTC** is only a good idea if you must keep Python — high latency for a
   shooter.

---

## Future improvements

- Sprite-based enemies + multiple background scenes.
- Replay highlight system (rolling buffer → save best 5 sec on death).
- Online leaderboard service.
- Voice command input (`vosk` / `whisper`) for reload + weapon swap.
- Multiplayer co-op via `python-socketio` (server-authoritative).

---

## Credits

Design, code, FX, sound synthesis — all original.
Inspired by Call of Duty, Valorant, and arcade zombie shooters.
