"""Traditional Noise Reduction (Wiener / spectral subtraction) — Sprint 1.

Port of phase1_matlab/nr/nr_trad_init.m + nr_trad_process.m.
Algorithm: two 50%-OLA segments per frame, periodic Hann window, zero-pad FFT,
per-bin Wiener gain, overlap-add reconstruction.
"""
import numpy as np
from ecnr_python.config.ecnr_config import NrConfig


class NrTraditional:
    def __init__(self, config: NrConfig, frame_size: int, sampling_rate: int):
        if frame_size % 2 != 0:
            raise ValueError("frame_size must be even for 50% OLA NR")

        N = frame_size
        # Next power of 2 >= N  (e.g. N=320 → Nf=512, N=256 → Nf=256)
        Nf = 1 << (N - 1).bit_length()

        self._enabled = config.enabled
        self._N = N
        self._Nf = Nf
        self._hop = N // 2
        self._alpha = config.noise_smooth_alpha
        self._floor_lin = 10.0 ** (config.spectral_floor_db / 20.0)
        # aggressiveness_db 0 dB → lambda=1.0, 24 dB → lambda=2.5  (matches MATLAB)
        self._lambda = 1.0 + (config.aggressiveness_db / 24.0) * 1.5

        # Periodic Hann window: matches MATLAB hann(N, 'periodic')
        # Required for 50% OLA to sum to 1: win[n] + win[n + hop] = 1
        self._win = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(N) / N))

        # State arrays (float64 for numeric parity with MATLAB double)
        # noise_psd is None until the first frame seeds it from real spectral power;
        # a hardcoded 1e-6 initial value causes the noise gate to stay closed
        # because real audio power (~1e-4) is always >10× larger than 1e-6.
        self._noise_psd: np.ndarray | None = None
        self._prev_in = np.zeros(N, dtype=np.float64)
        self._ola_buf = np.zeros(N, dtype=np.float64)

        # Exposed per-frame metrics (updated each process() call)
        self.snr_in_db: float = 0.0
        self.snr_out_db: float = 0.0

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Apply Wiener NR.  frame: (frame_size,) → (frame_size,)."""
        if not self._enabled:
            return frame.copy()

        N, Nf, hop = self._N, self._Nf, self._hop
        e = frame.astype(np.float64)

        # Two 50%-OLA analysis segments (matches MATLAB seg1/seg2 formation)
        # seg1: last hop of previous frame + first hop of current frame
        # seg2: full current frame
        seg1 = np.concatenate([self._prev_in[hop:], e[:hop]])
        y_out = np.zeros(N, dtype=np.float64)

        for k, seg in enumerate((seg1, e)):
            # Analysis: periodic-Hann window + zero-pad FFT
            X = np.fft.rfft(self._win * seg, n=Nf)
            P = np.abs(X) ** 2

            # Seed noise PSD from first real frame so the gate level is realistic.
            # A fixed 1e-6 init keeps the gate permanently closed for normal audio.
            if self._noise_psd is None:
                self._noise_psd = P.copy() + 1e-12

            # Noise PSD update: IIR, gated when frame looks noise-like
            # (instantaneous power within 10 dB of current estimate)
            if np.mean(P) < 10.0 * (np.mean(self._noise_psd) + 1e-12):
                self._noise_psd[:] = (self._alpha * self._noise_psd
                                      + (1.0 - self._alpha) * P)

            # Per-bin Wiener gain: G[k] = max(floor, 1 - lambda / (SNR_post[k] + 1))
            snr_post = P / (self._noise_psd + 1e-12)
            G = np.maximum(self._floor_lin, 1.0 - self._lambda / (snr_post + 1.0))

            # Synthesis: apply gain, IFFT, take first N samples
            y_seg = np.fft.irfft(G * X, n=Nf)[:N]

            # Overlap-add: accumulate, emit one hop, shift buffer
            self._ola_buf += y_seg
            y_out[k * hop:(k + 1) * hop] = self._ola_buf[:hop]
            self._ola_buf[:hop] = self._ola_buf[hop:N]
            self._ola_buf[hop:] = 0.0

        self._prev_in[:] = e

        noise_power = np.mean(self._noise_psd) + 1e-12
        self.snr_in_db = 10.0 * np.log10(np.mean(e ** 2) / noise_power)
        self.snr_out_db = 10.0 * np.log10(np.mean(y_out ** 2) / noise_power)

        return y_out.astype(np.float32)
