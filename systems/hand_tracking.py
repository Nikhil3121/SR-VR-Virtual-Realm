"""Threaded webcam capture + MediaPipe Hands + gesture recognition."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from core import constants as C
from core.one_euro import Vec2Filter
from core.utils import apply_sensitivity_curve, clamp


# MediaPipe is heavy to import; import lazily here so unit-importing this
# module without a camera doesn't blow up.
import mediapipe as mp
_mp_hands = mp.solutions.hands


# Landmark name -> index (subset we actually use)
WRIST = 0
THUMB_TIP = 4
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20


@dataclass
class GestureState:
    detected: bool = False
    num_hands: int = 0
    # Aim point in screen coordinates (pygame space)
    aim: tuple = (C.SCREEN_WIDTH / 2, C.SCREEN_HEIGHT / 2)
    # Edge-triggered events for THIS frame only
    shoot_event: bool = False
    reload_event: bool = False
    grenade_event: bool = False
    special_event: bool = False
    # Continuous signals
    pinch_distance: float = 1.0
    fist_closed: bool = False
    index_extended: bool = False
    peace_sign: bool = False
    two_hands: bool = False
    # Raw landmarks for debug overlays
    raw_landmarks: list = field(default_factory=list)


class _WebcamThread:
    """Always-fresh-frame capture thread. Drops old frames automatically."""

    def __init__(self, src: int = 0, width: int = C.WEBCAM_WIDTH,
                 height: int = C.WEBCAM_HEIGHT):
        self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Some systems don't support CAP_DSHOW — fall back to default backend.
            self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = self.cap.isOpened()
        if self._running:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            self._thread = None

    @property
    def is_open(self) -> bool:
        return self._running and self.cap.isOpened()

    def _run(self):
        while self._running:
            ok, frame = self.cap.read()
            if not ok or frame is None:
                time.sleep(0.005)
                continue
            with self._lock:
                self._frame = frame

    def read_latest(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def release(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        if self.cap is not None:
            self.cap.release()


class HandTracker:
    """Front-of-house: poll() returns a fresh GestureState every frame."""

    def __init__(self, settings, src: int = 0):
        self.settings = settings
        self.webcam = _WebcamThread(src=src)
        self.hands = _mp_hands.Hands(
            model_complexity=0,           # lightest model for speed
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
            max_num_hands=2,
        )

        # One Euro Filter — adaptive smoothing on aim. Slow motion = precise,
        # fast motion = responsive. Beta is tied to settings.smoothing_alpha
        # so the existing slider keeps working: higher slider = snappier feel.
        self._aim_filter = Vec2Filter(
            min_cutoff=C.ONE_EURO_MIN_CUTOFF,
            beta=C.ONE_EURO_BETA,
        )
        self._smoothed_aim = (C.SCREEN_WIDTH / 2, C.SCREEN_HEIGHT / 2)
        self._prev_raw_aim = self._smoothed_aim
        self._prev_aim_time = time.time()

        # Edge-detection memory
        self._pinch_active = False
        self._fist_active = False
        self._peace_active = False
        self._two_hands_active = False
        self._last_event_time = 0.0

        # The last raw BGR frame we processed — exposed for rendering
        self._last_frame_bgr: Optional[np.ndarray] = None

    @property
    def camera_ok(self) -> bool:
        return self.webcam.is_open

    def get_last_frame_bgr(self) -> Optional[np.ndarray]:
        return self._last_frame_bgr

    def poll(self) -> GestureState:
        frame = self.webcam.read_latest()
        if frame is None:
            return GestureState(aim=self._smoothed_aim)

        # Selfie mirror so motion feels natural
        if self.settings.invert_x:
            frame = cv2.flip(frame, 1)
        self._last_frame_bgr = frame

        # MediaPipe expects RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            return GestureState(aim=self._smoothed_aim)

        hands_data = results.multi_hand_landmarks
        primary = hands_data[0]
        landmarks = [(lm.x, lm.y, lm.z) for lm in primary.landmark]

        ix, iy, _ = landmarks[INDEX_TIP]
        screen_x = ix * C.SCREEN_WIDTH
        screen_y = iy * C.SCREEN_HEIGHT

        # Map the slider [0.1, 0.95] onto a One Euro beta range so the existing
        # "smoothing" UI control keeps making intuitive sense: higher = snappier.
        slider = clamp(self.settings.smoothing_alpha, 0.1, 0.95)
        beta = C.ONE_EURO_BETA * (0.2 + slider * 2.5)
        self._aim_filter.configure(min_cutoff=C.ONE_EURO_MIN_CUTOFF, beta=beta)

        # Sensitivity curve: use the *raw* speed since last frame to compute a
        # gain, then re-apply it as an offset from the previous filtered aim.
        # This makes slow pointing precise but quick flicks feel snappy.
        now = time.time()
        dt = max(1e-3, now - self._prev_aim_time)
        rx_prev, ry_prev = self._prev_raw_aim
        raw_dx = screen_x - rx_prev
        raw_dy = screen_y - ry_prev
        raw_speed = math.hypot(raw_dx, raw_dy) / dt
        gain = apply_sensitivity_curve(raw_speed,
                                       C.SENSITIVITY_CURVE_GAIN)
        boosted_x = rx_prev + raw_dx * gain
        boosted_y = ry_prev + raw_dy * gain
        self._prev_raw_aim = (screen_x, screen_y)
        self._prev_aim_time = now

        fx, fy = self._aim_filter(boosted_x, boosted_y, now)
        self._smoothed_aim = (clamp(fx, 0, C.SCREEN_WIDTH),
                              clamp(fy, 0, C.SCREEN_HEIGHT))

        pinch = self._distance_3d(landmarks[THUMB_TIP], landmarks[INDEX_TIP])
        is_pinch = pinch < C.GESTURE_PINCH_THRESHOLD

        index_ext = self._finger_extended(landmarks, INDEX_TIP, INDEX_PIP)
        middle_ext = self._finger_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP)
        ring_ext = self._finger_extended(landmarks, RING_TIP, RING_PIP)
        pinky_ext = self._finger_extended(landmarks, PINKY_TIP, PINKY_PIP)

        is_fist = (not index_ext) and (not middle_ext) and (not ring_ext) and (not pinky_ext)
        is_peace = index_ext and middle_ext and (not ring_ext) and (not pinky_ext)
        is_two = len(hands_data) >= 2

        now = time.time()
        debounce_ok = (now - self._last_event_time) > C.GESTURE_DEBOUNCE_TIME

        state = GestureState(
            detected=True,
            num_hands=len(hands_data),
            aim=self._smoothed_aim,
            pinch_distance=pinch,
            fist_closed=is_fist,
            index_extended=index_ext,
            peace_sign=is_peace,
            two_hands=is_two,
            raw_landmarks=landmarks,
        )

        # SHOOT — fires on the leading edge of a pinch
        if is_pinch and not self._pinch_active and debounce_ok:
            state.shoot_event = True
            self._last_event_time = now
        self._pinch_active = is_pinch

        # RELOAD — fires on the leading edge of a closed fist
        if is_fist and not self._fist_active and debounce_ok:
            state.reload_event = True
            self._last_event_time = now
        self._fist_active = is_fist

        # GRENADE — leading edge of peace sign
        if is_peace and not self._peace_active and debounce_ok:
            state.grenade_event = True
            self._last_event_time = now
        self._peace_active = is_peace

        # SPECIAL — leading edge of two hands visible (and both with index up)
        if is_two and not self._two_hands_active and debounce_ok:
            # Confirm both hands have index extended for intent
            second = [(lm.x, lm.y, lm.z) for lm in hands_data[1].landmark]
            second_ext = self._finger_extended(second, INDEX_TIP, INDEX_PIP)
            if index_ext and second_ext:
                state.special_event = True
                self._last_event_time = now
        self._two_hands_active = is_two

        return state

    def release(self):
        try:
            self.hands.close()
        except Exception:
            pass
        self.webcam.release()

    @staticmethod
    def _distance_3d(a, b) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

    @staticmethod
    def _finger_extended(landmarks, tip_idx: int, pip_idx: int) -> bool:
        """A finger is 'extended' when the tip is meaningfully above its PIP joint."""
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        # In normalized image coords, y grows downward.
        return (pip[1] - tip[1]) > 0.03
