"""Wave director: spawn pacing, surprise rushes, mini-bosses; routes neighbors+threats to enemies."""

import random
import time

from core import constants as C


class WaveDirector:
    PHASE_INTRO = "intro"
    PHASE_ACTIVE = "active"
    PHASE_BREAK = "break"
    PHASE_ENDED = "ended"

    def __init__(self, particles, effects, audio, settings, mode: str):
        self.particles = particles
        self.effects = effects
        self.audio = audio
        self.settings = settings
        self.mode = mode

        self.wave = 0
        self.phase = WaveDirector.PHASE_INTRO
        self.phase_t = 1.5
        self.enemies: list = []
        self._to_spawn: list = []
        self._spawn_cd = 0.0
        self._kills_this_wave = 0
        self._enemies_this_wave = 0

        # Pacing — calm/tension/chaos rhythm
        self._wave_elapsed = 0.0
        self._surprise_at: float | None = None
        self._surprise_fired = False
        self._mini_boss_pending = False

        # Time attack
        self._time_attack_start: float = 0.0
        self._time_attack_remaining: float = float(C.TIME_ATTACK_SECONDS)
        self._time_attack_spawn_cd = 0.0

        # Open break (shop)
        self.shop_open = False

        # Pending "boss just entered" event for engine to consume
        self.pending_boss_entrance: bool = False

    @property
    def difficulty_mul(self) -> float:
        base = {"easy": 0.75, "normal": 1.0, "hard": 1.3}.get(
            self.settings.difficulty, 1.0)
        return base * (1.0 + (self.wave - 1) * 0.06)

    def start(self):
        self.wave = 0
        self.phase = WaveDirector.PHASE_INTRO
        self.phase_t = 1.5
        self.enemies.clear()
        self._to_spawn.clear()
        self.shop_open = False
        self._wave_elapsed = 0.0
        self._surprise_at = None
        self._surprise_fired = False
        self.pending_boss_entrance = False
        if self.mode == C.MODE_TIME_ATTACK:
            self._time_attack_start = time.time()
            self._time_attack_remaining = float(C.TIME_ATTACK_SECONDS)
            self._time_attack_spawn_cd = 0.5

    @property
    def is_boss_wave(self) -> bool:
        if self.mode == C.MODE_BOSS_RUSH:
            return self.phase == WaveDirector.PHASE_ACTIVE
        return (self.wave > 0 and self.wave % C.BOSS_EVERY_N_WAVES == 0
                and self.phase == WaveDirector.PHASE_ACTIVE)

    def update(self, dt: float, target_pos, threats=None):
        """threats: live player bullets (passed through to Enemy.update for dodge)."""
        if self.mode == C.MODE_TIME_ATTACK:
            self._update_time_attack(dt, target_pos, threats)
            return

        if self.phase == WaveDirector.PHASE_INTRO:
            self.phase_t -= dt
            if self.phase_t <= 0:
                self._start_next_wave()
        elif self.phase == WaveDirector.PHASE_BREAK:
            pass  # Stays open until engine closes the shop

        if self.phase == WaveDirector.PHASE_ACTIVE:
            self._wave_elapsed += dt
            # Surprise rush — sudden cluster mid-wave (if rolled at wave start)
            if (self._surprise_at is not None and not self._surprise_fired
                    and self._wave_elapsed >= self._surprise_at):
                self._surprise_fired = True
                self._spawn_surprise_rush()
            # Normal spawn pacing — gets quicker as the wave wears on
            if self._to_spawn:
                self._spawn_cd -= dt
                if self._spawn_cd <= 0:
                    kind = self._to_spawn.pop(0)
                    self._spawn_enemy(kind)
                    # Spawn rate ramps up as the wave progresses (chaos build)
                    pacing = max(0.25, 1.1 - self._wave_elapsed * 0.025)
                    self._spawn_cd = random.uniform(pacing * 0.5, pacing)

        # Update enemies with neighbors + threats
        self._tick_enemies(dt, target_pos, threats)

        self.enemies = [e for e in self.enemies if not e.is_dead_done]

        if (self.phase == WaveDirector.PHASE_ACTIVE
                and not self._to_spawn
                and all(not e.alive for e in self.enemies)):
            self._end_wave()

    def _tick_enemies(self, dt, target_pos, threats):
        """Pass neighbors + threats to each enemy for organic behavior."""
        live = [e for e in self.enemies if e.alive]
        for e in self.enemies:
            # Only consider near neighbors for separation (perf optimization).
            neighbors = [n for n in live if n is not e and
                         abs(n.x - e.x) + abs(n.y - e.y)
                         < C.ENEMY_SEPARATION_RADIUS * 1.4]
            e.update(dt, target_pos, neighbors=neighbors, threats=threats)

    def _update_time_attack(self, dt, target_pos, threats):
        self._time_attack_remaining = max(0.0,
            C.TIME_ATTACK_SECONDS - (time.time() - self._time_attack_start))
        if self.phase == WaveDirector.PHASE_INTRO:
            self.phase_t -= dt
            if self.phase_t <= 0:
                self.phase = WaveDirector.PHASE_ACTIVE
                self.wave = 1
        if self._time_attack_remaining <= 0:
            self.phase = WaveDirector.PHASE_ENDED
            return
        if self.phase == WaveDirector.PHASE_ACTIVE:
            self._time_attack_spawn_cd -= dt
            if self._time_attack_spawn_cd <= 0:
                progress = 1.0 - (self._time_attack_remaining / C.TIME_ATTACK_SECONDS)
                count = 1 + int(progress * 2)
                pool = ["zombie", "fast", "soldier"]
                if progress > 0.3:
                    pool.append("fast")
                if progress > 0.5:
                    pool.append("tank")
                for _ in range(count):
                    self._spawn_enemy(random.choice(pool))
                self._time_attack_spawn_cd = max(0.4, 1.4 - progress * 1.0)
        self._tick_enemies(dt, target_pos, threats)
        self.enemies = [e for e in self.enemies if not e.is_dead_done]

    def notify_kill(self):
        self._kills_this_wave += 1

    def request_shop(self):
        if self.phase == WaveDirector.PHASE_BREAK and self.mode != C.MODE_TIME_ATTACK:
            self.shop_open = True

    def close_shop(self):
        self.shop_open = False
        self.phase_t = C.WAVE_BREAK_TIME
        self.phase = WaveDirector.PHASE_INTRO
        self.phase_t = 1.5

    def consume_boss_entrance(self) -> bool:
        """Engine polls this once per frame to know if it should fire a boss
        cinematic intro (slow-mo + dim + roar)."""
        if self.pending_boss_entrance:
            self.pending_boss_entrance = False
            return True
        return False

    def _start_next_wave(self):
        self.wave += 1
        self._kills_this_wave = 0
        self._wave_elapsed = 0.0
        self._surprise_fired = False
        self._surprise_at = None
        roster = self._build_roster(self.wave)
        random.shuffle(roster)
        self._enemies_this_wave = len(roster)
        self._to_spawn = roster
        self._spawn_cd = 0.6
        self.phase = WaveDirector.PHASE_ACTIVE
        # Roll a surprise rush for this wave?
        if (self.mode != C.MODE_BOSS_RUSH
                and not self.is_boss_wave
                and random.random() < C.SURPRISE_RUSH_CHANCE):
            self._surprise_at = random.uniform(6.0, 10.0)
        # Mini-boss every Nth non-boss wave
        if (self.mode == C.MODE_SURVIVAL
                and not self.is_boss_wave
                and self.wave > 1
                and self.wave % C.MINI_BOSS_EVERY == 0):
            self._mini_boss_pending = True
            # Spawn the mini-boss right at wave start so it stomps in early
            self._spawn_enemy("tank")

    def _end_wave(self):
        self.phase = WaveDirector.PHASE_BREAK

    def _spawn_surprise_rush(self):
        n = random.randint(C.SURPRISE_RUSH_COUNT_MIN, C.SURPRISE_RUSH_COUNT_MAX)
        for _ in range(n):
            self._spawn_enemy("fast")
        # Tactical audio hint
        try:
            self.audio.play("enemy", volume=0.9)
        except Exception:
            pass

    def _build_roster(self, wave: int) -> list:
        if self.mode == C.MODE_BOSS_RUSH:
            kinds = ["boss", "boss_summoner", "boss_berserker"]
            return [random.choice(kinds)]
        n = C.WAVE_BASE_ENEMIES + C.WAVE_GROWTH * (wave - 1)
        pool = (
            [("zombie", 6 + max(0, 8 - wave))] +
            [("fast", 1 + wave // 2)] +
            [("soldier", max(0, wave - 1))] +
            [("tank", max(0, wave // 3))]
        )
        weighted = []
        for kind, w in pool:
            weighted.extend([kind] * max(1, w))
        roster = []
        for _ in range(n):
            roster.append(random.choice(weighted))
        if wave > 0 and wave % C.BOSS_EVERY_N_WAVES == 0:
            roster.append(random.choice(["boss", "boss_summoner", "boss_berserker"]))
        return roster

    def _spawn_enemy(self, kind: str):
        side = random.choice(["top", "left", "right"])
        if side == "top":
            x = random.uniform(80, C.SCREEN_WIDTH - 80)
            y = random.uniform(-40, 80)
        elif side == "left":
            x = random.uniform(-40, 60)
            y = random.uniform(120, C.SCREEN_HEIGHT - 220)
        else:
            x = random.uniform(C.SCREEN_WIDTH - 60, C.SCREEN_WIDTH + 40)
            y = random.uniform(120, C.SCREEN_HEIGHT - 220)
        from entities.enemy import Enemy
        enemy = Enemy(kind, x, y, difficulty_mul=self.difficulty_mul)
        self.enemies.append(enemy)
        self.audio.play_at("enemy", enemy.x, volume=0.35)
        # Bosses trigger a cinematic intro (consumed by the engine next frame)
        if enemy.is_boss:
            self.pending_boss_entrance = True

    def add_summoned(self, x, y):
        from entities.enemy import Enemy
        e = Enemy("fast", x + random.uniform(-40, 40), y + random.uniform(-40, 40),
                  difficulty_mul=self.difficulty_mul * 0.8)
        self.enemies.append(e)

    def draw(self, surface):
        for e in sorted(self.enemies, key=lambda en: en.y):
            e.draw(surface)
