"""Screen recording — pygame surface → mp4 via cv2.VideoWriter, background-threaded."""

import os
import queue
import threading
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
import pygame

from core import constants as C


class RecordingSystem:
    def __init__(self):
        self.recording = False
        self._writer: Optional[cv2.VideoWriter] = None
        self._queue: "queue.Queue[Optional[np.ndarray]]" = queue.Queue(maxsize=120)
        self._thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0
        self._frame_interval = 1.0 / C.RECORDING_FPS
        self._last_frame_time = 0.0
        self._path: Optional[str] = None
        self._frame_count = 0
        C.RECORDING_DIR.mkdir(parents=True, exist_ok=True)

    def toggle(self) -> Optional[str]:
        """Start or stop recording. Returns the output path on stop, else None."""
        if self.recording:
            return self.stop()
        self.start()
        return None

    def start(self):
        if self.recording:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = str(C.RECORDING_DIR / f"phantom_strike_{stamp}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        try:
            self._writer = cv2.VideoWriter(
                self._path, fourcc, C.RECORDING_FPS,
                (C.SCREEN_WIDTH, C.SCREEN_HEIGHT),
            )
            if not self._writer.isOpened():
                self._writer = None
                return
        except Exception:
            self._writer = None
            return
        self.recording = True
        self._start_time = time.time()
        self._last_frame_time = 0.0
        self._frame_count = 0
        self._thread = threading.Thread(target=self._encoder_loop, daemon=True)
        self._thread.start()

    def stop(self) -> Optional[str]:
        if not self.recording:
            return None
        self.recording = False
        try:
            self._queue.put_nowait(None)  # sentinel
        except queue.Full:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._writer is not None:
            try:
                self._writer.release()
            except Exception:
                pass
            self._writer = None
        return self._path

    def capture(self, surface: pygame.Surface):
        """Called once per frame; enqueues a copy if it's time."""
        if not self.recording or self._writer is None:
            return
        now = time.time() - self._start_time
        # Hit the max recording length cap
        if now > C.RECORDING_MAX_SECONDS:
            self.stop()
            return
        if now - self._last_frame_time < self._frame_interval:
            return
        self._last_frame_time = now
        try:
            # surfarray returns (W, H, 3) RGB
            arr = pygame.surfarray.array3d(surface)
            arr = np.transpose(arr, (1, 0, 2))         # (H, W, 3)
            bgr = arr[:, :, ::-1].copy()                # RGB -> BGR
            self._queue.put_nowait(bgr)
        except queue.Full:
            # drop the frame rather than block
            pass
        except Exception:
            pass

    def elapsed_seconds(self) -> float:
        if not self.recording:
            return 0.0
        return time.time() - self._start_time

    def _encoder_loop(self):
        while True:
            try:
                frame = self._queue.get(timeout=0.5)
            except queue.Empty:
                if not self.recording:
                    return
                continue
            if frame is None:
                return
            try:
                if self._writer is not None:
                    self._writer.write(frame)
                    self._frame_count += 1
            except Exception:
                pass
