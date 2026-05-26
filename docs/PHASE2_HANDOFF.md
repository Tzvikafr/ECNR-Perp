# Phase 2 Handoff Notes — ECNR Python → C/C++ (AM62x Cortex-A53)

**Version:** 1.0 | **Date:** May 2026 | **Status:** Active

This document records per-module time budgets, algorithmic mapping notes, and
configuration semantics needed to port the Python RT engine to C/C++ on AM62x.

---

## 1. Frame Budget Reference

| Parameter | Value |
|-----------|-------|
| Sample rate | 16 000 Hz |
| Frame size | 320 samples |
| Frame duration | 20 ms |
| Frame budget (80% rule) | 16 ms |
| Platform target | TI AM62x Cortex-A53 @ 1.4 GHz |

Run `python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --profile`
to get measured per-module timings on the current PC. Expect 10–50× slowdown on A53
vs. desktop PC — scale accordingly when sizing buffers and SIMD optimisations.

### 1.1 Measured PC Timings (Phase 1D validation, 2026-05-26)

Measured on Windows 11 desktop PC, 200 frames, `phase1_default.json` config
(BF enabled, AEC filter_length=128, NR agg=8 dB):

| Module | Mean µs | p99 µs | % of 20 ms budget |
|--------|---------|--------|-------------------|
| bf     | 2010.8  | 3276.6 | 10.1%             |
| aec    | 1877.4  | 3418.3 |  9.4%             |
| nr     |  205.0  |  322.9 |  1.0%             |
| TOTAL  | 4093.3  |        | 20.5%             |

Real-time factor: ~5× (gate: > 1.0×) — PASS

Note: These are NumPy/Python timings on PC. Expect 10–50× slowdown on A53 Cortex-A53
at 1.4 GHz. The BF and AEC modules are the dominant cost; both are prime candidates
for NEON SIMD optimisation in the C port.

---

## 2. Per-Module NumPy → C Mapping

### 2.1 Beamformer (`dsp/beamformer.py` → `src/beamformer.c`)

| Python | C equivalent |
|--------|-------------|
| `np.zeros((M, 64))` delay lines | `float delay_line[4][64]` |
| `_lagrange_coeffs(frac, 8)` — computed once at init | `float frac_delay_coeff[4][8]` — precomputed at `ecnr_init()` |
| Inner loop: `frac_coeffs[i] @ delay_lines[i, :8]` | `for j in 0..7: acc += coeff[j] * line[j]` |
| Delay shift: `delay_line[i, 1:] = delay_line[i, :-1]` | `memmove(&line[1], &line[0], 63*sizeof(float))` |

**Key constant:** `SPEED_OF_SOUND = 343.0 m/s`. Precompute delays at init; never recompute per frame.

**SIMD note:** The 8-tap FIR per mic per sample is the primary BF hotspot. Use NEON `vfmaq_f32` on A53 to process 4 taps in one instruction. With 2 mics × 8 taps = 16 MACs/sample, one NEON pass covers the BF inner loop.

---

### 2.2 AEC (`dsp/aec.py` → `src/aec.c`)

| Python | C equivalent |
|--------|-------------|
| `np.zeros(L)` filter weights `w` | `float w[1024]` — stack or static |
| `np.zeros(L)` reference history `x_hist` | `float x_hist[1024]` — newest-first shift |
| Per-sample: `x_hist[1:] = x_hist[:-1]` | `memmove(&x_hist[1], &x_hist[0], (L-1)*sizeof(float))` |
| `w @ x_hist` | CMSIS-DSP `arm_dot_prod_f32` or manual NEON loop |
| NLMS update: `w += (step/norm) * e * x_hist` | `arm_scale_f32` + `arm_add_f32` |

**DTD formula (power ratio):** `P_mic / P_ref > threshold_lin` where `threshold_lin = 10^(threshold_dB / 10)`. Compute per-frame (one mean over `frame_size` samples each), not per-sample.

**ERLE:** rolling mean over `erle_window_frames` (default 25). Use a circular float array + running sum for O(1) update.

**NLMS freeze:** when `dtd_active == true`, skip the weight update inner loop entirely — do not zero-out `w`.

**Filter length guidance:**
- 128 taps @ 16 kHz → covers 8 ms echo path (≈ 2.7 m)  
- 512 taps → covers 32 ms (≈ 11 m) — use for reverberant rooms
- C port default: 128 (matches `phase1_default.json`)

---

### 2.3 Traditional NR (`dsp/nr_traditional.py` → `src/nr_traditional.c`)

| Python | C equivalent |
|--------|-------------|
| `np.fft.rfft(x, n=Nf)` | CMSIS-DSP `arm_rfft_fast_f32` or TI DSPLIB `DSPF_sp_fftSPxSP` |
| `np.fft.irfft(Y, n=Nf)` | Corresponding inverse FFT |
| `noise_psd` IIR update | `for k: psd[k] = alpha*psd[k] + (1-alpha)*P[k]` |
| Wiener gain: `max(floor, 1 - lambda/(snr+1))` | Element-wise float array — NEON-friendly |
| OLA shift: `ola_buf[:hop] = ola_buf[hop:]` | `memcpy` then `memset` |

**Window:** Periodic Hann: `w[n] = 0.5 * (1 - cos(2π·n/N))`. Precompute at init as `float win[frame_size]`.

**FFT size:** `Nf = next_power_of_2(frame_size)`. For `frame_size=320` → `Nf=512`. For `frame_size=256` → `Nf=256`. Allocate FFT instance at init; do not allocate per frame.

**OLA invariant:** Two segments per frame call. Segment 1 uses `[prev_in[hop:], e[:hop]]`; segment 2 uses `e`. The `prev_in` buffer (size `frame_size`) must persist between calls.

**Noise gate:** Update PSD only when `mean(P) < 10 * mean(noise_psd)`. Use scalar comparison; no per-bin gating.

---

## 3. Configuration Schema — C Loader Notes

The JSON config is the single source of truth across MATLAB, Python, and C.
The C loader must enforce the same validation rules as `load_config()`:

| Field | C validation |
|-------|-------------|
| `sample_rate_hz` | Must be 16000 or 48000 |
| `mic_count` | Must be 1, 2, or 4 |
| `frame.length_samples` | 128–512; must be even |
| `aec.filter_length` | 64–1024 |
| `aec.step_size` | 0.001–1.0 |
| `nr.aggressiveness_db` | 0–24 |
| `mic_count == 1` | Force `beamformer.enabled = false` |

Recommended C JSON parser: **cJSON** (single header, MIT licence, no heap fragmentation if pool-allocated).

---

## 4. Reference Source Configuration

| `source_type` | Phase 1 Python | Phase 2 C |
|--------------|---------------|----------|
| `"file"` | `soundfile.read()` frame-by-frame | `fread()` from WAV after header parse |
| `"loopback"` | WASAPI loopback `InputStream` | ALSA loopback capture device |
| `"capture_channel"` | Not yet implemented | ALSA multi-channel capture, channel index |

For Phase 2 offline regression: keep `source_type = "file"` with `ref_wav` path.
For Phase 2 live demo: set `source_type = "loopback"` (ALSA hw:0,1 or similar).

---

## 5. Hot-Updateable vs Restart-Required Parameters

| Parameter | Safe to update live | Notes |
|-----------|--------------------|-|
| `aec.step_size` | Yes | Write new float, takes effect next frame |
| `aec.double_talk_threshold_db` | Yes | Recompute `threshold_lin = 10^(x/10)` |
| `nr.aggressiveness_db` | Yes | Recompute `lambda = 1 + (x/24)*1.5` |
| `nr.noise_smooth_alpha` | Yes | Scalar replace |
| `aec.filter_length` | **No** — requires full state reset | |
| `sampling_rate`, `frame_size`, `mic_count` | **No** — requires engine restart | |
| `mode` (Traditional ↔ Hybrid) | **No** — different module graph | |

---

## 6. Metrics Output Format

The Python `Metrics.export_csv()` produces the same column order as the MATLAB baseline.
The C port should write the same CSV columns for regression parity:

```
erle_db, erle_inst_db, erle_window_db, snr_in_db, snr_out_db,
dtd_active, frame_index,
beamformer_enabled, beamformer_algorithm,
aec_enabled, aec_algorithm,
nr_enabled, nr_algorithm
```

NaN values must be written as the string `NaN` (not `nan`, not empty) to match
the MATLAB baseline comparison logic in `regression.py`.

---

## 7. Regression Parity Targets (Python vs MATLAB)

From Sprint 6 validation:

| Metric | Target tolerance |
|--------|-----------------|
| ERLE (windowed mean) | ±2 dB vs MATLAB baseline |
| SNR-out (mean) | ±1.5 dB vs MATLAB baseline |
| Output WAV RMS | ±0.5 dB vs MATLAB output |

Run `python -m ecnr_python.regression` to verify before Phase 2 branch is created.

---

## 8. Known Differences Python vs MATLAB

| Aspect | MATLAB | Python | Impact |
|--------|--------|--------|--------|
| Float precision | `double` (64-bit) everywhere | `float64` for DSP, `float32` at I/O boundary | Negligible |
| Hann window | `hann(N, 'periodic')` | `0.5*(1 - cos(2π·n/N))` | Identical |
| NLMS loop order | Per-sample (matches Python) | Per-sample | Identical |
| noise_smooth_alpha default | 0.98 | 0.95 (config-overridden) | Config-driven |
| BF implementation | Equal weights only (no Lagrange) | Lagrange FIR + equal weights | Python is more accurate |

---

## 9. Phase 2 Acceptance Gate

Before Phase 2 C branch is declared MVP-ready:

- [ ] `python -m ecnr_python.regression` returns PASS on all Phase 1 scenarios
- [ ] `python -m ecnr_python.offline_runner ... --profile` shows total < 80% frame budget on PC
- [ ] C engine passes same WAV through same scenario; CSV compared vs Python CSV within tolerances
- [ ] `--stability-run --loops 90` completes with 0 xruns and `rt_factor > 1.0×`
- [ ] ALSA integration tested at target frame size on AM62x EVK
