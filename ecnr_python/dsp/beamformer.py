"""DAS Beamformer — Sprint 3 placeholder.

LLD-3: geometric delay computation, Lagrange FIR fractional delay, DAS accumulation.
"""
import numpy as np
from ecnr_python.config.ecnr_config import BfConfig


class Beamformer:
    def __init__(self, config: BfConfig, sampling_rate: int, frame_size: int):
        # TODO Sprint 3: compute per-channel integer + fractional delays
        pass

    def process(self, mic_frame: np.ndarray) -> np.ndarray:
        """mic_frame: (frame_size, mic_count) → (frame_size,)"""
        # TODO Sprint 3: apply delays and sum
        return mic_frame[:, 0].copy()
