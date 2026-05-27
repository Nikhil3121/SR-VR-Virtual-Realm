<div align="center">

# SR-VR Virtual Realm

### AI Gesture-Controlled FPS — *Your hand is your weapon*

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.6-green?logo=pygame&logoColor=white)](https://www.pygame.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-orange)](https://google.github.io/mediapipe/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.10-red?logo=opencv&logoColor=white)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](#license)
[![Made with](https://img.shields.io/badge/Made%20with-Love-ff69b4)]()

**Point. Pinch. Fire. Reload. Survive.**

A cinematic, webcam-controlled first-person arcade shooter built in pure Python.
No mouse. No keyboard. Just your hand and a camera.

<!-- TODO: Add gameplay GIF here. Record with F9, convert mp4 -> gif with ffmpeg -->
<!-- <img src="docs/gameplay.gif" alt="Gameplay" width="780"> -->

</div>

---

## About

**SR-VR Virtual Realm** uses your webcam and AI hand tracking to turn your hand into a real-time aiming controller. Point your index finger to aim, pinch to fire, close your fist to reload — all without touching a single button.

Built entirely in Python with **OpenCV + MediaPipe + Pygame + NumPy**. Every visual is drawn procedurally and every sound is synthesized at runtime, so the game runs out of the box with **zero external asset files**.

---

## Highlights

### Gameplay
- **4 weapons** with distinct stats and recoil curves — Pistol, AK-47, Shotgun, Sniper
- **7 enemy types** including 3 boss variants (Standard, Summoner, Berserker)
- **7 power-ups** that drop from enemies — Health, Armor, Ammo, Shield, 2× Damage, Bullet Time, Rapid Fire
- **10-item shop** between waves for permanent upgrades and weapon unlocks
- **4 game modes** — Survival, Boss Rush, Time Attack, Headhunter
- **Multi-kill callouts** — Double / Triple / Quad / Overkill / Rampage / Unstoppable / Godlike
- **Critical hits**, headshot detection, combo + killstreak multipliers
- **10 achievements** + persistent save + daily challenge seed

### Hand Tracking
- **One Euro Filter** for smooth, lag-free aim — precise when still, snappy when flicking
- **Adaptive sensitivity curve** for premium aim feel
- **5-gesture vocabulary** including two-handed special attack
- **Threaded webcam capture** keeps frames fresh under load

### Cinematic Feel
- Per-weapon **recoil patterns** with vertical kick + horizontal drift
- **Hit-stop** freeze frames on every impact
- **Slow motion** on headshots and boss kills
- Procedural **muzzle flash, blood, shell ejection, smoke, damage numbers**
- **Cinematic boss entrance** — slow-mo zoom + screen darken + boss roar
- **Bloom, vignette, screen shake, damage direction arc**

### Audio
- Procedurally synthesized — **no .wav files required**
- **Layered gunshots** (sub-bass thump + mid crack + high tail)
- **Weapon-specific reloads** — click, slap, pump, bolt-action
- **Spatial stereo panning** based on enemy x-position
- **Dynamic music** swaps to a heavy loop during boss fights
- Optional **voice announcer** via `pyttsx3`

### Visual Polish
- **5 crosshair styles × 6 colors**
- **Weather** — Rain, Fog, Storm with lightning
- **Sniper zoom** vignette + tactical lines
- **AR body-occlusion** mode (MediaPipe Selfie Segmentation) — enemies appear *behind your silhouette*
- **Animated HUD** with smooth value tweens

### Quality of Life
- **F12** — Save screenshot
- **F9** — Toggle MP4 recording (background-thread encoder)
- **Persistent settings**, save game, and run statistics
- Full **settings menu** with 19 options

---

## Quick Start

### Requirements
- **Python 3.10, 3.11, or 3.12**
  > MediaPipe does not yet ship wheels for Python 3.13+. Use 3.12 or older.
- A working **webcam**
- Windows, macOS, or Linux

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/Nikhil3121/SR-VR-Virtual-Realm.git
cd SR-VR-Virtual-Realm

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. (Optional) enable the voice announcer
pip install pyttsx3

# 5. Run the game
python main.py
```

The game opens to the **main menu**. Pick **PLAY** to start, or try **SELECT MODE** for one of the four game modes.

---

## How to Play

### Gestures

| Action          | Gesture                                    |
| --------------- | ------------------------------------------ |
| **Aim**         | Point your **index finger** at the screen  |
| **Fire**        | **Pinch** thumb and index finger together  |
| **Reload**      | Close your hand into a **fist**            |
| **Grenade**     | **Peace sign** (index + middle finger up)  |
| **Special**     | Show **both hands**, both with index up    |
| **Collect**     | Move your **crosshair near a pickup**      |

### Keyboard (menus + backup controls)

| Key             | Action                              |
| --------------- | ----------------------------------- |
| `↑` `↓`         | Navigate menus                      |
| `←` `→`         | Change setting value                |
| `Enter`         | Confirm                             |
| `Esc`           | Pause / back                        |
| `1` – `4`       | Select weapon directly              |
| `Q`             | Cycle to next weapon                |
| `Space`         | Fire (keyboard fallback)            |
| `R`             | Reload (keyboard fallback)          |
| `G`             | Grenade (keyboard fallback)         |
| `E`             | Special (keyboard fallback)         |
| `T`             | Hide the tutorial strip             |
| `F9`            | Start / stop screen recording       |
| `F12`           | Save screenshot                     |

### Game Modes

| Mode             | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| **Survival**     | Endless waves with scaling difficulty. Bosses every 5 waves.  |
| **Boss Rush**    | Back-to-back boss fights. No regular enemies.                 |
| **Time Attack**  | Score as many kills as possible in 90 seconds.                |
| **Headhunter**   | Body shots deal zero damage. Only headshots count.            |

### Tips for Best Experience
- Sit roughly **40–60 cm** from your webcam
- Use **small wrist movements** for precise aiming
- The game **mirrors the camera** by default — your on-screen hand matches your real-world hand
- Use the **Calibrate** menu option to verify each gesture is detected before playing
- Lower the **Hand Smoothing** slider in Settings if aim feels laggy
- **Recording (F9)** captures up to 60 seconds straight to MP4 — share your best moments

---

## Tech Stack

| Component                      | Tool                                                                    |
| ------------------------------ | ----------------------------------------------------------------------- |
| Game engine                    | [Pygame](https://www.pygame.org/) 2.6                                   |
| Hand & body tracking           | [MediaPipe](https://google.github.io/mediapipe/) 0.10.14                |
| Webcam I/O and video encoding  | [OpenCV](https://opencv.org/) 4.10                                      |
| Math + procedural audio synth  | [NumPy](https://numpy.org/) 1.x                                         |
| Voice announcer *(optional)*   | [pyttsx3](https://pypi.org/project/pyttsx3/)                            |

---

## Project Structure

```
SR-VR-Virtual-Realm/
├── main.py                    # entry point
├── requirements.txt
├── README.md
├── .gitignore
│
├── core/
│   ├── constants.py           # every tunable parameter
│   ├── settings.py            # persisted settings, save data, run stats
│   ├── utils.py               # math, drawing, audio synthesis, OpenCV<->Pygame
│   ├── one_euro.py            # One Euro Filter implementation
│   └── engine.py              # main loop + state machine + system wiring
│
├── entities/
│   ├── weapons.py             # Weapon class + procedural gun render
│   ├── bullet.py              # Player bullet (with piercing)
│   ├── enemy_bullet.py        # Enemy projectile
│   ├── enemy.py               # Enemy AI with momentum / dodge / flinch
│   ├── pickup.py              # Power-up drop entity
│   └── player.py              # HP, ammo, score, combo, power-ups
│
├── systems/
│   ├── hand_tracking.py       # Threaded webcam + MediaPipe + gestures
│   ├── shooting_system.py     # Bullets, fire/grenade/special, crits, knockback
│   ├── enemy_system.py        # Wave director, spawning, pacing
│   ├── particle_system.py     # Pooled sparks / smoke / blood / numbers
│   ├── ui_system.py           # HUD, crosshair, menus, shop, banners
│   ├── audio_system.py        # Procedural SFX + dynamic music + spatial pan
│   ├── effects_system.py      # Shake, slow-mo, bloom, vignette, explosion light
│   ├── pickup_system.py       # Drops + crosshair-radius collection
│   ├── weather_system.py      # Rain / fog / storm overlay
│   ├── recording_system.py    # Background-thread MP4 encoder
│   ├── announcer.py           # Optional pyttsx3 voice
│   └── ar_mask.py             # MediaPipe Selfie Segmentation occlusion
│
├── assets/                    # optional drop-in overrides
│   └── sounds/                # .wav / .mp3 / .ogg files (overrides synthesis)
│
├── saves/                     # auto-generated at runtime
├── screenshots/               # F12 outputs
└── recordings/                # F9 outputs (.mp4)
```

---

## Customization

### Use Your Own Sounds

Drop any `.wav`, `.mp3`, or `.ogg` file into `assets/sounds/` with one of these names and the game will use it automatically:

```
shoot_pistol      shoot_rifle       shoot_shotgun    shoot_sniper
reload_pistol     reload_rifle      reload_shotgun   reload_sniper
hit               crit              bass_thump       boss_roar
explosion         click             enemy            enemy_death
heartbeat         powerup           ammo_pickup      shop_buy
```

No code changes needed — the asset loader checks for files first and falls back to procedural synthesis if missing.

### Tune the Gameplay

Every value lives in [`core/constants.py`](core/constants.py). Examples:

```python
# Enemy feel
ENEMY_ACCEL = 9.0             # higher = snappier direction change
ENEMY_DRAG  = 2.4             # higher = heavier movement
ENEMY_SEPARATION_RADIUS = 78  # how close enemies can pack together

# Combat balance
CRIT_CHANCE = 0.08            # 0.0 - 1.0
HEADSHOT_BONUS = 1.6          # damage multiplier
COMBO_DECAY_TIME = 2.2        # seconds before your combo resets

# Pacing
SURPRISE_RUSH_CHANCE = 0.40   # chance of mid-wave fast-enemy rush
MINI_BOSS_EVERY = 3           # mini-boss every Nth wave
BOSS_EVERY_N_WAVES = 5        # boss every Nth wave
```

### Add a New Enemy Type

Add entries to `ENEMY_TYPES` and `ENEMY_MOVE_STYLE` in `core/constants.py`. Color, health, speed, damage, attack range, and movement personality are all controlled from there — no other code changes required.

---

## Performance Notes

- **MediaPipe Hands** runs at `model_complexity=0` for ~60 FPS on a typical laptop
- **Webcam thread** keeps `BUFFERSIZE=1` so we always read the freshest frame
- **Bullet trails** use bounding-box-sized alpha surfaces instead of full-screen (huge perf win)
- **Particles** are pooled and capped at `MAX_PARTICLES = 700`
- **AR body occlusion** is opt-in (adds ~3–8 ms per frame on a modern CPU)
- **Bloom** is a cheap downscale → upscale → additive blit (toggle if FPS drops)
- `dt` is clamped at `1/20s` so a long stall can't teleport enemies through you

---

## Troubleshooting

<details>
<summary><b>"AttributeError: module 'mediapipe' has no attribute 'solutions'"</b></summary>

You have a newer MediaPipe version that removed the legacy API. Pin to 0.10.14:

```bash
pip install --force-reinstall "mediapipe==0.10.14" "numpy<2.0" "opencv-python==4.10.0.84"
```
</details>

<details>
<summary><b>"opencv-python requires numpy>=2"</b></summary>

Same fix as above — pin OpenCV to a NumPy-1.x compatible release.
</details>

<details>
<summary><b>Pygame fails to install on Python 3.13/3.14</b></summary>

Pygame doesn't have prebuilt wheels for the newest Python. **Use Python 3.11 or 3.12** instead. Install it from [python.org](https://www.python.org/downloads/) and recreate your virtual environment with `py -3.12 -m venv .venv`.
</details>

<details>
<summary><b>Camera not detected</b></summary>

The game tries DirectShow on Windows first, then falls back. Make sure another app isn't holding the webcam (Zoom, OBS, browser tabs).
</details>

<details>
<summary><b>Game runs slowly</b></summary>

Open **Settings** and:
- Turn off **AR Body Occlusion**
- Turn off **Bloom**
- Set **Weather** to **None**
- Lower the **Difficulty**
</details>

---

## Roadmap

- [ ] Sprite-based enemy art (currently procedural shapes)
- [ ] Online leaderboard with daily-challenge rankings
- [ ] Multiplayer co-op via WebSocket
- [ ] Voice command input (`vosk` / `whisper`)
- [ ] Web port — browser MediaPipe + Three.js
- [ ] Replay highlight system (rolling 5-sec buffer on death)

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

Found a bug, balance issue, or have a feature idea? [Open an issue](https://github.com/Nikhil3121/SR-VR-Virtual-Realm/issues).

---

## License

MIT — free for personal and commercial use. Attribution appreciated but not required.

---

## Author

**Nikhil** — [@Nikhil3121](https://github.com/Nikhil3121)

Built as a portfolio project. Inspired by Call of Duty, Valorant, and arcade zombie shooters.

---

<div align="center">

If you played the game and enjoyed it, **please consider starring the repo** — it helps a lot.

</div>
