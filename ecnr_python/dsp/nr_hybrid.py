"""Hybrid DL Noise Reduction (CRM mask) — Sprint 5 placeholder.

LLD-6: STFT feature extraction, CRM mask via PyTorch or ONNX Runtime, overlap-add.
"""
import numpy as np
from ecnr_python.config.ecnr_config import DlConfig


class NrHybrid:
    def __init__(self, config: DlConfig, frame_size: int, sampling_rate: int):
        # TODO Sprint 5: load model (PyTorch or ONNX), initialise STFT buffers
        pass

    def process(self, frame: np.ndarray) -> np.ndarray:
        """frame: (frame_size,) → (frame_size,)"""
        # TODO Sprint 5: extract features, run inference, apply CRM mask
        return frame.copy()
