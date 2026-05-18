import numpy as np

from ecnr_python.config.ecnr_config import EcnrConfig, EcnrMode, BfType


class EcnrEngine:
    """Frame-level dispatcher: routes each frame through the enabled DSP stages.

    Stage order: Beamformer → AEC → NR (Traditional or Hybrid)

    DSP module instances are None until the corresponding sprint wires them in.
    A None module is treated as a bypass — the signal passes through unchanged.
    """

    def __init__(self, config: EcnrConfig):
        self.config = config
        self._bf = None       # Sprint 3: Beamformer
        self._aec = None      # Sprint 2: AEC
        self._nr = None       # Sprint 1: Traditional NR
        self._nr_hybrid = None  # Sprint 5: Hybrid DL NR

    def process_frame(self, mic_frame: np.ndarray, ref_frame: np.ndarray) -> np.ndarray:
        """Process one frame through the enabled pipeline.

        Args:
            mic_frame: (frame_size, mic_count) float32 — raw mic input
            ref_frame: (frame_size,) float32 — far-end reference signal

        Returns:
            (frame_size,) float32 — processed output
        """
        cfg = self.config

        # Stage 1: Beamformer (multi-mic → single channel)
        if cfg.beamformer.enabled and cfg.beamformer.type == BfType.DAS and self._bf is not None:
            signal = self._bf.process(mic_frame)
        else:
            signal = mic_frame[:, 0].copy()

        # Stage 2: AEC
        if cfg.aec.enabled and self._aec is not None:
            signal = self._aec.process(signal, ref_frame)

        # Stage 3: NR
        if cfg.mode == EcnrMode.HYBRID and self._nr_hybrid is not None:
            signal = self._nr_hybrid.process(signal)
        elif cfg.nr.enabled and self._nr is not None:
            signal = self._nr.process(signal)

        return signal
