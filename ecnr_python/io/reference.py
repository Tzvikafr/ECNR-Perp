"""Reference source abstraction — Sprint 2.

Two backends, swappable via config reference.source_type:
  'file'     — read WAV file frame-by-frame (offline scenario)
  'loopback' — WASAPI loopback capture via sounddevice InputStream (Windows)
"""
import math
import queue
import numpy as np
from ecnr_python.config.ecnr_config import RefConfig


class ReferenceSource:
    def __init__(self, config: RefConfig, frame_size: int, sampling_rate: int):
        self._frame_size = frame_size
        self._sr = sampling_rate
        self._source_type = config.source_type

        self._file_data: np.ndarray | None = None
        self._file_ptr: int = 0
        self._stream = None
        self._queue: queue.Queue | None = None

        if config.source_type == "file":
            self._open_file(config.file_path, config.delay_compensation_samples)
        elif config.source_type == "loopback":
            self._open_loopback(config)
        elif config.source_type != "none":
            print(f"[ref] Unknown source_type '{config.source_type}' — returning silence")

    def _open_file(self, path: str, delay_samples: int) -> None:
        if not path:
            print("[ref] source_type='file' but no file_path set — returning silence")
            return
        try:
            import soundfile as sf
            data, sr = sf.read(path, dtype="float32", always_2d=True)
            if sr != self._sr:
                raise ValueError(
                    f"Reference WAV sample rate {sr} Hz != engine {self._sr} Hz"
                )
            self._file_data = data[:, 0]
            self._file_ptr = max(0, delay_samples)
            print(
                f"[ref] file '{path}'  "
                f"{len(self._file_data)} samples @ {sr} Hz  "
                f"delay_offset={self._file_ptr}"
            )
        except Exception as exc:
            print(f"[ref] Failed to open '{path}': {exc} — returning silence")

    def _open_loopback(self, config: RefConfig) -> None:
        try:
            import sounddevice as sd
            self._queue = queue.Queue(maxsize=64)
            ch_idx = config.channel_index

            wasapi_opts = sd.WasapiSettings(loopback=True)
            device = config.device_id if config.device_id else sd.default.device[1]

            def _cb(indata, frames, time_info, status):
                if status:
                    print(f"[ref/loopback] {status}")
                mono = indata[:, min(ch_idx, indata.shape[1] - 1)].copy()
                try:
                    self._queue.put_nowait(mono)
                except queue.Full:
                    pass

            self._stream = sd.InputStream(
                samplerate=self._sr,
                blocksize=self._frame_size,
                device=device,
                channels=1,
                dtype="float32",
                extra_settings=wasapi_opts,
                callback=_cb,
            )
            self._stream.start()
            print(f"[ref] WASAPI loopback started  device={device}")
        except Exception as exc:
            print(f"[ref] Loopback init failed: {exc} — returning silence")
            self._stream = None
            self._queue = None

    def read_frame(self) -> np.ndarray:
        """Return next far-end reference frame: (frame_size,) float32."""
        N = self._frame_size

        if self._source_type == "file" and self._file_data is not None:
            start = self._file_ptr
            end = start + N
            if start >= len(self._file_data):
                return np.zeros(N, dtype=np.float32)
            chunk = self._file_data[start:end]
            self._file_ptr += N
            if len(chunk) < N:
                chunk = np.pad(chunk, (0, N - len(chunk)))
            return chunk

        if self._source_type == "loopback" and self._queue is not None:
            try:
                return self._queue.get_nowait()
            except queue.Empty:
                return np.zeros(N, dtype=np.float32)

        return np.zeros(N, dtype=np.float32)

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
