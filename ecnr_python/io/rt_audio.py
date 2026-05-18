import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from ecnr_python.config.ecnr_config import EcnrConfig

# (in_frame: (frame_size, mic_count), out_frame: (frame_size, 1)) -> None
# Callback must fill out_frame in-place.
FrameCallback = Callable[[np.ndarray, np.ndarray], None]

# Amplitude threshold to detect the loopback click (0–1 float32 scale)
_CLICK_DETECT_THRESHOLD = 0.05
# Length of the injected click impulse in samples
_CLICK_LEN = 8


class RtAudio:
    """sounddevice duplex stream wrapper for ECNR real-time demo.

    Usage:
        rt = RtAudio(cfg, frame_callback=my_cb)
        rt.start()
        ...
        rt.stop()
    """

    def __init__(
        self,
        config: EcnrConfig,
        frame_callback: Optional[FrameCallback] = None,
        input_device=None,
        output_device=None,
    ):
        self.config = config
        self.frame_callback = frame_callback if frame_callback is not None else _passthrough
        self.input_device = input_device
        self.output_device = output_device

        self.xrun_count: int = 0
        self._stream: Optional[sd.Stream] = None

        # Latency click state — written from main thread, read in callback
        self._click_lock = threading.Lock()
        self._click_pending: bool = False
        self._click_sent_ns: Optional[int] = None
        self._click_detected_ns: Optional[int] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._stream = sd.Stream(
            samplerate=self.config.sampling_rate,
            blocksize=self.config.frame_size,
            channels=(self.config.mic_count, 1),
            dtype="float32",
            latency="low",
            device=(self.input_device, self.output_device),
            callback=self._sd_callback,
        )
        self._stream.start()
        lat = self._stream.latency
        print(
            f"[rt_audio] Stream started  "
            f"input_lat={lat[0]*1000:.1f} ms  "
            f"output_lat={lat[1]*1000:.1f} ms  "
            f"reported_total={sum(lat)*1000:.1f} ms"
        )

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print(f"[rt_audio] Stream stopped  total_xruns={self.xrun_count}")

    def measure_latency(self) -> None:
        """Inject a click into the output; prints round-trip when detected in input.

        Requires the speaker output to be acoustically or electrically looped back
        into the mic input.  The reported sounddevice latency is always printed at
        stream start; this method measures the *acoustic* round-trip on top of that.
        """
        with self._click_lock:
            self._click_detected_ns = None
            self._click_sent_ns = None
            self._click_pending = True
        print("[rt_audio] Click injected — waiting for acoustic round-trip ...")

    def round_trip_ms(self) -> Optional[float]:
        """Return measured acoustic round-trip in ms, or None if not yet detected."""
        with self._click_lock:
            if self._click_sent_ns is not None and self._click_detected_ns is not None:
                return (self._click_detected_ns - self._click_sent_ns) / 1e6
        return None

    # ------------------------------------------------------------------
    # sounddevice callback (runs in PortAudio native thread — no GIL)
    # ------------------------------------------------------------------

    def _sd_callback(
        self,
        indata: np.ndarray,   # (frame_size, mic_count)  float32
        outdata: np.ndarray,  # (frame_size, 1)           float32
        frames: int,
        time_info,
        status: sd.CallbackFlags,
    ) -> None:
        if status.input_overflow or status.output_underflow:
            self.xrun_count += 1
            print(f"[rt_audio] XRUN #{self.xrun_count}: {status}")

        outdata[:] = 0.0

        with self._click_lock:
            click_pending = self._click_pending
            waiting_for_click = (
                self._click_sent_ns is not None and self._click_detected_ns is None
            )

        if click_pending:
            # Inject click
            click_len = min(_CLICK_LEN, frames)
            outdata[:click_len, 0] = 1.0
            with self._click_lock:
                self._click_sent_ns = time.perf_counter_ns()
                self._click_pending = False
        elif waiting_for_click:
            # Check for loopback click in mic channel 0
            if np.max(np.abs(indata[:, 0])) > _CLICK_DETECT_THRESHOLD:
                with self._click_lock:
                    self._click_detected_ns = time.perf_counter_ns()
                    rtt = (self._click_detected_ns - self._click_sent_ns) / 1e6
                print(f"[rt_audio] Click detected  acoustic_round_trip={rtt:.1f} ms")

        self.frame_callback(indata, outdata)


# ------------------------------------------------------------------
# Default passthrough callback
# ------------------------------------------------------------------

def _passthrough(in_frame: np.ndarray, out_frame: np.ndarray) -> None:
    out_frame[:, 0] = in_frame[:, 0]
