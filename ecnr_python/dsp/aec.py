"""Acoustic Echo Canceller (NLMS + DTD) — Sprint 2 placeholder.

LLD-4: NLMS adaptive filter, circular reference history, double-talk detector.
"""
import numpy as np
from ecnr_python.config.ecnr_config import AecConfig


class AEC:
    def __init__(self, config: AecConfig, frame_size: int):
        # TODO Sprint 2: initialise NLMS filter taps and reference ring buffer
        self.dtd_active: bool = False

    def process(self, mic_frame: np.ndarray, ref_frame: np.ndarray) -> np.ndarray:
        """mic_frame: (frame_size,), ref_frame: (frame_size,) → (frame_size,)"""
        # TODO Sprint 2: NLMS update + residual output
        return mic_frame.copy()
