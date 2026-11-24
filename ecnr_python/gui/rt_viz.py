"""Live visualisation — Sprint 4.

Layout:
  Left panel   — DTD indicator, ERLE/SNR gauges, Record button
  Right panel  — input spectrogram | output spectrogram (top)
                 ERLE time series  |  SNR-delta time series (bottom)

Threading model:
  Audio callback  →  push() (non-blocking)  →  queue
  Qt timer @ 100 ms  →  _drain_queue()  →  plot updates

Requires: PyQt5, pyqtgraph, soundfile (all in requirements.txt Sprint 4).
Falls back gracefully if imports fail.
"""
import math
import json
import queue
import time
from collections import deque
from pathlib import Path

import numpy as np

try:
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtWidgets import (
        QApplication, QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox,
        QHBoxLayout, QLabel, QMainWindow, QPushButton, QSpinBox, QVBoxLayout, QWidget,
    )
    import pyqtgraph as pg
    _GUI_AVAILABLE = True
except ImportError:
    _GUI_AVAILABLE = False

from ecnr_python.config.ecnr_config import EcnrConfig

_SPEC_COLS = 300          # scrolling spectrogram width (columns = frames ≈ 6 s @ 50 fps)
_DISPLAY_SECS = 30        # ERLE/SNR time-series window
_FFT_SIZE = 512           # spectrogram FFT size


class RtViz:
    def __init__(self, config: EcnrConfig, record_path: str = "ecnr_capture.wav",
                 bypass_callback=None, engine=None):
        """
        bypass_callback: callable(bool) — called with True/False when the
                         ECNR ON/OFF button is toggled. Wire to engine.set_bypass().
        """
        self._config = config
        self._sr = config.sampling_rate
        self._fs = config.frame_size
        self._record_path = record_path
        self._bypass_callback = bypass_callback
        self._engine = engine
        self._rt_audio = None
        self._last_rtt_ms = None
        self._bypass_active = False

        self._queue: queue.Queue = queue.Queue(maxsize=512)

        # Rolling time-series buffers
        fps = self._sr / self._fs
        n_disp = int(_DISPLAY_SECS * fps)
        self._erle_buf = deque([0.0] * n_disp, maxlen=n_disp)
        self._snr_delta_buf = deque([0.0] * n_disp, maxlen=n_disp)

        # Scrolling spectrogram (deque of column vectors)
        self._n_bins = _FFT_SIZE // 2 + 1
        self._spec_in_cols: deque = deque(maxlen=_SPEC_COLS)
        self._spec_out_cols: deque = deque(maxlen=_SPEC_COLS)
        # Hann window for spectrogram display (matches frame size, not FFT size)
        n_win = min(self._fs, _FFT_SIZE)
        self._spec_win = np.hanning(n_win)

        # Recording
        self._recording = False
        self._record_buf: list = []

        # Qt objects (populated in _build_window)
        self._app = None
        self._win = None

    # ------------------------------------------------------------------ #
    # Public API (called from audio thread or main thread)                #
    # ------------------------------------------------------------------ #

    def push(self, frame_in: np.ndarray, frame_out: np.ndarray,
             erle: float, snr_in: float, snr_out: float, dtd_active: bool) -> None:
        """Non-blocking push from audio callback (real-time safe)."""
        try:
            self._queue.put_nowait({
                "in": frame_in.astype(np.float32),
                "out": frame_out.astype(np.float32),
                "erle": erle,
                "snr_in": snr_in,
                "snr_out": snr_out,
                "dtd": dtd_active,
            })
        except queue.Full:
            pass

        if self._recording:
            self._record_buf.append(frame_out.astype(np.float32))

    def run(self, duration: float) -> None:
        """Start Qt event loop in the calling thread. Blocks until done."""
        import sys
        if not _GUI_AVAILABLE:
            print("[viz] PyQt5/pyqtgraph not available — run without --gui")
            return

        pg.setConfigOptions(antialias=False, useOpenGL=False)
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._build_window()

        update_timer = QTimer()
        update_timer.timeout.connect(self._drain_queue)
        update_timer.start(100)  # ~100 ms ≈ 5 frames at 50 fps

        latency_timer = QTimer()
        latency_timer.timeout.connect(self._poll_latency)
        latency_timer.start(200)

        self._start = time.perf_counter()
        self._duration = duration
        dur_timer = QTimer()
        dur_timer.timeout.connect(self._check_done)
        dur_timer.start(500)

        self._win.show()
        self._app.exec_()

    def stop(self) -> None:
        if self._app is not None:
            self._app.quit()

    def set_rt_audio(self, rt_audio) -> None:
        self._rt_audio = rt_audio

    # ------------------------------------------------------------------ #
    # Window construction                                                  #
    # ------------------------------------------------------------------ #

    def _build_window(self) -> None:
        self._win = QMainWindow()
        self._win.setWindowTitle("ECNR Real-Time Monitor")
        self._win.resize(1280, 720)

        central = QWidget()
        self._win.setCentralWidget(central)
        root = QHBoxLayout(central)

        # ---- Left: status + controls ----
        left = QWidget()
        left.setFixedWidth(200)
        lv = QVBoxLayout(left)
        lv.setAlignment(Qt.AlignTop)
        lv.setSpacing(10)

        # ECNR ON/OFF toggle — most prominent control at top
        self._bypass_btn = QPushButton("ECNR: ON")
        self._bypass_btn.setCheckable(True)
        self._bypass_btn.setChecked(False)
        self._bypass_btn.setMinimumHeight(44)
        self._bypass_btn.setStyleSheet(
            "QPushButton { background:#1565c0; color:white; font-size:14px; "
            "font-weight:bold; border-radius:6px; }"
            "QPushButton:checked { background:#b71c1c; }"
        )
        self._bypass_btn.toggled.connect(self._on_bypass_toggle)
        lv.addWidget(self._bypass_btn)

        # DTD indicator
        dtd_box = QGroupBox("Double-Talk")
        dtd_inner = QVBoxLayout(dtd_box)
        self._dtd_label = QLabel("OFF")
        self._dtd_label.setAlignment(Qt.AlignCenter)
        self._dtd_label.setStyleSheet(
            "background:#2e7d32; color:white; padding:8px; border-radius:4px; font-weight:bold;"
        )
        dtd_inner.addWidget(self._dtd_label)
        lv.addWidget(dtd_box)

        # Module controls
        ctrl_box = QGroupBox("Module Controls")
        ctrl_form = QFormLayout(ctrl_box)

        self._bf_enable = QCheckBox("Beamformer ON")
        self._bf_enable.setChecked(self._config.beamformer.enabled)
        self._bf_enable.toggled.connect(self._on_bf_toggle)
        ctrl_form.addRow(self._bf_enable)

        self._bf_angle = QDoubleSpinBox()
        self._bf_angle.setRange(-90.0, 90.0)
        self._bf_angle.setDecimals(1)
        self._bf_angle.setSingleStep(5.0)
        self._bf_angle.setValue(float(self._config.beamformer.steering_angle_deg))
        self._bf_angle.valueChanged.connect(self._on_bf_angle_change)
        ctrl_form.addRow("BF steer (deg)", self._bf_angle)

        self._aec_enable = QCheckBox("AEC ON")
        self._aec_enable.setChecked(self._config.aec.enabled)
        self._aec_enable.toggled.connect(self._on_aec_toggle)
        ctrl_form.addRow(self._aec_enable)

        self._aec_step = QDoubleSpinBox()
        self._aec_step.setRange(0.001, 1.0)
        self._aec_step.setDecimals(3)
        self._aec_step.setSingleStep(0.01)
        self._aec_step.setValue(float(self._config.aec.step_size))
        self._aec_step.valueChanged.connect(self._on_aec_step_change)
        ctrl_form.addRow("AEC step", self._aec_step)

        self._aec_dtd = QDoubleSpinBox()
        self._aec_dtd.setRange(-20.0, 40.0)
        self._aec_dtd.setDecimals(1)
        self._aec_dtd.setSingleStep(1.0)
        self._aec_dtd.setValue(float(self._config.aec.double_talk_threshold_db))
        self._aec_dtd.valueChanged.connect(self._on_aec_dtd_change)
        ctrl_form.addRow("AEC DTD (dB)", self._aec_dtd)

        self._nr_enable = QCheckBox("NR ON")
        self._nr_enable.setChecked(self._config.nr.enabled)
        self._nr_enable.toggled.connect(self._on_nr_toggle)
        ctrl_form.addRow(self._nr_enable)

        self._nr_aggr = QDoubleSpinBox()
        self._nr_aggr.setRange(0.0, 24.0)
        self._nr_aggr.setDecimals(1)
        self._nr_aggr.setSingleStep(1.0)
        self._nr_aggr.setValue(float(self._config.nr.aggressiveness_db))
        self._nr_aggr.valueChanged.connect(self._on_nr_aggr_change)
        ctrl_form.addRow("NR aggressiveness", self._nr_aggr)

        self._nr_alpha = QDoubleSpinBox()
        self._nr_alpha.setRange(0.85, 0.99)
        self._nr_alpha.setDecimals(3)
        self._nr_alpha.setSingleStep(0.005)
        self._nr_alpha.setValue(float(self._config.nr.noise_smooth_alpha))
        self._nr_alpha.valueChanged.connect(self._on_nr_alpha_change)
        ctrl_form.addRow("NR smooth alpha", self._nr_alpha)

        lv.addWidget(ctrl_box)

        # Latency controls
        lat_box = QGroupBox("Latency")
        lat_form = QFormLayout(lat_box)

        self._lat_meas_btn = QPushButton("Measure RTT")
        self._lat_meas_btn.clicked.connect(self._on_measure_latency)
        lat_form.addRow(self._lat_meas_btn)

        self._lat_label = QLabel("RTT: -- ms")
        lat_form.addRow(self._lat_label)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 48000)
        self._delay_spin.setSingleStep(16)
        self._delay_spin.setValue(int(self._config.reference.delay_compensation_samples))
        lat_form.addRow("Delay samples", self._delay_spin)

        self._lat_store_btn = QPushButton("Store delay to config")
        self._lat_store_btn.clicked.connect(self._on_store_delay)
        lat_form.addRow(self._lat_store_btn)

        self._lat_status = QLabel("")
        self._lat_status.setWordWrap(True)
        lat_form.addRow(self._lat_status)

        lv.addWidget(lat_box)

        # Metric readouts
        metrics_box = QGroupBox("Metrics")
        mv = QVBoxLayout(metrics_box)
        self._erle_label = QLabel("ERLE:  — dB")
        self._snr_label = QLabel("SNR Δ: — dB")
        for lbl in (self._erle_label, self._snr_label):
            lbl.setAlignment(Qt.AlignLeft)
            mv.addWidget(lbl)
        lv.addWidget(metrics_box)

        # Record button
        rec_box = QGroupBox("Capture")
        rv = QVBoxLayout(rec_box)
        self._rec_btn = QPushButton("⏺  Record")
        self._rec_btn.setCheckable(True)
        self._rec_btn.toggled.connect(self._on_record_toggle)
        rv.addWidget(self._rec_btn)
        self._rec_status = QLabel("")
        self._rec_status.setWordWrap(True)
        rv.addWidget(self._rec_status)
        lv.addWidget(rec_box)

        root.addWidget(left)

        # ---- Right: pyqtgraph plots ----
        gl = pg.GraphicsLayoutWidget()
        root.addWidget(gl)

        # Row 0: spectrogram labels
        gl.addLabel("<b>Input Spectrogram</b>", row=0, col=0)
        gl.addLabel("<b>Output Spectrogram</b>", row=0, col=1)

        # Row 1: spectrogram images
        self._spec_in_img = pg.ImageItem(axisOrder="col-major")
        self._spec_out_img = pg.ImageItem(axisOrder="col-major")

        freq_axis_in = pg.AxisItem(orientation="left")
        freq_axis_out = pg.AxisItem(orientation="left")
        vb_in = gl.addViewBox(row=1, col=0)
        vb_in.addItem(self._spec_in_img)
        vb_in.setAspectLocked(False)
        vb_out = gl.addViewBox(row=1, col=1)
        vb_out.addItem(self._spec_out_img)
        vb_out.setAspectLocked(False)

        # Color bar (shared)
        cmap_name = "inferno"
        try:
            cmap = pg.colormap.get(cmap_name)
        except Exception:
            cmap = pg.colormap.get("grey")
        for img in (self._spec_in_img, self._spec_out_img):
            img.setColorMap(cmap)
            img.setLevels((-80, 0))

        # Row 2: ERLE time series
        self._erle_plot = gl.addPlot(row=2, col=0, colspan=2)
        self._erle_plot.setLabel("left", "ERLE (dB)")
        self._erle_plot.setLabel("bottom", f"frames  [{_DISPLAY_SECS}s window]")
        self._erle_plot.addLegend()
        self._erle_curve = self._erle_plot.plot(
            pen=pg.mkPen("y", width=1), name="ERLE"
        )
        self._erle_plot.setYRange(0, 40, padding=0.05)

        # Row 3: SNR-delta time series
        self._snr_plot = gl.addPlot(row=3, col=0, colspan=2)
        self._snr_plot.setLabel("left", "SNR Δ (dB)")
        self._snr_plot.setLabel("bottom", f"frames  [{_DISPLAY_SECS}s window]")
        self._snr_plot.addLegend()
        self._snr_curve = self._snr_plot.plot(
            pen=pg.mkPen("c", width=1), name="SNR delta"
        )

    # ------------------------------------------------------------------ #
    # Qt timer callbacks                                                   #
    # ------------------------------------------------------------------ #

    def _drain_queue(self) -> None:
        frames = []
        for _ in range(128):
            try:
                frames.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if not frames:
            return

        for f in frames:
            # Time-series buffers
            erle = f["erle"] if not math.isnan(f["erle"]) else 0.0
            self._erle_buf.append(erle)
            self._snr_delta_buf.append(f["snr_out"] - f["snr_in"])

            # Spectrogram columns
            for key, col_buf in (("in", self._spec_in_cols), ("out", self._spec_out_cols)):
                audio = f[key]
                n = min(len(audio), _FFT_SIZE)
                buf = np.zeros(_FFT_SIZE, dtype=np.float32)
                buf[:n] = audio[:n] * self._spec_win[:n]
                X_db = 20.0 * np.log10(np.abs(np.fft.rfft(buf)) + 1e-8)
                col_buf.append(X_db.astype(np.float32))

        # Update spectrogram images
        if self._spec_in_cols:
            self._spec_in_img.setImage(np.array(self._spec_in_cols))
            self._spec_out_img.setImage(np.array(self._spec_out_cols))

        # Update time-series curves
        self._erle_curve.setData(np.array(self._erle_buf))
        self._snr_curve.setData(np.array(self._snr_delta_buf))

        # Update status labels from most recent frame
        latest = frames[-1]
        erle_val = latest["erle"]
        delta = latest["snr_out"] - latest["snr_in"]

        if not math.isnan(erle_val):
            self._erle_label.setText(f"ERLE:  {erle_val:+.1f} dB")
        self._snr_label.setText(f"SNR Δ: {delta:+.1f} dB")

        if latest["dtd"]:
            self._dtd_label.setText("ON")
            self._dtd_label.setStyleSheet(
                "background:#c62828; color:white; padding:8px; border-radius:4px; font-weight:bold;"
            )
        else:
            self._dtd_label.setText("OFF")
            self._dtd_label.setStyleSheet(
                "background:#2e7d32; color:white; padding:8px; border-radius:4px; font-weight:bold;"
            )

    def _check_done(self) -> None:
        if time.perf_counter() - self._start >= self._duration:
            self._app.quit()

    # ------------------------------------------------------------------ #
    # Recording                                                            #
    # ------------------------------------------------------------------ #

    def _poll_latency(self) -> None:
        if self._rt_audio is None:
            return
        rtt = self._rt_audio.round_trip_ms()
        if rtt is None:
            return
        if self._last_rtt_ms is not None and abs(rtt - self._last_rtt_ms) < 1e-3:
            return
        self._last_rtt_ms = rtt
        self._lat_label.setText(f"RTT: {rtt:.1f} ms")
        one_way_samples = int(round((rtt * 0.5 / 1000.0) * self._sr))
        self._delay_spin.setValue(max(0, one_way_samples))
        self._lat_status.setText("Suggested delay updated from latest RTT.")

    def _call_engine(self, method_name: str, *args) -> None:
        if self._engine is None:
            return
        method = getattr(self._engine, method_name, None)
        if callable(method):
            method(*args)

    def _on_bypass_toggle(self, checked: bool) -> None:
        self._bypass_active = checked
        if checked:
            self._bypass_btn.setText("ECNR: OFF  (bypass)")
        else:
            self._bypass_btn.setText("ECNR: ON")
        if self._bypass_callback is not None:
            self._bypass_callback(checked)

    def _on_bf_toggle(self, checked: bool) -> None:
        self._call_engine("set_beamformer_enabled", checked)

    def _on_bf_angle_change(self, value: float) -> None:
        self._call_engine("set_beamformer_steering_angle_deg", value)

    def _on_aec_toggle(self, checked: bool) -> None:
        self._call_engine("set_aec_enabled", checked)

    def _on_aec_step_change(self, value: float) -> None:
        self._call_engine("set_aec_step_size", value)

    def _on_aec_dtd_change(self, value: float) -> None:
        self._call_engine("set_aec_double_talk_threshold_db", value)

    def _on_nr_toggle(self, checked: bool) -> None:
        self._call_engine("set_nr_enabled", checked)

    def _on_nr_aggr_change(self, value: float) -> None:
        self._call_engine("set_nr_aggressiveness_db", value)

    def _on_nr_alpha_change(self, value: float) -> None:
        self._call_engine("set_nr_noise_smooth_alpha", value)

    def _on_measure_latency(self) -> None:
        if self._rt_audio is None:
            self._lat_status.setText("Latency unavailable: RT audio stream not attached.")
            return
        self._last_rtt_ms = None
        self._lat_label.setText("RTT: measuring...")
        self._lat_status.setText("Click injected. Keep speaker loopback path active.")
        self._rt_audio.measure_latency()

    def _on_store_delay(self) -> None:
        cfg_path = getattr(self._config, "runtime_config_path", "")
        if not cfg_path:
            self._lat_status.setText("No runtime config path available.")
            return

        try:
            p = Path(cfg_path)
            with open(p, "r", encoding="utf-8") as f:
                j = json.load(f)

            if "reference" not in j or not isinstance(j["reference"], dict):
                j["reference"] = {}

            delay_samples = int(self._delay_spin.value())
            j["reference"]["delay_compensation_samples"] = delay_samples

            with open(p, "w", encoding="utf-8") as f:
                json.dump(j, f, indent=2)
                f.write("\n")

            self._config.reference.delay_compensation_samples = delay_samples
            self._lat_status.setText(
                f"Saved delay_compensation_samples={delay_samples} to {p.name}"
            )
            print(f"[viz] Saved reference.delay_compensation_samples={delay_samples} to {p}")
        except Exception as exc:
            self._lat_status.setText(f"Save failed: {exc}")
            print(f"[viz] Save delay failed: {exc}")

    def _on_record_toggle(self, checked: bool) -> None:
        self._recording = checked
        if checked:
            self._record_buf.clear()
            self._rec_btn.setText("⏹  Stop")
            self._rec_status.setText("Recording…")
        else:
            self._rec_btn.setText("⏺  Record")
            self._save_recording()

    def _save_recording(self) -> None:
        if not self._record_buf:
            self._rec_status.setText("Nothing recorded.")
            return
        try:
            import soundfile as sf
            data = np.concatenate(self._record_buf)
            sf.write(self._record_path, data, self._sr)
            secs = len(data) / self._sr
            msg = f"Saved {secs:.1f}s\n→ {self._record_path}"
            self._rec_status.setText(msg)
            print(f"[viz] {msg.replace(chr(10), ' ')}")
        except Exception as exc:
            self._rec_status.setText(f"Save failed:\n{exc}")
            print(f"[viz] Save failed: {exc}")
