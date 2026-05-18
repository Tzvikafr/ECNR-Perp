# Low-Level Design (LLD)
## ECNR Pipeline – Complete Module Specifications

**Version:** 2.0 | **Date:** March 23, 2026 | **Status:** Complete

---

## 1. Overview & Purpose

This Low-Level Design (LLD) document provides the detailed specifications, data structures, algorithms, and implementation logic for all 11 core modules of the ECNR pipeline. Each module is designed to be:

- **Independently testable** with well-defined unit test boundaries
- **Language-agnostic** (MATLAB prototype, C/C++ production, Python DL wrapper)
- **Real-time safe** (no dynamic allocation in hot paths)
- **Agent-Ready** (unambiguous logic flows suitable for AI code generation)

Unless otherwise stated, numeric values, file names, transport choices, and runtime backends in this document are reference defaults for planning and code generation. Final platform selections shall remain consistent with the PRD/SRS phase gates, hot-update policy, and target profiling results.

---

## Module Directory

| # | Module Name | Responsibility | Phase 1 | Phase 2/3 |
|---|---|---|---|---|
| 1 | Configuration Manager | Parse/validate config, hot-param updates | MATLAB | C/cJSON |
| 2 | Frame Buffer Manager | Ring buffers, overlap-add buffering | MATLAB | POSIX mmap |
| 3 | Beamformer (DAS) | Multi-channel → single channel | MATLAB | C + optional VCOP |
| 4 | Linear AEC (NLMS) | Echo cancellation + DTD | MATLAB | C + optional MMA |
| 5 | Traditional NR | Spectral subtraction in STFT domain | MATLAB | C + DSPLIB FFT |
| 6 | Hybrid DL NR | DL-based mask application | Python PyTorch | TFLM / ONNX |
| 7 | Metrics Engine | ERLE, SNR, DTD, Convergence | MATLAB | C lock-free queue |
| 8 | ALSA I/O Manager | Audio capture/playback | — | C / libasound |
| 9 | IPC & DSP Offload | RPMsg, DDR buffers | — | C (A53 + C7x) |
| 10 | MATLAB Phase 1 Engine | App Designer GUI, timer loop | MATLAB | — |
| 11 | C/C++ File Structure | Portable core, test harness | — | C/C++ |

---

## LLD-1: Configuration Manager

### 1.1 Responsibility
Parse versioned JSON/YAML configuration into typed C struct (`ecnr_config_t`) or MATLAB struct. Validate all fields against documented ranges at startup. Provide thread-safe parameter update API only for parameters classified as hot-updateable by the SRS.

### 1.2 Data Structures

```c
// Beamformer Configuration
typedef enum { BF_DISABLED = 0, BF_DAS = 1 } bf_type_t;
typedef enum { GEO_LINEAR = 0, GEO_CIRCULAR = 1 } array_geo_t;

typedef struct {
    bf_type_t    type;
    array_geo_t  geometry;
    float        spacing_m;           // 0.01–0.20 m
    float        steering_angle_deg;  // -90 to +90 degrees
} bf_config_t;

// AEC Configuration
typedef struct {
    int   filter_length;            // 64–1024 taps
    float step_size;                // 0.001–1.0 (learning rate μ)
    float regularization;           // 1e-6–1e-2 (epsilon for stability)
    float double_talk_threshold_db; // -40 to 0 dB
} aec_config_t;

// Noise Reduction Configuration
typedef enum { NR_SPECTRAL_SUB = 0, NR_WIENER = 1 } nr_type_t;

typedef struct {
    nr_type_t type;
    float     aggressiveness_db;   // 0–24 dB (oversubtraction factor β)
    float     spectral_floor_db;   // -60 to -10 dB (min gain floor)
    float     noise_smooth_alpha;  // 0.85–0.99 (IIR noise tracking)
} nr_config_t;

// Deep Learning Configuration (Hybrid)
typedef struct {
    char  model_id[64];            // e.g., "ecnr_crn_v1"
    char  model_path[256];         // path to .tflite / .onnx / .pt
    float operating_point;         // 0.0 (mild) – 1.0 (aggressive)
} dl_config_t;

typedef struct {
  char  source_type[32];         // "file", "loopback", "capture_channel"
  char  device_id[128];          // Logical device or route identifier
  int   channel_index;           // Channel index when applicable
  int   delay_compensation_samples;
} ref_config_t;

// Top-Level Configuration (Master)
typedef enum { MODE_TRADITIONAL = 0, MODE_HYBRID = 1 } ecnr_mode_t;

typedef struct {
    int          sampling_rate;    // 16000 or 48000 Hz
    int          frame_size;       // 128–512 samples per frame
    int          mic_count;        // 1, 2, or 4 channels
    ecnr_mode_t  mode;             // Algorithm mode selector
  ref_config_t reference;        // Far-end reference acquisition
    bf_config_t  beamformer;       // Beamformer settings
    aec_config_t aec;              // AEC filter parameters
    nr_config_t  nr;               // Noise reduction parameters
    dl_config_t  dl;               // DL model selection (Hybrid)
} ecnr_config_t;
```

### 1.3 Initialization Logic (C Implementation)

```
FUNCTION config_load(filepath: string) → ecnr_config_t:
  1. IF filepath does not exist:
       IF running in prototype/development mode:
           LOG WARNING "Config file not found; using documented defaults"
           RETURN default config
       ELSE:
           LOG ERROR "Required config file not found"
           ABORT startup

  2. OPEN and parse JSON file using cJSON library
  3. FOR each field in ecnr_config_t:
       a. IF field missing from JSON:
            Use documented default value
       b. EXTRACT value from JSON
       c. IF value outside valid range:
            CLAMP to range
            LOG WARNING "Parameter X clamped from Y to Z"

  4. VALIDATE cross-field constraints:
       IF mic_count == 1:
           FORCE beamformer.type = BF_DISABLED
       IF mode == MODE_HYBRID:
           ASSERT file_exists(dl.model_path)
           IF NOT: LOG ERROR and ABORT

  5. RETURN validated config
```

### 1.4 Hot-Parameter Update API

```c
// Thread-safe parameter update for safe hot-updateable parameters only
int ecnr_set_param(ecnr_handle_t h, const char *key, float value);

// Valid hot-updateable keys (immediate effect):
// "aec.step_size"
// "aec.double_talk_threshold_db"
// "nr.aggressiveness_db"
// "nr.spectral_floor_db"
// "dl.operating_point"
// "mode" (only if both processing backends are initialized and frame topology, routing, and model-loading requirements are unchanged)

// Invalid hot-updateable (require ecnr_destroy + ecnr_create):
// "sampling_rate", "frame_size", "mic_count", "aec.filter_length"
```

### 1.5 Validation Rules

| Field | Valid Range | Default | Notes |
|---|---|---|---|
| `sampling_rate` | 16000, 48000 | 16000 | Only two options |
| `frame_size` | Platform-supported processing cadence | 256 | External engine cadence; overlap for STFT modules is internal |
| `mic_count` | 1, 2, 4 | 1 | Must match hardware |
| `aec.filter_length` | 64–1024 | 512 | Covers 20–120 cm @ 16 kHz |
| `aec.step_size` | 0.001–1.0 | 0.1 | Convergence speed |
| `nr.aggressiveness_db` | 0–24 | 12 | Linear scale (not dB internally) |
| `dl.operating_point` | 0.0–1.0 | 0.5 | Maps to model threshold |

---

## LLD-2: Frame Buffer Manager

### 2.1 Responsibility
Accepts variable-size raw PCM from audio driver. Delivers fixed-size `frame_size` buffers to the Core DSP Engine at the external engine cadence. Any overlap/add required by frequency-domain Traditional NR or Hybrid modules is maintained inside those modules rather than by this manager.

### 2.2 State Structure

```c
typedef struct {
    float  *ring_buf;           // Circular buffer: 4 × frame_size × mic_count
    int     write_idx;          // Next write position (samples)
    int     read_idx;           // Next read position
    int     sample_rate;        // From config
    int     frame_size;         // From config
    int     mic_count;          // From config
    int     xrun_count;         // Underrun/overrun counter
    pthread_mutex_t lock;       // Protect concurrent access (optional)
} fbm_state_t;
```

### 2.3 Push Samples Logic (From Audio Driver)

```
FUNCTION fbm_push_samples(state: fbm_state_t, 
                          new_samples[N_new]:  float,
                          mic_ch: int):
  // Called from ALSA interrupt context (Phase 2)
  // Must complete in < 1 ms

  1. Compute circular write index:
       write_pos = (state.write_idx + i) % (4 × frame_size)

  2. FOR i = 0 to N_new - 1:
       state.ring_buf[write_pos + mic_ch × 4 × frame_size] = new_samples[i]

  3. state.write_idx += N_new

  4. WHILE (state.write_idx - state.read_idx) >= frame_size:
       TRIGGER processing thread semaphore
      state.read_idx += frame_size
```

### 2.4 Pop Frame Logic (To DSP Engine)

```
FUNCTION fbm_pop_frame(state: fbm_state_t, 
                       out: float[frame_size]):
  // Called by real-time processing loop
  // Produces the next fixed-size engine frame

  1. FOR n = 0 to frame_size - 1:
    out[n] = ring_buf[state.read_idx + n]
```

---

## LLD-3: Beamformer Module (Delay-and-Sum)

### 3.1 Responsibility
Spatially filter N-channel microphone array to produce single enhanced output using delay-and-sum (DAS) beamforming based on pre-computed sample delays and fractional-delay FIR filters.

### 3.2 State Structure

```c
typedef struct {
    int   mic_count;
    int   frame_size;
    int   delay_samples[4];        // Integer sample delays [0..3]
    float frac_delay_coeff[4][8];  // Lagrange FIR coeff (order 7)
    float delay_line[4][64];       // Per-mic delay state (≤ 4 ms)
    float w[4];                    // Summation weights (uniform = 1/N)
    float latency_ms;              // Documented latency contribution
} bf_state_t;
```

### 3.3 Delay Computation at Init (Per-Channel)

```
FUNCTION bf_compute_delays(cfg: bf_config_t, 
                           sample_rate: int):

  speed_of_sound = 343 m/s  // @20°C

  FOR each microphone i = 0..mic_count-1:

    1. Compute geometric delay:
         IF geometry == GEO_LINEAR:
             distance_m = i × cfg.spacing_m × cos(cfg.steering_angle_deg × π/180)
         ELSE IF geometry == GEO_CIRCULAR:
             angle_rad = 2π × i / mic_count + cfg.steering_angle_deg
             distance_m = cfg.spacing_m/2 × cos(angle_rad)

    2. Convert to sample delay:
         delay_samples_exact = distance_m × sample_rate / speed_of_sound

    3. Split into integer + fractional:
         delay_samples[i] = floor(delay_samples_exact)
         frac_part = delay_samples_exact - delay_samples[i]

    4. Compute Lagrange FIR coefficients for frac_part:
         FOR tap j = 0..7:
             L_j(frac_part) = ∏_{m=0,m≠j}^{7} (frac_part - m) / (j - m)
             frac_delay_coeff[i][j] = L_j(frac_part)

    5. Initialize delay line:
         FOR tap n = 0..63:
             delay_line[i][n] = 0.0

    6. Compute weight (uniform for DAS):
         w[i] = 1.0 / mic_count

    7. Log latency:
         latency_ms = max(delay_samples[i]) / sample_rate × 1000
```

### 3.4 Per-Frame Processing

```
FUNCTION bf_process(state: bf_state_t, 
                    mic_in[mic_count][frame_size]: float,
                    out[frame_size]: float):

  FOR each output sample n = 0 to frame_size - 1:

    acc = 0.0

    FOR each microphone i = 0 to mic_count - 1:

      1. Insert new sample into delay line:
           delay_line[i][0] = mic_in[i][n]

      2. Apply fractional delay FIR:
           delayed = ∑_{j=0}^{7} frac_delay_coeff[i][j] × delay_line[i][j]

      3. Shift delay line (circular):
           FOR tap j = 63 down to 1:
               delay_line[i][j] = delay_line[i][j-1]

      4. Accumulate weighted delayed sample:
           acc += w[i] × delayed

    out[n] = acc
```

**Computational cost:** O(8 × mic_count × frame_size) MACs per frame. At 4 mics, 256 samples: ~8k MACs = negligible.

---

## LLD-4: Linear AEC Module (NLMS + DTD)

### 4.1 Responsibility
Adaptive echo canceller using Normalized Least Mean Squares (NLMS) with integrated Double-Talk Detector (DTD). Suppresses acoustic echo by estimating and subtracting the echo path impulse response.

### 4.2 State Structure

```c
typedef struct {
    // Adaptive filter state
    float  *w;                   // Weights: [filter_length]
    float  *x_hist;              // Reference history: [2 × filter_length]
    int     hist_idx;            // Circular insertion index
    int     filter_length;       // Configurable (64–1024 taps)

    // NLMS parameters
    float   step_size;           // μ (learning rate, 0.001–1.0)
    float   regularization;      // ε (1e-6–1e-2, prevents div-by-0)

    // Double-talk detection
    float   power_mic_smooth;    // IIR-smoothed mic power
    float   power_ref_smooth;    // IIR-smoothed reference power
    float   dtd_threshold;       // Threshold (linear, not dB)
    int     dtd_active;          // 1 = double-talk detected
    float   dtd_alpha;           // IIR constant (0.9)

    // Comfort noise (Traditional mode)
    float   cnoise_level;        // Estimated background noise floor
} aec_state_t;
```

### 4.3 Initialization

```
FUNCTION aec_create(cfg: aec_config_t) → aec_state_t*:

  1. Allocate state on heap
  2. Allocate w[filter_length], x_hist[2 × filter_length]
  3. memset(w, 0); memset(x_hist, 0)
  4. hist_idx = 0
  5. Set all params from cfg:
       step_size = cfg.step_size
       regularization = cfg.regularization
       filter_length = cfg.filter_length
       dtd_threshold = 10^(cfg.double_talk_threshold_db / 10)  // Convert from dB
       dtd_alpha = 0.9
  6. RETURN state pointer
```

### 4.4 Per-Frame Processing (Core NLMS Algorithm)

```
FUNCTION aec_process(state: aec_state_t,
                     ref_in[L]: float,
                     mic_in[L]: float,
                     residual_out[L]: float):

  // ──── Step 1: Insert reference into circular history ────
  FOR n = 0 to L - 1:
    x_hist[(hist_idx + n) % filter_length] = ref_in[n]

  // ──── Step 2: Double-Talk Detection (frame-level) ────
  P_mic = dtd_alpha × power_mic_smooth + 
          (1 - dtd_alpha) × (1/L) × ∑_{n=0}^{L-1} mic_in[n]²

  P_ref = dtd_alpha × power_ref_smooth + 
          (1 - dtd_alpha) × (1/L) × ∑_{n=0}^{L-1} ref_in[n]²

  power_mic_smooth = P_mic
  power_ref_smooth = P_ref

  IF (P_ref > 1e-6) AND (P_mic / P_ref > dtd_threshold):
      dtd_active = 1  // Far-end + near-end (freeze adaptation)
  ELSE:
      dtd_active = 0  // Far-end only (allow adaptation)

  // ──── Step 3: Per-Sample Filtering & NLMS Update ────
  FOR n = 0 to L - 1:

    // Construct reference vector (most recent filter_length samples)
    FOR k = 0 to filter_length - 1:
      x_vec[k] = x_hist[(hist_idx + n - k) % filter_length]

    // Echo estimate: y_hat = w^T × x_vec
    y_hat = ∑_{k=0}^{filter_length-1} w[k] × x_vec[k]

    // Error signal (residual)
    e[n] = mic_in[n] - y_hat
    residual_out[n] = e[n]

    // NLMS weight update (only if no double-talk)
    IF dtd_active == 0:
      P_x = ∑_{k=0}^{filter_length-1} x_vec[k]² + regularization
      mu_norm = step_size / (P_x + ε)
      FOR k = 0 to filter_length - 1:
        w[k] += mu_norm × e[n] × x_vec[k]

  // ──── Step 4: Advance history index ────
  hist_idx = (hist_idx + L) % filter_length
```

**Computational cost:** O(2 × filter_length × frame_size) MACs per frame.
Example: filter_length=512, frame_size=256 @ 16 kHz: ~262k MACs per 16 ms = **~16.4 MMAC/s**.

### 4.5 ERLE Computation (Metrics Observer - Non-Blocking)

```
FUNCTION aec_compute_erle(mic_in[L]: float,
                          residual_out[L]: float,
                          dtd_active: int,
                          P_ref: float) → float:

  // Only measure ERLE during far-end single-talk (not double-talk)
  IF dtd_active == 1 OR P_ref < 1e-6:
      RETURN previous_erle_smooth  // Skip this frame

  P_mic = (1/L) × ∑_{n=0}^{L-1} mic_in[n]²
  P_residual = (1/L) × ∑_{n=0}^{L-1} residual_out[n]²

  ERLE_inst = 10 × log10(P_mic / (P_residual + 1e-12))

  // Smooth with IIR:
  ERLE_smooth = 0.95 × ERLE_smooth_prev + 0.05 × ERLE_inst

  RETURN ERLE_smooth
```

---

## LLD-5: Traditional Noise Reduction Module

### 5.1 Responsibility
Suppress residual noise in the STFT domain using spectral subtraction or Wiener filtering with IIR noise floor tracking.

### 5.2 State Structure

```c
typedef struct {
    int     fft_size;              // 2 × frame_size (zero-padded)
    int     frame_size;
    int     n_bins;                // fft_size / 2 + 1
    float  *window;                // Hann window [frame_size]
    float  *noise_est;             // Noise power estimate [n_bins]
    float  *prev_frame;            // OLA tail buffer [frame_size/2]
    float   alpha;                 // Noise tracking (0.85–0.99)
    float   oversubtraction;       // β aggressiveness (1.0–2.0 linear)
    float   spectral_floor;        // Min gain (e.g., 0.05 = -26 dB)
    float   vad_threshold_db;      // Frame energy threshold for VAD
} nr_state_t;
```

### 5.3 Per-Frame Processing

```
FUNCTION nr_process(state: nr_state_t,
                    residual_in[frame_size]: float,
                    enhanced_out[frame_size]: float):

  // ──── Step 1: Windowing & Zero-Pad & FFT ────
  FOR n = 0 to frame_size - 1:
    windowed[n] = residual_in[n] × window[n]
  FOR n = frame_size to fft_size - 1:
    windowed[n] = 0.0

  X[0..n_bins-1] = real_fft(windowed, fft_size)

  // ──── Step 2: Magnitude Spectrum ────
  FOR k = 0 to n_bins - 1:
    |X[k]| = sqrt(Re(X[k])² + Im(X[k])²)

  // ──── Step 3: Voice Activity Detection ────
  E_frame = (1/frame_size) × ∑_{n=0}^{frame_size-1} residual_in[n]²
  E_thresh = 10^(vad_threshold_db / 10)

  IF E_frame < E_thresh:  // No speech → update noise estimate
    FOR k = 0 to n_bins - 1:
      noise_est[k] = alpha × noise_est[k] + 
                     (1 - alpha) × |X[k]|²

  // ──── Step 4: Gain Mask Computation (Wiener Approx) ────
  FOR k = 0 to n_bins - 1:
    SNR_k = |X[k]|² / (noise_est[k] + 1e-12)
    G[k] = max(spectral_floor, 1 - oversubtraction / (SNR_k + 1))

    // Alternative pure spectral subtraction:
    // G[k] = max(spectral_floor, (|X[k]| - sqrt(oversubtraction × noise_est[k])) / |X[k]|)

  // ──── Step 5: Apply Gain & Enforce Hermitian Symmetry ────
  FOR k = 0 to n_bins - 1:
    Y[k] = G[k] × X[k]

  FOR k = 1 to n_bins - 2:
    Y[fft_size - k] = conj(Y[k])  // Ensure real IFFT output

  // ──── Step 6: IFFT & Overlap-Add ────
  y_time[0..fft_size-1] = real_ifft(Y, fft_size)

  FOR n = 0 to frame_size/2 - 1:
    enhanced_out[n] = prev_frame[n] + y_time[n]

  FOR n = frame_size/2 to frame_size - 1:
    enhanced_out[n] = y_time[n]

  // Store new tail for next frame:
  FOR n = 0 to frame_size/2 - 1:
    prev_frame[n] = y_time[frame_size/2 + n]
```

**Key parameters:**
- `alpha=0.99`: slow noise tracking (good for non-stationary)
- `oversubtraction=1.5`: moderate suppression, avoid musical noise
- `spectral_floor=0.1`: residual noise ~-20 dB, prevents over-suppression

---

## LLD-6: Hybrid DL Noise Reduction Module

### 6.1 Responsibility
Run a deep neural network (CRN/UNet/RNN-like) as a post-AEC suppressor using a model contract that can evolve during Phase 1 research. The first required integration is offline and quality-focused; embedded deployment is conditional on export, memory, and timing feasibility.

### 6.2 State Structure

```c
typedef struct {
    void        *model_ctx;           // Opaque model handle (TFLM/ONNX)
    int          fft_size;
    int          n_bins;              // fft_size / 2 + 1
    float       *window;              // Hann window
    float       *feature_buf;         // Input tensor [n_bins × 2]
    float       *mask_buf;            // Output tensor [n_bins × 2] (CRM)
    float       *prev_frame;          // OLA tail
    float        operating_point;     // 0.0–1.0
    float        model_norm_factor;   // Normalization for features
} dl_nr_state_t;
```

### 6.3 Per-Frame Processing

```
FUNCTION dl_nr_process(state: dl_nr_state_t,
                       residual_in[frame_size]: float,
                       enhanced_out[frame_size]: float):

  // ──── Step 1: STFT Feature Extraction ────
  windowed = residual_in × window
  X[0..n_bins-1] = real_fft(zero_pad(windowed, fft_size))

  norm_factor = max(|X[k]|) + ε  // Prevent NaN

  FOR k = 0 to n_bins - 1:
    feature_buf[k×2 + 0] = Re(X[k]) / norm_factor  // Real part
    feature_buf[k×2 + 1] = Im(X[k]) / norm_factor  // Imag part

  // Optional: Log-magnitude features
  // FOR k = 0 to n_bins - 1:
  //   mag[k] = sqrt(feature_buf[k×2]² + feature_buf[k×2+1]²)
  //   feature_buf[k] = 10 × log10(mag[k]² + 1e-12)

  // ──── Step 2: DL Inference ────
  model_infer(state.model_ctx, feature_buf, mask_buf)
  // Returns [Re_mask[k], Im_mask[k]] for each k

  // ──── Step 3: Complex Ratio Mask Application ────
  FOR k = 0 to n_bins - 1:
    Mr = mask_buf[k × 2 + 0]      // CRM real component
    Mi = mask_buf[k × 2 + 1]      // CRM imag component

    // Complex multiplication: Y = M × X
    Re_X = Re(X[k])
    Im_X = Im(X[k])

    Re_Y = Mr × Re_X - Mi × Im_X
    Im_Y = Mr × Im_X + Mi × Re_X

    Y[k] = Re_Y + j × Im_Y

  // ──── Step 4: Enforce Hermitian Symmetry ────
  FOR k = 1 to n_bins - 2:
    Y[fft_size - k] = conj(Y[k])

  // ──── Step 5: IFFT & Overlap-Add (same as Traditional NR) ────
  y_time = real_ifft(Y, fft_size)

  FOR n = 0 to frame_size/2 - 1:
    enhanced_out[n] = prev_frame[n] + y_time[n]

  FOR n = frame_size/2 to frame_size - 1:
    enhanced_out[n] = y_time[n]

  FOR n = 0 to frame_size/2 - 1:
    prev_frame[n] = y_time[frame_size/2 + n]
```

### 6.4 Model I/O Specification (Baseline Reference Profile)

| Property | Specification |
|---|---|
| Input tensor shape | Example baseline: `[1, n_bins, 2]` (batch=1, frequency bins, real+imag) |
| Input data type | `float32` |
| Input normalization | Example baseline: linear normalization by max magnitude |
| Output tensor shape | Example baseline: `[1, n_bins, 2]` (complex ratio mask) |
| Output data type | `float32` |
| Model format (Phase 1) | Research format selected by ML workflow |
| Model format (Phase 2) | Optional embedded export format selected after feasibility review |
| Model format (Phase 3) | Optional DSP-capable export format selected after feasibility review |
| Model size (Phase 3) | Must fit measured target memory budget if offloaded |
| Max inference time (Phase 3) | Must fit measured end-to-end latency budget if offloaded |

---

## LLD-7: Metrics Engine

### 7.1 Responsibility
Compute ERLE, SNR, convergence time, and DTD transparency in a non-blocking manner. Log metrics to CSV and expose latest metrics to GUI via atomic writes.

### 7.2 Metrics Record Structure

```c
typedef struct {
    uint64_t frame_index;
    float    erle_db;              // Echo Return Loss Enhancement
    float    snr_input_db;         // Segmental SNR (pre-NR)
    float    snr_output_db;        // Segmental SNR (post-NR)
    float    dt_transparency_db;   // Speech attenuation during DT
    int      dtd_active;           // 1 = double-talk this frame
    float    convergence_frames;   // Frames to reach 20 dB ERLE
} metrics_record_t;
```

### 7.3 ERLE Computation Logic

```
FUNCTION metrics_compute_erle(mic_in[L]: float,
                              residual_out[L]: float,
                              dtd_active: int) → float:

  IF dtd_active == 1:
      RETURN previous_erle  // Skip during double-talk

  P_mic = mean(mic_in²)
  P_residual = mean(residual_out²)

  ERLE_inst = 10 × log10(P_mic / (P_residual + ε))
  ERLE_smooth = 0.95 × ERLE_smooth_prev + 0.05 × ERLE_inst

  RETURN ERLE_smooth
```

### 7.4 Convergence Tracking

```
FUNCTION metrics_track_convergence(ERLE_smooth: float,
                                   current_frame: uint64_t) → float:

  // Detect echo-path change (sudden ERLE drop)
  IF |ERLE_smooth - ERLE_prev| > 5 dB:
      convergence_start_frame = current_frame
      LOG "Echo path change detected; starting convergence timer"

  // Measure convergence time
  IF ERLE_smooth >= 20.0 dB AND convergence_start_frame set:
      convergence_frames = current_frame - convergence_start_frame
      LOG_RECORD "Convergence achieved in %d frames", convergence_frames
      RESET convergence_start_frame
      RETURN convergence_frames

  RETURN 0
```

### 7.5 Lock-Free Logging Queue

```
FUNCTION metrics_queue_push(record: metrics_record_t):
  // Called from real-time processing loop (non-blocking)

  IF lock_free_queue full:
      LOG WARNING "Metrics queue overflow"
      RETURN

  lock_free_ring_buffer_push(&metrics_queue, record)
  SIGNAL background_logger_thread

FUNCTION metrics_background_logger_thread():
  // Runs at low priority, continuous loop

  WHILE running:
    IF lock_free_ring_buffer_pop(&metrics_queue, &record):
        CSV_APPEND {
          record.frame_index,
          record.erle_db,
          record.snr_input_db,
          record.snr_output_db,
          record.dt_transparency_db,
          record.dtd_active,
          record.convergence_frames
        }

        ATOMIC_STORE(&metrics_latest, record)  // For GUI

        IF frames_since_flush > 1000:  // Every ~16 s @ 16 kHz
            FLUSH CSV file
            frames_since_flush = 0
    ELSE:
        USLEEP(5000)  // 5 ms sleep
```

---

## LLD-8: ALSA I/O Manager (Phase 2 & 3)

### 8.1 Responsibility
Manage Linux ALSA audio capture (microphone array + reference) and playback (enhanced output). Handle period-based blocking I/O, supported sample formats, explicit reference routing, and graceful xrun recovery.

Reference-routing policy:

- `reference.source_type = file` uses a synchronized offline reference stream.
- `reference.source_type = loopback` uses a validated playout tap or loopback route.
- `reference.source_type = capture_channel` uses an explicitly configured channel from a capture path distinct from microphone speech channels unless hardware documentation defines the multiplexing.
- Implementations shall apply `delay_compensation_samples` before handing the reference frame to AEC.

### 8.2 State Structure

```c
typedef struct {
    snd_pcm_t  *pcm_capture;       // Capture handle (mic array)
    snd_pcm_t  *pcm_playback;      // Playback handle (output)
    int         sampling_rate;     // 16000 or 48000 Hz
    int         frame_size;        // Processing frame in samples
    int         period_size;       // ALSA period = frame_size
    int         buffer_size;       // ALSA buffer = 4 × period_size
    int         mic_count;         // 1, 2, or 4 channels
    float      *capture_buf;       // Interleaved [mic_count × period_size]
    float      *playback_buf;      // [period_size]
    int         xrun_count;        // Monitoring counter
    uint64_t    frames_captured;   // Monotonic frame counter
} alsa_io_t;
```

### 8.3 Initialization Sequence

```
FUNCTION alsa_init(cfg: ecnr_config_t) → alsa_io_t*:

  1. OPEN capture device:
       snd_pcm_open(&pcm_capture, "hw:0,0", 
                     SND_PCM_STREAM_CAPTURE, 0)

  2. OPEN playback device:
       snd_pcm_open(&pcm_playback, "hw:0,1",
                     SND_PCM_STREAM_PLAYBACK, 0)

  3. FOR each PCM handle (capture, playback):
      snd_pcm_hw_params_set_format(→ supported format such as FLOAT_LE, S16_LE, or S32_LE)
       snd_pcm_hw_params_set_rate(→ cfg.sampling_rate, 0)
       snd_pcm_hw_params_set_channels(→ mic_count for capture, 1 for playback)
       snd_pcm_hw_params_set_period_size(→ cfg.frame_size, 0)
       snd_pcm_hw_params_set_buffer_size(→ 4 × cfg.frame_size)
       snd_pcm_hw_params(apply params)

  4. snd_pcm_prepare(pcm_capture)
     snd_pcm_prepare(pcm_playback)

  5. Pre-fill playback buffer with silence (2 periods):
       FOR i = 0 to 2 × frame_size - 1:
           playback_buf[i] = 0.0
       snd_pcm_writei(pcm_playback, playback_buf, 2 × period_size)

  6. Start capture:
       snd_pcm_start(pcm_capture)

  7. RETURN state pointer
```

### 8.4 Real-Time Processing Loop

```
FUNCTION processing_loop(alsa_io: alsa_io_t,
                         ecnr_handle: ecnr_handle_t):

  // Apply scheduler and CPU-affinity tuning if profiling shows it is required.
  // Exact policy is platform- and deployment-specific.

  WHILE running:

    // ──── CAPTURE ────
    ret = snd_pcm_readi(pcm_capture, capture_buf, period_size)

    IF ret == -EPIPE:  // Overrun
        LOG WARNING "Capture overrun"
        snd_pcm_prepare(pcm_capture)
        xrun_count++
        CONTINUE

    IF ret < 0:
        LOG ERROR "snd_pcm_readi failed: %s", snd_strerror(ret)
        BREAK

    // ──── DEINTERLEAVE ────
    FOR ch = 0 to mic_count - 1:
        FOR n = 0 to period_size - 1:
            mic_frame[ch][n] = capture_buf[n × mic_count + ch]

    // ──── REFERENCE ────
    ref_frame = read_reference_frame_from_configured_source()
    // Reference must come from an explicit playout tap, loopback, or separate capture path.
    // It must not alias microphone channel 0 unless the hardware contract explicitly defines that routing.

    // ──── ECNR PROCESSING ────
    ecnr_frame_t in = {
        .mic_in = mic_frame,
        .ref_in = ref_frame
    }
    ecnr_frame_t out = {
        .out = playback_buf
    }
    ecnr_process_frame(ecnr_handle, &in, &out)

    // ──── PLAYBACK ────
    ret = snd_pcm_writei(pcm_playback, playback_buf, period_size)

    IF ret == -EPIPE:  // Underrun
        LOG WARNING "Playback underrun"
        snd_pcm_recover(pcm_playback, ret, 0)
        xrun_count++

    IF ret < 0 AND ret != -EPIPE:
        LOG ERROR "snd_pcm_writei failed: %s", snd_strerror(ret)
        BREAK

    // ──── METRICS (non-blocking) ────
    metrics_queue_push(latest_record)
```

---

## LLD-9: IPC & DSP Offload Manager (Phase 3)

### 9.1 Responsibility
Manage bidirectional A53↔C7x communication via TI-supported IPC over shared memory. RPMsg over carveout DDR is the baseline reference approach, but exact transport and buffer sizing may vary by platform integration results.

### 9.2 Shared Memory Layout

```
Carveout DDR (allocated via device tree, ~16 KB):
┌──────────────────────────────────────────────────────────┐
│ Ping Buffer A: ecnr_frame_t                  │ 4 KB      │
│   mic_in[4][256], ref_in[256], out[256]                  │
├──────────────────────────────────────────────────────────┤
│ Pong Buffer B: ecnr_frame_t                  │ 4 KB      │
├──────────────────────────────────────────────────────────┤
│ IPC Control Block:                           │ 256 B    │
│   uint32_t a53_write_slot;  // 0=PingA, 1=PongB         │
│   uint32_t dsp_read_slot;                                │
│   uint32_t msg_id;  // Command type                      │
│   uint32_t status;  // Result (OK/ERROR)                 │
│   uint32_t reserved[60];                                 │
├──────────────────────────────────────────────────────────┤
│ Config Buffer: ecnr_config_t                 │ 2 KB      │
│   (Written once at ECNR_MSG_INIT)                        │
├──────────────────────────────────────────────────────────┤
│ Metrics Buffer: metrics_record_t             │ 128 B    │
│   (Updated by DSP after each frame)                      │
└──────────────────────────────────────────────────────────┘
```

### 9.3 IPC Message Protocol

```c
typedef enum {
    ECNR_MSG_INIT       = 0x01,
    ECNR_MSG_PROCESS    = 0x02,
    ECNR_MSG_DONE       = 0x03,
    ECNR_MSG_SET_PARAM  = 0x04,
    ECNR_MSG_SHUTDOWN   = 0x05
} ecnr_ipc_msg_t;

typedef struct {
    uint32_t msg_id;             // Command type
    uint32_t frame_slot;         // 0 or 1 (ping-pong)
    char     param_key[32];      // For SET_PARAM
    float    param_value;        // For SET_PARAM
} ecnr_ipc_hdr_t;
```

### 9.4 A53 Host State Machine

```
States: IDLE → INITIALIZING → RUNNING → DRAINING → STOPPED

IDLE:
  On start: serialize config to config_buf
            send ECNR_MSG_INIT via RPMsg
            → INITIALIZING

INITIALIZING:
  Wait for ECNR_MSG_DONE response from DSP
  → RUNNING

RUNNING (per-frame loop):
  1. slot = (frame_index mod 2)
  2. Copy mic_frame + ref_frame into DDR Ping/Pong buffer
  3. FLUSH D-cache for that buffer region
  4. Send ECNR_MSG_PROCESS(slot) via RPMsg (8-byte message)
  5. WAIT on semaphore (set by RPMsg IRQ handler on ECNR_MSG_DONE)
  6. INVALIDATE D-cache for output region
  7. Copy enhanced_out from DDR → playback_buf
  8. Advance to next frame

On ECNR_SET_PARAM request:
  Send ECNR_MSG_SET_PARAM(key, value)
  DSP applies atomically on next frame boundary (no ACK needed)
```

### 9.5 C7x DSP Firmware State Machine

```
Idle loop:
  Wait on RPMsg mailbox interrupt

On ECNR_MSG_INIT:
  1. Deserialize ecnr_config_t from config_buf
  2. ecnr_create(cfg)  // Allocate in L2 SRAM (fast)
  3. Reply ECNR_MSG_DONE via RPMsg

On ECNR_MSG_PROCESS(slot):
  1. INVALIDATE L1/L2 cache for input DDR region
  2. Load ecnr_frame_t from DDR slot
  3. ecnr_process_frame(handle, in, out)
  4. FLUSH D-cache for output region
  5. Update metrics_buf (atomic stores)
  6. Reply ECNR_MSG_DONE(slot) via RPMsg

On ECNR_MSG_SET_PARAM(key, value):
  1. ecnr_set_param(handle, key, value)  // Atomic
  2. No reply (takes effect next ECNR_MSG_PROCESS)

On ECNR_MSG_SHUTDOWN:
  1. ecnr_destroy(handle)
  2. Free L2 SRAM
  3. Reply ECNR_MSG_DONE
  4. Exit main loop
```

---

## LLD-10: MATLAB Phase 1 Engine

### 10.1 Class/Function Directory

```
ecnr_matlab/
├── ecnr_load_config.m          % Parse JSON → MATLAB struct
├── ecnr_init.m                 % Create all module states
├── ecnr_process_frame.m        % Main dispatcher
├── ecnr_get_metrics.m          % Export metrics struct
├── ecnr_set_param.m            % Hot parameter update
├── ecnr_destroy.m              % Cleanup
│
├── beamformer/
│   ├── bf_init.m               % Compute delays, DAS state
│   └── bf_process.m            % Per-frame DAS processing
│
├── aec/
│   ├── aec_init.m              % Init weights, history
│   ├── aec_process.m           % NLMS + DTD per frame
│   └── dtd_compute.m           % Double-talk detection
│
├── nr/
│   ├── nr_trad_init.m          % Init noise_est, FFT state
│   ├── nr_trad_process.m       % Spectral sub per frame
│   ├── nr_hybrid_init.m        % Load DL model, init offline bridge/runtime
│   └── nr_hybrid_process.m     % Feature extract → offline bridge or optional live IPC
│
├── metrics/
│   ├── metrics_init.m          % Initialize tracking structs
│   ├── metrics_update.m        % Compute ERLE, SNR, DTD
│   └── metrics_save_csv.m      % Write results to disk
│
└── io/
    ├── io_wav_open.m           % audioread wrapper
    ├── io_wav_write.m          % audiowrite wrapper
    ├── io_live_init.m          % Validated live audio adapter / native helper
    └── io_live_callback.m      % Frame timer callback
```

### 10.2 Real-Time Loop Design (MATLAB)

```matlab
function start_realtime_processing(state)
  % Create a MATLAB-compatible real-time loop.
  % Timer-based scheduling is a baseline approach and may be replaced by
  % another validated callback/helper mechanism if device integration requires it.
    t = timer('ExecutionMode', 'fixedRate', ...
              'Period', state.cfg.frame_size / state.cfg.sampling_rate, ...
              'TimerFcn', @(~,~) process_one_frame(state));

    start(t);
    state.timer_handle = t;
end

function process_one_frame(state)
    % ──── Read frame from audio input ────
    [mic_frame, ref_frame] = io_live_read(state.io, ...
                                          state.cfg.frame_size);
    if isempty(mic_frame), return; end

    % ──── Process through ECNR engine ────
    [out_frame, state.ecnr] = ecnr_process_frame(state.ecnr, ...
                                                   mic_frame, ...
                                                   ref_frame);

    % ──── Playback ────
    io_live_write(state.io, out_frame);

    % ──── Update GUI (rate-limited) ────
    state.frame_count = state.frame_count + 1;
    if mod(state.frame_count, 10) == 0  % Every 160 ms @ 16 kHz
        metrics = ecnr_get_metrics(state.ecnr);
        update_gui_plots(state.gui_handle, metrics);
    end
end
```

### 10.3 GUI Panel Layout (App Designer)

```
┌─────────────────────────────────────────────────────────────────┐
│                 ECNR Tuning Tool (App Designer)                 │
├──────────────────────┬──────────────────────────────────────────┤
│  CONFIGURATION       │  VISUALIZATION                           │
│  Mic Count:          │  ┌────────────────────────────────────┐  │
│  [1][2][4]           │  │  Input Waveform / Output Waveform  │  │
│                      │  └────────────────────────────────────┘  │
│  Mode:               │  ┌────────────────────────────────────┐  │
│  [Trad][Hybrid]      │  │  ERLE over Time (dB)               │  │
│                      │  └────────────────────────────────────┘  │
│  Beamformer:         │  ┌──────────────┐ ┌────────────────┐    │
│  [ON][OFF]           │  │ Spectrogram  │ │ Spectrogram    │    │
│                      │  │ (Input)      │ │ (Output)       │    │
│  Sample Rate:        │  └──────────────┘ └────────────────┘    │
│  [16k][48k]          │  ┌────────────────────────────────────┐  │
│                      │  │ VAD / DTD Indicator (Timeline)     │  │
│  Frame Size:         │  └────────────────────────────────────┘  │
│  [128][256][512]     │                                          │
├──────────────────────┤──────────────────────────────────────────┤
│  AEC PARAMS          │  METRICS TABLE                           │
│  Step Size: [0.1]    │  ERLE: 42.3 dB    Offline PESQ: 3.8 MOS │
│  Filter Len: [512]   │  SNR Δ: +7.2 dB   DT Trans: 1.1 dB      │
│  DTD Thresh: [-20dB] │  Conv. Time: 0.65 s  Xruns: 0           │
├──────────────────────┤                                          │
│  NR PARAMS           │                                          │
│  Aggressiveness:     │  [Metrics updated every 160 ms]          │
│  [12 dB] ▬▬▬▬▬▬     │                                          │
│  Floor: [-30 dB]     │                                          │
├──────────────────────┤──────────────────────────────────────────┤
│  DL PARAMS (Hybrid)  │  CONTROL BUTTONS                         │
│  Model: [crn_v1 ▼]   │  [START]  [STOP]  [SAVE CONFIG]         │
│  OpPoint: [medium▼]  │                                          │
│  Load Model: [...]   │  [Export Metrics] [Clear Plots]          │
└──────────────────────┴──────────────────────────────────────────┘
```

---

## LLD-11: C/C++ File Structure & Build

### 11.1 Source Tree Layout

```
ecnr_c/
├── include/
│   ├── ecnr_api.h                   % Public API
│   ├── ecnr_config.h                % ecnr_config_t & substruct defs
│   ├── ecnr_frame.h                 % ecnr_frame_t, metrics_record_t
│   └── ecnr_internal.h              % Private state aggregator
│
├── src/
│   ├── ecnr_core.c                  % ecnr_create/destroy, dispatch
│   ├── config_parser.c              % JSON parsing (cJSON)
│   ├── beamformer.c                 % bf_init, bf_process
│   ├── aec_nlms.c                   % aec_init, aec_process, ERLE
│   ├── nr_traditional.c             % nr_init, nr_process
│   ├── nr_hybrid.c                  % dl_init, dl_process
│   ├── model_infer_tflm.c           % TFLM inference backend
│   ├── model_infer_onnx.c           % ONNX Runtime backend
│   ├── metrics_engine.c             % ERLE, SNR, DTD computation
│   ├── metrics_logger.c             % Lock-free queue + CSV writer
│   └── frame_buffer.c               % Ring buffers + OLA
│
├── platform/
│   ├── alsa_io.c                    % ALSA capture/playback (Phase 2)
│   ├── ipc_host.c                   % RPMsg A53 side (Phase 3)
│   ├── ipc_dsp.c                    % RPMsg DSP side (Phase 3)
│   └── common.h                     % Platform abstractions
│
├── tests/
│   ├── test_aec_erle.c              % Synthetic echo, verify ≥40 dB ERLE
│   ├── test_nr_snr.c                % Stationary noise, verify ≥5 dB SNR
│   ├── test_config.c                % JSON parse + range clamp tests
│   ├── test_e2e_wav.c               % End-to-end WAV file processing
│   └── CMakeLists.txt               % Test build rules
│
├── CMakeLists.txt                   % Master build configuration
├── README.md                        % Build instructions
└── toolchain-c7x.cmake              % TI Code Gen Tools config
```

### 11.2 CMake Build Configuration (Partial)

```cmake
cmake_minimum_required(VERSION 3.16)
project(ECNR)

# ─── Detect platform ───
if(TI_C7X_TOOLCHAIN)
    message(STATUS "Building for TI C7x DSP")
    include(${CMAKE_CURRENT_SOURCE_DIR}/toolchain-c7x.cmake)
else()
    message(STATUS "Building for ARM A53")
    set(CMAKE_C_COMPILER arm-linux-gnueabihf-gcc)
    set(CMAKE_C_FLAGS "-O2 -mfpu=neon -Wall -Wextra")
endif()

# ─── Core ECNR library ───
add_library(ecnr_core STATIC
    src/ecnr_core.c
    src/config_parser.c
    src/beamformer.c
    src/aec_nlms.c
    src/nr_traditional.c
    src/nr_hybrid.c
    src/metrics_engine.c
    src/frame_buffer.c
)

target_include_directories(ecnr_core PUBLIC include)
target_link_libraries(ecnr_core PRIVATE m cJSON)

# ─── DL inference backends ───
if(NOT TI_C7X_TOOLCHAIN)
    add_library(dl_infer_onnx OBJECT src/model_infer_onnx.c)
    target_link_libraries(ecnr_core PRIVATE onnxruntime)
endif()

if(TI_C7X_TOOLCHAIN)
    add_library(dl_infer_tflm OBJECT src/model_infer_tflm.c)
    target_link_libraries(ecnr_core PRIVATE tflm)
endif()

# ─── Platform-specific targets ───
if(NOT TI_C7X_TOOLCHAIN)
    add_executable(ecnr_a53_daemon
        platform/alsa_io.c
        platform/ipc_host.c
        src/ecnr_core.c
        # ... other sources
    )
    target_link_libraries(ecnr_a53_daemon PRIVATE asound ecnr_core)
else()
    add_executable(ecnr_c7x_fw.out
        platform/ipc_dsp.c
        src/ecnr_core.c
        # ... other sources (C7x optimized)
    )
    target_link_libraries(ecnr_c7x_fw.out PRIVATE ecnr_core)
endif()

# ─── Unit tests ───
enable_testing()
add_executable(test_aec_erle tests/test_aec_erle.c)
target_link_libraries(test_aec_erle PRIVATE ecnr_core)
add_test(NAME AEC_ERLE COMMAND test_aec_erle)

add_executable(test_nr_snr tests/test_nr_snr.c)
target_link_libraries(test_nr_snr PRIVATE ecnr_core)
add_test(NAME NR_SNR COMMAND test_nr_snr)
```

### 11.3 Unit Test Example (AEC ERLE)

```c
// tests/test_aec_erle.c
// Verify AEC achieves ≥40 dB ERLE on synthetic echo path

#include <stdlib.h>
#include <math.h>
#include "ecnr_api.h"

#define SAMPLE_RATE 16000
#define FRAME_SIZE 256
#define TEST_FRAMES 100

int test_aec_erle() {
    ecnr_config_t cfg = {
        .sampling_rate = SAMPLE_RATE,
        .frame_size = FRAME_SIZE,
        .mic_count = 1,
        .aec.filter_length = 512,
        .aec.step_size = 0.1,
        .aec.regularization = 0.001,
        .aec.double_talk_threshold_db = -20
    };

    ecnr_handle_t handle = ecnr_create(&cfg);

    // Generate synthetic echo path: h(n) = 0.8 * δ(n-50) + 0.3 * δ(n-100)
    float h[512] = {0};
    h[50] = 0.8;
    h[100] = 0.3;

    // Pseudorandom reference signal
    float ref_in[FRAME_SIZE];
    for (int i = 0; i < FRAME_SIZE; i++)
        ref_in[i] = 0.5 * sin(2 * M_PI * 1000 * i / SAMPLE_RATE);  // 1 kHz tone

    float erle_final = 0.0;

    for (int frame = 0; frame < TEST_FRAMES; frame++) {
        // Generate echo: mic_in = ref_in convolved with h + noise
        float mic_in[FRAME_SIZE] = {0};
        for (int n = 0; n < FRAME_SIZE; n++) {
            for (int k = 0; k < 512; k++) {
                if (n - k >= 0)
                    mic_in[n] += ref_in[n - k] * h[k];
            }
        }

        // Add small noise
        for (int n = 0; n < FRAME_SIZE; n++)
            mic_in[n] += 0.01 * (rand() / (float)RAND_MAX - 0.5);

        // Process frame
        ecnr_frame_t in = { .mic_in = mic_in, .ref_in = ref_in };
        ecnr_frame_t out = { .out = malloc(FRAME_SIZE * sizeof(float)) };
        ecnr_process_frame(handle, &in, &out);

        // Compute frame ERLE
        float p_mic = 0, p_residual = 0;
        for (int n = 0; n < FRAME_SIZE; n++) {
            p_mic += mic_in[n] * mic_in[n];
            p_residual += out.out[n] * out.out[n];
        }
        float erle = 10 * log10(p_mic / (p_residual + 1e-12));
        if (frame == TEST_FRAMES - 1)
            erle_final = erle;

        free(out.out);
    }

    ecnr_destroy(handle);

    // Assert ERLE ≥ 40 dB
    printf("Final ERLE: %.1f dB\n", erle_final);
    return (erle_final >= 40.0) ? 0 : 1;  // PASS / FAIL
}
```

---

## Conclusion

This LLD provides the complete implementation blueprint for all 11 ECNR modules across all phases. Every module is:

- **Independently testable** (unit test examples provided)
- **Agent-Ready** (unambiguous pseudocode logic flows)
- **Language-agnostic** (MATLAB, C, Python implementations possible)
- **Real-time safe** (no dynamic allocation in hot paths)
- **Portable** (identical core logic across phases)

Implementation teams can now proceed with confidence to translate these specifications into production code.
