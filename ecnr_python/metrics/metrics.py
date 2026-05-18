"""Metrics engine — Sprint 1/2 placeholder.

LLD-7: ERLE, segmental SNR, DTD transparency, convergence time.
"""
import numpy as np
from ecnr_python.config.ecnr_config import EcnrConfig


class Metrics:
    def __init__(self, config: EcnrConfig):
        self.erle_db: float = 0.0
        self.snr_in_db: float = 0.0
        self.snr_out_db: float = 0.0
        self._frame_count: int = 0

    def update(
        self,
        mic_frame: np.ndarray,
        ref_frame: np.ndarray,
        out_frame: np.ndarray,
        dtd_active: bool = False,
    ) -> None:
        """Update running metrics with one frame of data."""
        # TODO Sprint 1: compute segmental SNR
        # TODO Sprint 2: compute ERLE
        self._frame_count += 1

    def report(self) -> str:
        return (
            f"ERLE={self.erle_db:.1f} dB  "
            f"SNR_in={self.snr_in_db:.1f} dB  "
            f"SNR_out={self.snr_out_db:.1f} dB"
        )
