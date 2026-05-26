"""Acoustic Echo Canceller (NLMS + DTD) — Sprint 2.

Port of phase1_matlab/aec/aec_init.m + aec_process.m + dtd_compute.m.
Algorithm: per-sample NLMS adaptive filter with frame-level double-talk detection.
"""
import math
import numpy as np
from ecnr_python.config.ecnr_config import AecConfig


class AEC:
    def __init__(self, config: AecConfig, frame_size: int):
        self._enabled = config.enabled
        self._step_size = config.step_size
        self._reg = config.regularization
        # MATLAB: dtd_threshold_lin = 10^(threshold_db / 10)  (power ratio)
        self._dtd_threshold_lin = 10.0 ** (config.double_talk_threshold_db / 10.0)
        self._erle_win = config.erle_window_frames

        L = config.filter_length
        self._w = np.zeros(L, dtype=np.float64)
        self._x_hist = np.zeros(L, dtype=np.float64)  # newest-first reference history

        self._erle_hist = np.full(config.erle_window_frames, np.nan)
        self._erle_hist_idx = 0

        # Exposed per-frame metrics
        self.dtd_active: bool = False
        self.erle_inst_db: float = math.nan
        self.erle_window_db: float = math.nan

    def process(self, mic_frame: np.ndarray, ref_frame: np.ndarray) -> np.ndarray:
        """Apply NLMS AEC.

        mic_frame: (frame_size,) — microphone input
        ref_frame:  (frame_size,) — far-end reference signal
        returns:    (frame_size,) — echo-cancelled residual
        """
        if not self._enabled:
            self.dtd_active = False
            self.erle_inst_db = math.nan
            self.erle_window_db = math.nan
            return mic_frame.copy()

        mic = mic_frame.astype(np.float64)
        ref = ref_frame.astype(np.float64)

        # Frame-level DTD: mic power vs reference power
        p_ref = np.mean(ref ** 2) + 1e-12
        self.dtd_active = bool((np.mean(mic ** 2) / p_ref) > self._dtd_threshold_lin)
        dtd = self.dtd_active

        N = len(mic)
        e = np.empty(N, dtype=np.float64)
        w = self._w
        x_hist = self._x_hist
        step = self._step_size
        reg = self._reg

        for n in range(N):
            # Shift history right (newest-first), insert current reference sample
            x_hist[1:] = x_hist[:-1]
            x_hist[0] = ref[n]

            y_hat = float(w @ x_hist)
            e[n] = mic[n] - y_hat

            if not dtd:
                norm_x = float(x_hist @ x_hist) + reg
                w += (step / norm_x) * e[n] * x_hist

        # ERLE: 10·log10(P_mic / P_residual)
        p_mic = np.mean(mic ** 2) + 1e-12
        p_e = np.mean(e ** 2) + 1e-12
        self.erle_inst_db = 10.0 * math.log10(p_mic / p_e)

        slot = self._erle_hist_idx % self._erle_win
        self._erle_hist[slot] = self.erle_inst_db
        self._erle_hist_idx += 1

        valid = self._erle_hist[~np.isnan(self._erle_hist)]
        self.erle_window_db = float(np.mean(valid)) if len(valid) > 0 else math.nan

        return e.astype(np.float32)
