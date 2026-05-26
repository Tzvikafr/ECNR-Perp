import math
import time
from typing import Optional

import numpy as np

from ecnr_python.config.ecnr_config import EcnrConfig, EcnrMode, BfType
from ecnr_python.dsp.aec import AEC
from ecnr_python.dsp.beamformer import Beamformer
from ecnr_python.dsp.nr_traditional import NrTraditional


class EcnrEngine:
    """Frame-level dispatcher: routes each frame through the enabled DSP stages.

    Stage order: Beamformer → AEC → NR (Traditional or Hybrid)
    """

    def __init__(self, config: EcnrConfig):
        self.config = config
        self._nr_hybrid = None    # Sprint 5: Hybrid DL NR
        self._frame_count = 0
        self._viz = None          # Sprint 4: RtViz (optional)
        self._profile = False
        self._timings: dict = {"bf": [], "aec": [], "nr": []}
        self._bypass = False      # when True: passthrough, no DSP

        # Sprint 3: Beamformer
        if config.beamformer.enabled and config.beamformer.type == BfType.DAS and config.mic_count > 1:
            self._bf = Beamformer(
                config.beamformer, config.sampling_rate, config.frame_size, config.mic_count
            )
        else:
            self._bf = None

        # Sprint 2: AEC
        if config.aec.enabled:
            self._aec = AEC(config.aec, config.frame_size)
            print(f"[engine] AEC enabled  "
                  f"filter_length={config.aec.filter_length}  "
                  f"step_size={config.aec.step_size}  "
                  f"dtd_threshold={config.aec.double_talk_threshold_db} dB")
        else:
            self._aec = None

        # Sprint 1: Traditional NR
        if config.nr.enabled and config.mode == EcnrMode.TRADITIONAL:
            self._nr = NrTraditional(config.nr, config.frame_size, config.sampling_rate)
            print(f"[engine] NrTraditional enabled  "
                  f"agg={config.nr.aggressiveness_db:.0f} dB  "
                  f"alpha={config.nr.noise_smooth_alpha:.2f}")
        else:
            self._nr = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def process_frame(self, mic_frame: np.ndarray, ref_frame: np.ndarray) -> np.ndarray:
        """Process one frame through the enabled pipeline.

        Args:
            mic_frame: (frame_size, mic_count) float32
            ref_frame: (frame_size,) float32

        Returns:
            (frame_size,) float32
        """
        # Bypass mode: raw mic channel 0 straight to output, no DSP
        if self._bypass:
            signal = mic_frame[:, 0].copy()
            if self._viz is not None:
                self._viz.push(signal, signal, math.nan, 0.0, 0.0, False)
            return signal

        p = self._profile

        # Stage 1: Beamformer
        if self._bf is not None and self.config.beamformer.enabled:
            if p: _t0 = time.perf_counter_ns()
            signal = self._bf.process(mic_frame)
            if p: self._timings["bf"].append(time.perf_counter_ns() - _t0)
        else:
            signal = mic_frame[:, 0].copy()

        # Stage 2: AEC
        if self._aec is not None and self.config.aec.enabled:
            if p: _t0 = time.perf_counter_ns()
            signal = self._aec.process(signal, ref_frame)
            if p: self._timings["aec"].append(time.perf_counter_ns() - _t0)

        # Stage 3: NR
        if self.config.mode == EcnrMode.HYBRID and self._nr_hybrid is not None:
            signal = self._nr_hybrid.process(signal)
        elif self._nr is not None and self.config.nr.enabled:
            if p: _t0 = time.perf_counter_ns()
            signal = self._nr.process(signal)
            if p: self._timings["nr"].append(time.perf_counter_ns() - _t0)

        self._frame_count += 1
        if self._frame_count % 10 == 0:
            self._print_status()

        if self._viz is not None:
            erle   = float(self._aec.erle_window_db) if self._aec is not None else math.nan
            snr_in  = self._nr.snr_in_db  if self._nr is not None else 0.0
            snr_out = self._nr.snr_out_db if self._nr is not None else 0.0
            dtd    = self._aec.dtd_active if self._aec is not None else False
            self._viz.push(mic_frame[:, 0], signal, erle, snr_in, snr_out, dtd)

        return signal

    def set_viz(self, viz) -> None:
        self._viz = viz

    def set_bypass(self, enabled: bool) -> None:
        """Toggle full bypass (passthrough). Safe to call from any thread."""
        self._bypass = enabled
        print(f"[engine] bypass={'ON (passthrough)' if enabled else 'OFF (ECNR active)'}")

    def set_profile(self, enabled: bool) -> None:
        self._profile = enabled
        if enabled:
            self._timings = {"bf": [], "aec": [], "nr": []}

    def profile_report(self) -> dict:
        """Return per-module timing stats dict: {name: {mean_us, p99_us}}."""
        result = {}
        for name, times in self._timings.items():
            if times:
                arr = np.array(times, dtype=np.float64) / 1e3  # ns → µs
                result[name] = {
                    "mean_us": float(np.mean(arr)),
                    "p99_us":  float(np.percentile(arr, 99)),
                    "n":       len(times),
                }
            else:
                result[name] = {"mean_us": 0.0, "p99_us": 0.0, "n": 0}
        return result

    # ------------------------------------------------------------------ #
    # Sub-module accessors (used by offline_runner to collect metrics)    #
    # ------------------------------------------------------------------ #

    @property
    def aec(self) -> Optional[AEC]:
        return self._aec

    @property
    def nr(self) -> Optional[NrTraditional]:
        return self._nr

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _print_status(self) -> None:
        parts = [f"frame={self._frame_count:6d}"]
        if self._aec is not None:
            erle = (f"{self._aec.erle_window_db:+5.1f} dB"
                    if not math.isnan(self._aec.erle_window_db) else "   nan")
            dtd = " DTD" if self._aec.dtd_active else "    "
            parts.append(f"ERLE={erle}{dtd}")
        if self._nr is not None:
            delta = self._nr.snr_out_db - self._nr.snr_in_db
            parts.append(
                f"SNR {self._nr.snr_in_db:+5.1f}→{self._nr.snr_out_db:+5.1f} dB"
                f" ({delta:+.1f})"
            )
        print("[ecnr] " + "  ".join(parts))
