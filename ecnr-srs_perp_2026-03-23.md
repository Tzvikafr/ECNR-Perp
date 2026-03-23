# Software Requirements Specification (SRS)
**ECNR Pipeline – Automotive & Consumer**

## 1. Scope

This SRS defines the software behavior, interfaces, data models, and module structure for a multi-phase **Echo Cancellation and Noise Reduction (ECNR)** pipeline deployed in:

- **Phase 1:** PC-based prototyping and tuning (MATLAB + optional Python).
- **Phase 2:** Embedded MVP on **TI AM62x** (Arm Cortex‑A53, Linux/ALSA).
- **Phase 3:** Optimized embedded implementation with offload to **C7x DSP/accelerator**.

The pipeline supports **1/2/4 microphones**, optional beamforming, **Traditional** and **Hybrid** algorithm modes (Linear AEC + DL NN postfilter), and I/O via WAV files or live audio (PC audio device / RME Fireface).

---

## 2. System Overview

### 2.1 High-Level Data Flow

1. **Reference (far-end) audio in** (playout stream).
2. **Microphone array input** (1/2/4 channels).
3. Optional **Beamformer** → single enhanced mic stream (for 2/4 mics).
4. **AEC module (linear adaptive, e.g., NLMS)** to cancel acoustic echo.
5. **Noise/Echo Suppression module:**
   - Traditional: spectral subtraction / classical postfilter.
   - Hybrid: deep-learning based denoiser/echo suppressor.
6. **Output** audio stream for near-end transmission or logging.
7. **Metrics and logging** (ERLE, PESQ, SNR, convergence).

---

## 3. External Interfaces

### 3.1 User Interfaces

#### 3.1.1 Phase 1 MATLAB GUI

- Implemented using **base MATLAB + Signal Processing Toolbox only**.
- Panels:
  - **Configuration panel:** mic count (1/2/4), sample rate, frame size, beamformer on/off, mode (Traditional/Hybrid).
  - **AEC/NR parameters:** step size, filter length, DTD thresholds, NR aggressiveness.
  - **DL (Hybrid) parameters:** model selection, operating point (aggressiveness curve).
  - **I/O control:** input mode (WAV / live), device selection (PC / RME Fireface), start/stop.
  - **Metrics & plots:** ERLE over time, waveforms, spectrograms, VAD/DTD indicators.

#### 3.1.2 Python GUI/Control (optional)

- If used, presents a **mirrored control surface** for Hybrid mode (selection of model, parameters).
- Communicates with core engine via:
  - Shared config files (JSON/YAML) or
  - IPC (sockets/ZeroMQ) with a simple control protocol (key–value messages).

### 3.2 Audio I/O Interfaces

#### 3.2.1 Phase 1 – PC

- **Offline:**
  - Read/write multi-channel WAV via MATLAB functions (`audioread`, `audiowrite`).
- **Real-time:**
  - Input/output via:
    - Base MATLAB-supported audio I/O mechanisms (e.g., Java bindings or OS-level libraries, not Audio Toolbox objects).
    - RME Fireface through OS audio drivers (ASIO/WASAPI/CoreAudio) accessed via MATLAB-supported APIs or small native helper where needed.
  - Real-time device support shall be validated by an early feasibility spike; offline WAV processing remains the required fallback path if device-specific integration is incomplete.
- Frame-based processing:
  - Typical frame size: 10–32 ms (e.g., 160–512 samples @16 kHz).
  - The external engine contract operates on a base `frame_size` cadence. Any overlap/add required by frequency-domain NR or Hybrid modules is maintained internally by those modules rather than by the external I/O contract.

#### 3.2.2 Phase 2/3 – AM62x

- **Linux ALSA** or TI audio framework for capture/playback (PCM).
- Configurable:
  - Sample rate: 16 kHz (minimum), 48 kHz (preferred).
  - Channel count: up to 4 mic channels + 1 reference channel.
- DSP offload path in Phase 3:
  - A53 side: ALSA I/O, buffer management, control.
  - DSP side: frame-based ECNR processing via IPC/RPMsg or TI audio framework.

---

## 4. Functional Requirements (Software Behavior)

### 4.1 Configuration Management

- **Config file format:** JSON or YAML.
- **Top-level schema (conceptual):**

```json
{
  "schema_version": "1.0",
  "sampling_rate": 16000,
  "frame_size": 256,
  "mic_count": 4,
  "reference": {
    "source_type": "loopback",
    "device_id": "default",
    "channel_index": 0,
    "delay_compensation_samples": 0
  },
  "beamformer": {
    "enabled": true,
    "type": "DAS",
    "geometry": "linear",
    "spacing_m": 0.05,
    "steering_angle_deg": 0
  },
  "mode": "traditional",        // or "hybrid"
  "aec": {
    "filter_length": 512,
    "step_size": 0.1,
    "regularization": 1e-3,
    "double_talk_threshold": -20
  },
  "nr": {
    "type": "spectral_subtraction",
    "aggressiveness_db": 12
  },
  "dl": {
    "model_id": "ecnr_crn_v1",
    "operating_point": "medium"
  }
}
```

- GUI shall:
  - Load and apply configuration on demand.
  - Save current configuration snapshot.
- Configuration loaders shall validate schema version and reject or migrate incompatible profiles explicitly.

Reference-source requirements:

- The configuration shall explicitly define how the far-end reference signal is acquired for AEC.
- Supported source types may include file-based reference, loopback/playout tap, or separate capture channel depending on platform.
- Implementations shall document any additional routing and synchronization assumptions needed to keep the reference aligned with microphone input.

### 4.1.1 Runtime Reconfiguration Policy

- The implementation shall distinguish between **hot-updateable** parameters and **restart-required** parameters.
- Hot-updateable parameters include tuning values that do not invalidate internal buffer topology, such as NLMS step size, DTD threshold, NR aggressiveness, and Hybrid operating point.
- Restart-required parameters include topology-changing values such as sample rate, frame size, microphone count, adaptive filter length, and model binary/path unless a specific platform implementation proves safe in-place replacement.
- Algorithm mode is hot-switchable only when both required processing backends are already initialized and the switch does not change frame topology, routing, or model-loading requirements.
- Runtime APIs and GUI behavior shall enforce the same reconfiguration policy on every platform.

### 4.2 Core Processing API (Logical)

Define a **language-neutral** processing API; each platform must provide a concrete implementation:

```c
typedef struct {
    float *mic_in;        // [N_mic][frame_size] interleaved or separate
    float *ref_in;        // [frame_size]
    float *out;           // [frame_size]
} ecnr_frame_t;

typedef struct {
    // Parsed configuration values (see JSON schema)
} ecnr_config_t;

typedef void* ecnr_handle_t;

ecnr_handle_t ecnr_create(const ecnr_config_t *cfg);
int ecnr_process_frame(ecnr_handle_t h, const ecnr_frame_t *in, ecnr_frame_t *out);
int ecnr_set_param(ecnr_handle_t h, const char *key, float value);
int ecnr_get_metrics(ecnr_handle_t h, /* metrics struct */);
void ecnr_destroy(ecnr_handle_t h);
```

- **MATLAB wrapper** calls into equivalent MATLAB functions/classes (or compiled MEX in later phase).
- **Python wrapper** calls C via ctypes/cffi or Python-native implementation for prototypes.
- `ecnr_set_param` shall be used only for parameters classified as hot-updateable by Section 4.1.1.

### 4.3 Beamforming Module

- Inputs: multi-channel mic frames X_i[n] for i = 1..N.
- Output: single-channel beamformed signal x_b[n].
- Supported methods:
  - Delay-and-sum (time-domain or frequency-domain).
- MVP expectation:
  - Delay-and-sum is the required first implementation.
  - More advanced beamforming such as MVDR-like processing is an optional extension after DAS parity and latency targets are met.
- Requirements:
  - Latency introduced by beamformer must be **bounded and documented**.
  - Steering angle and geometry configured via config/GUI.

### 4.4 AEC Module (Linear Adaptive)

- Algorithm: **NLMS or variant**.
- Inputs: reference frame, mic (or beamformed) frame.
- Output: echo-cancelled microphone frame.
- Features:
  - Configurable **filter length** and **step size**.
  - Double-talk detection (DTD) to freeze or slow adaptation during near-end speech.
  - Optional non-linear postprocessing (clipping/comfort noise) in Traditional mode.

### 4.5 Noise/Echo Suppression Module

#### 4.5.1 Traditional Mode

- Operates on AEC output.
- Algorithm: spectral subtraction / Wiener-like noise suppression in STFT domain.
- Inputs: frame(s) of time-domain AEC output; noise estimate (tracked from non-speech segments).
- Outputs: enhanced speech frame.
- Parameters:
  - Aggressiveness (attenuation dB).
  - Min/max gain floor.
  - Smoothing factors for noise estimate.

#### 4.5.2 Hybrid Mode (DL Postfilter)

- Operates on AEC output (residual signal).
- Model type: CRN/UNet/RNN-like time–frequency model (design to be refined; requirement at SRS level is **DL-based spectral or waveform denoiser/echo suppressor**).
- Inference:
  - Python prototype: PyTorch/TF.
  - Embedded: exported model (e.g., TFLM, ONNX + TI tools) running on DSP or A53.
- Model I/O:
  - Input: framed features (e.g., STFT magnitude, log-mel, complex STFT).
  - Output: gain mask or enhanced waveform.
- Configurable:
  - `model_id` (select between model binaries).
  - `operating_point` (mapping to internal thresholding/temperature, etc.).

### 4.6 Metrics Computation

Required metrics (offline and/or online where applicable):

- **ERLE**: 10 log10(E[y^2]/E[e^2]) during far-end single talk.
- **Convergence time**: number of frames until ERLE > 20 dB after start or echo-path change.
- **PESQ (P.862)**: batch/offline evaluation only.
- **Segmental SNR improvement**: difference between input and output segmental SNR.
- **Double-talk transparency index**: ratio of near-end power between clean and processed during DT windows.

Metrics shall be:

- Logged per scenario into CSV/JSON files.
- Exposed to GUI for trend visualization.

---

## 5. Detailed Module Decomposition

### 5.1 MATLAB Layer (Phase 1)

#### 5.1.1 MATLAB ECNR Engine

- Implemented as MATLAB functions/classes using:
  - **Base MATLAB** and **Signal Processing Toolbox** only (e.g., `fft`, `ifft`, filter design, STFT utilities).
- Public API (MATLAB side, conceptual):

```matlab
cfg = ecnr_load_config('config.json');
h  = ecnr_init(cfg);
[out_frame, h] = ecnr_process_frame(h, mic_frame, ref_frame);
metrics = ecnr_get_metrics(h);
```

#### 5.1.2 MATLAB GUI

- Built with `uifigure`, `uicontrol` / App Designer.
- Responsibilities:
  - Bind GUI controls to `cfg` fields.
  - Provide **start/stop** hooks that call I/O and core engine.
  - Plotting using `plot`, `spectrogram`, etc.
  - Implement real-time loop respecting frame timing (e.g., using timers or audio callback wrapper).

### 5.2 Python / DL Layer (Phase 1, Hybrid)

- Python package layout:

```text
ecnr_py/
  __init__.py
  config.py
  dl_model.py
  hybrid_wrapper.py
  io_utils.py
```

- `dl_model.py`:
  - Loads model from disk.
  - Provides `process_frame(features) -> mask/enhanced`.
- `hybrid_wrapper.py`:
  - Takes AEC output from MATLAB/C.
  - Applies STFT/feature extraction.
  - Calls DL model.
  - Produces enhanced waveform back to MATLAB/C.

Integration options:

- **Option A (required baseline):** Offline WAV processing where MATLAB dumps intermediate AEC output; Python post-processes and returns result.
- **Option B (optional extension):** Real-time IPC where MATLAB sends frames to Python over a socket.

Recommended sequencing:

- Complete Option A first to validate Hybrid quality and model/export assumptions without coupling success to real-time IPC.
- Add Option B only after the offline Hybrid path is stable and the control/runtime contract is frozen.

---

## 6. Embedded Software Behavior (Phase 2 & 3)

### 6.1 Phase 2 – A53 Linux Process

- Implementation language: **C/C++**.
- Process responsibilities:
  - Initialize ALSA capture/playback.
  - Read configuration file.
  - Create ECNR engine via `ecnr_create`.
  - Run real-time processing loop:
    - Read frames from ALSA.
    - Package into `ecnr_frame_t`.
    - Call `ecnr_process_frame`.
    - Write output to ALSA.
  - Periodically emit metrics (e.g., via log or shared memory).

- Scope requirement:
  - Traditional mode is the required Phase 2 MVP.
  - Hybrid mode may be added after Traditional parity, CPU budget, and latency targets are demonstrated on AM62x.
  - Single-core execution on A53 is preferred for MVP simplicity, but the formal acceptance criterion is meeting the latency and CPU budget rather than forcing one exact core-allocation policy.

- Error handling:
  - If buffer underrun/overrun: log, attempt recovery, maintain audio continuity.
  - If configuration invalid: abort startup with descriptive error.

### 6.2 Phase 3 – DSP Offload

- Architecture:
  - **A53 side**:
    - Audio I/O (ALSA).
    - Configuration and control.
    - Packaging frames to DSP via IPC (e.g., RPMsg).
  - **C7x DSP side**:
    - Receives `ecnr_frame_t` buffers.
    - Runs ECNR core.
    - Returns processed frames.

- Additional requirements:
  - Formal interface description for IPC messages (e.g., `ECNR_INIT`, `ECNR_PROCESS`, `ECNR_SET_PARAM`).
  - Latency budget must include IPC overhead; algorithm must be tuned to respect end-to-end target (<15 ms).
  - Offload boundaries shall be profiling-driven; Hybrid inference shall remain on A53 or be staged out if DSP deployment does not fit measured memory or timing budgets.

---

## 7. Performance Requirements

- **Real-time capability:**
  - System shall process each frame within **80%** of its frame duration on the target platform (e.g., 8 ms compute for 10 ms frame) to leave safety margin.
- **Complexity constraints:**
  - Provide estimated MIPS for AEC + NR (Traditional) and for Hybrid at typical settings, to check feasibility on A53 and C7x.
- **Memory:**
  - Document heap/stack usage and model size for each configuration.

---

## 8. Design Constraints

- Phase 1 MATLAB: **no Audio Toolbox**; only base MATLAB + Signal Processing Toolbox.
- Target OS in Phase 2: Linux distribution supported by TI AM62x SDK.
- Deep-learning models must be exportable to a format supported by TI tools or lightweight inference engines.

---

## 9. Verification & Validation

- **Unit tests**:
  - AEC unit test with synthetic echo path and known ERLE behavior.
  - NR unit test with stationary noise and known SNR improvement.
- **Integration tests**:
  - End-to-end tests on standard echo/noise scenarios (automotive and room).
- **Regression tests**:
  - Automated comparison of metrics across builds (Traditional vs Hybrid, Phase 1 vs Phase 2).
- **Embedded validation**:
  - Latency and CPU utilization measurement on AM62x for key configurations.
