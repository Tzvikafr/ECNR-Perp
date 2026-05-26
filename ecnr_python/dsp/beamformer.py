"""DAS Beamformer with Lagrange fractional-delay FIR — Sprint 3.

Port of LLD-3 (bf_compute_delays + bf_process).
Adds fractional-delay accuracy on top of the MATLAB equal-weight DAS baseline.
"""
import math
import numpy as np
from ecnr_python.config.ecnr_config import BfConfig, ArrayGeo, BfType

_SPEED_OF_SOUND = 343.0  # m/s @ 20°C
_FIR_TAPS = 8            # Lagrange order-7 (8 coefficients)
_DELAY_LINE_LEN = 64     # ≤ 4 ms @ 16 kHz


def _lagrange_coeffs(frac: float, n_taps: int = _FIR_TAPS) -> np.ndarray:
    """Order-(n_taps-1) Lagrange FIR coefficients for fractional delay `frac`."""
    c = np.ones(n_taps, dtype=np.float64)
    for j in range(n_taps):
        for m in range(n_taps):
            if m != j:
                c[j] *= (frac - m) / (j - m)
    return c


class Beamformer:
    def __init__(self, config: BfConfig, sampling_rate: int, frame_size: int, mic_count: int):
        M = mic_count
        self._enabled = config.enabled and M > 1
        self._M = M
        self._frame_size = frame_size
        self._w = np.full(M, 1.0 / M, dtype=np.float64)  # uniform DAS weights

        # Per-mic delay lines and fractional-delay FIR coefficients
        self._delay_lines = np.zeros((M, _DELAY_LINE_LEN), dtype=np.float64)
        self._frac_coeffs = np.zeros((M, _FIR_TAPS), dtype=np.float64)
        self._int_delays = np.zeros(M, dtype=int)

        if self._enabled:
            self._compute_delays(config, sampling_rate)
            sr = sampling_rate
            max_d = int(np.max(self._int_delays))
            self.latency_ms = max_d / sr * 1000.0
            print(f"[bf] DAS  mics={M}  spacing={config.spacing_m*100:.1f} cm  "
                  f"steer={config.steering_angle_deg:.1f} deg  "
                  f"latency<={self.latency_ms:.2f} ms")

    def _compute_delays(self, config: BfConfig, sr: int) -> None:
        angle_rad = math.radians(config.steering_angle_deg)
        for i in range(self._M):
            if config.geometry == ArrayGeo.LINEAR:
                dist = i * config.spacing_m * math.cos(angle_rad)
            else:  # CIRCULAR
                a = 2 * math.pi * i / self._M + angle_rad
                dist = (config.spacing_m / 2.0) * math.cos(a)

            delay_exact = dist * sr / _SPEED_OF_SOUND
            self._int_delays[i] = int(math.floor(delay_exact))
            frac = delay_exact - self._int_delays[i]
            self._frac_coeffs[i] = _lagrange_coeffs(frac)

    def process(self, mic_frame: np.ndarray) -> np.ndarray:
        """mic_frame: (frame_size, mic_count) → (frame_size,)."""
        if not self._enabled:
            return mic_frame[:, 0].copy()

        N = self._frame_size
        out = np.zeros(N, dtype=np.float64)

        for n in range(N):
            acc = 0.0
            for i in range(self._M):
                # Insert new sample at front of delay line
                self._delay_lines[i, 1:] = self._delay_lines[i, :-1]
                self._delay_lines[i, 0] = float(mic_frame[n, i])

                # Fractional-delay FIR output
                delayed = float(self._frac_coeffs[i] @ self._delay_lines[i, :_FIR_TAPS])
                acc += self._w[i] * delayed

            out[n] = acc

        return out.astype(np.float32)
