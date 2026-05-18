"""Reference source abstraction — Sprint 2 placeholder.

LLD (AD-06): supports 'file' (synchronised playback) and 'loopback' (WASAPI loopback).
Swappable via config reference.source_type without code changes.
"""
import numpy as np
from ecnr_python.config.ecnr_config import RefConfig


class ReferenceSource:
    def __init__(self, config: RefConfig, frame_size: int, sampling_rate: int):
        # TODO Sprint 2: open file or WASAPI loopback stream
        self.config = config
        self.frame_size = frame_size

    def read_frame(self) -> np.ndarray:
        """Return next far-end reference frame: (frame_size,) float32."""
        # TODO Sprint 2: read from file or loopback capture
        return np.zeros(self.frame_size, dtype="float32")

    def close(self) -> None:
        pass
