"""AR body-occlusion mask via MediaPipe Selfie Segmentation (runs on a background thread)."""

from __future__ import annotations

import threading
from typing import Optional

import cv2
import numpy as np

from core import constants as C

try:
    import mediapipe as mp  # type: ignore
    _mp_seg = getattr(mp.solutions, "selfie_segmentation", None)
except Exception:
    _mp_seg = None


class ARMaskSystem:
    """Holds the latest person-mask matched to the game window size."""

    def __init__(self, settings):
        self.settings = settings
        self._available = _mp_seg is not None
        self._segmenter = None
        if self._available:
            try:
                self._segmenter = _mp_seg.SelfieSegmentation(model_selection=1)
            except Exception:
                self._available = False
        self._mask: Optional[np.ndarray] = None  # H x W float32 in [0,1]
        self._lock = threading.Lock()
        self._busy = False

    @property
    def available(self) -> bool:
        return self._available

    def request(self, frame_bgr: np.ndarray):
        """Kick off segmentation on a background thread if idle."""
        if not self._available or not self.settings.ar_occlusion:
            return
        if frame_bgr is None or self._busy:
            return
        self._busy = True
        threading.Thread(target=self._compute, args=(frame_bgr.copy(),),
                         daemon=True).start()

    def _compute(self, frame_bgr: np.ndarray):
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            res = self._segmenter.process(rgb)
            mask = res.segmentation_mask
            if mask is None:
                return
            # Resize mask to the game window size
            resized = cv2.resize(mask, (C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
            # Soften the edge slightly
            blurred = cv2.GaussianBlur(resized, (15, 15), 0)
            with self._lock:
                self._mask = blurred
        except Exception:
            pass
        finally:
            self._busy = False

    def darken_inside_mask(self, surface) -> None:
        """Apply the mask: dim pixels where the person silhouette is, so the
        existing background (webcam) shows through 'in front'."""
        import pygame  # local to keep file portable
        if not self._available or not self.settings.ar_occlusion:
            return
        with self._lock:
            mask = None if self._mask is None else self._mask.copy()
        if mask is None:
            return
        # Build an RGBA layer with alpha = 0 outside the body, ~180 inside.
        alpha = np.clip(mask * 220.0, 0, 220).astype(np.uint8)
        h, w = alpha.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 3] = alpha
        # pygame.image.frombuffer expects bytes
        try:
            layer = pygame.image.frombuffer(rgba.tobytes(), (w, h), "RGBA")
            layer = layer.convert_alpha()
            surface.blit(layer, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        except Exception:
            pass

    def shutdown(self):
        try:
            if self._segmenter is not None:
                self._segmenter.close()
        except Exception:
            pass
