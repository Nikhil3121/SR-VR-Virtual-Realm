"""One Euro Filter — adaptive low-pass for noisy pointer input (Casiez et al. 2012)."""

from __future__ import annotations

import math
import time


class _LowPass:
    __slots__ = ("hat_x_prev", "initialized")

    def __init__(self):
        self.hat_x_prev = 0.0
        self.initialized = False

    def __call__(self, x: float, alpha: float) -> float:
        if not self.initialized:
            self.hat_x_prev = x
            self.initialized = True
            return x
        hat = alpha * x + (1.0 - alpha) * self.hat_x_prev
        self.hat_x_prev = hat
        return hat


class OneEuroFilter:
    """
    1-D One Euro Filter.

    Parameters:
        min_cutoff: lower bound for the cutoff frequency (Hz). Smaller =
                    smoother when stationary.
        beta:       speed-dependent slope. Bigger = more responsive when moving.
        d_cutoff:   cutoff frequency for the speed estimate's own low-pass.
    """

    __slots__ = ("min_cutoff", "beta", "d_cutoff",
                 "_x_filter", "_dx_filter", "_last_time")

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.015,
                 d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_filter = _LowPass()
        self._dx_filter = _LowPass()
        self._last_time: float | None = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float | None = None) -> float:
        if t is None:
            t = time.time()
        if self._last_time is None:
            self._last_time = t
            self._x_filter(x, 1.0)
            return x
        dt = max(1e-6, t - self._last_time)
        self._last_time = t

        # Speed estimate (low-passed)
        if not self._x_filter.initialized:
            dx = 0.0
        else:
            dx = (x - self._x_filter.hat_x_prev) / dt
        edx = self._dx_filter(dx, self._alpha(self.d_cutoff, dt))

        # Adaptive cutoff
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self._x_filter(x, self._alpha(cutoff, dt))

    def reset(self):
        self._x_filter = _LowPass()
        self._dx_filter = _LowPass()
        self._last_time = None


class Vec2Filter:
    """Convenience: two OneEuroFilters sharing the same parameters."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.015,
                 d_cutoff: float = 1.0):
        self.fx = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self.fy = OneEuroFilter(min_cutoff, beta, d_cutoff)

    def __call__(self, x: float, y: float, t: float | None = None) -> tuple:
        if t is None:
            t = time.time()
        return (self.fx(x, t), self.fy(y, t))

    def configure(self, min_cutoff: float, beta: float):
        for f in (self.fx, self.fy):
            f.min_cutoff = min_cutoff
            f.beta = beta

    def reset(self):
        self.fx.reset()
        self.fy.reset()
