"""Traditional Noise Reduction (Wiener / spectral subtraction) — Sprint 1 placeholder.

LLD-5: Hann window, zero-pad FFT, Wiener gain mask, overlap-add.
"""
import numpy as np
from ecnr_python.config.ecnr_config import NrConfig


class NrTraditional:
    def __init__(self, config: NrConfig, frame_size: int, sampling_rate: int):
        # TODO Sprint 1: initialise STFT buffers and noise estimate
        pass

    def process(self, frame: np.ndarray) -> np.ndarray:
        """frame: (frame_size,) → (frame_size,)"""
        # TODO Sprint 1: STFT → gain mask → overlap-add
        return frame.copy()
