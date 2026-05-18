# ECNR PC Real-Time Demo — Python Sprint Plan

**Version:** 1.0 | **Date:** 2026-05-14 | **Status:** Active

---

## Context

Phase 1 delivers offline WAV processing in MATLAB. This plan adds a **PC real-time (RT) demo phase** in Python before the embedded Phase 2 work begins on AM62x.

**Decision:** Python + `sounddevice` chosen over C/C++ for sprint velocity. C/C++ is the Phase 2 production target. The Python implementation becomes the behavioral reference and regression oracle for the Phase 2 C port.

**RT audio note:** `sounddevice` runs its callback in a native C thread (PortAudio/WASAPI). Python DSP runs inside that callback per frame. At a 16 ms frame budget (256 samples @ 16 kHz), NumPy arithmetic completes in ~0.5–2 ms — well inside budget on PC.

**Stack:** Python + NumPy (DSP) · `sounddevice` (RT audio via PortAudio/WASAPI) · PyTorch/ONNX (Hybrid DL)

**Rule:** every sprint ships something audible or measurable. No sprint ends with internal-only work.

---

## Architecture Decisions Carried Forward

| Decision | Impact on this phase |
|---|---|
| AD-02 | DAS beamformer first; MVDR staged |
| AD-03 | Hot-updateable vs restart-required params enforced in Python config |
| AD-04 | Mode switch Traditional ↔ Hybrid only when topology unchanged |
| AD-05 | Offline WAV remains the regression baseline; RT is additive |
| AD-06 | Reference source explicitly configured (`loopback` or `file`) |
| AD-07 | Frame cadence is external; overlap-add is internal to NR modules |
| AD-12 | Offline PESQ is a validation metric, not a live dependency |

---

## Project Structure

Mirrors LLD-11 naming so the Phase 2 C port is a straight module-by-module translation.

```
ecnr_python/
├── config/
│   └── ecnr_config.py        # Config dataclass (ecnr_config_t equivalent, LLD-1)
├── dsp/
│   ├── beamformer.py         # DAS — LLD-3
│   ├── aec.py                # NLMS + DTD — LLD-4
│   ├── nr_traditional.py     # Spectral subtraction — LLD-5
│   └── nr_hybrid.py          # DL mask (CRM) — LLD-6
├── io/
│   ├── rt_audio.py           # sounddevice duplex callback wrapper
│   └── reference.py          # Reference source abstraction (loopback / file)
├── metrics/
│   └── metrics.py            # ERLE, SNR, DTD — LLD-7
├── gui/
│   └── rt_viz.py             # Live spectrogram + metrics plots
├── engine.py                 # ecnr_process_frame dispatcher
├── scenarios/                # Reuse existing Phase 1 JSON configs
└── rt_demo.py                # Entry point / CLI
```

---

## Sprint 0 — RT Foundation & Passthrough

**Goal:** Live audio in and out, latency measured, project scaffolded.

| # | Task | Detail |
|---|---|---|
| 0.1 | Project scaffold | Create folder structure above |
| 0.2 | `ecnr_config.py` | Dataclass from LLD-1 field list; JSON loader reusing Phase 1 scenario files |
| 0.3 | `rt_audio.py` skeleton | `sounddevice` duplex stream, fixed `frame_size`, callback stub |
| 0.4 | Passthrough | mic frame → speaker frame, no DSP |
| 0.5 | Latency measurement | Play click through speaker, capture via mic, measure round-trip |
| 0.6 | Xrun counter | Log overrun/underrun events to console |

**Done when:**
- 60-second passthrough runs with 0 xruns
- Round-trip latency documented — target < 50 ms at `frame_size=256`, 16 kHz
- Config loads from existing `phase1_offline_wav.json` without error

---

## Sprint 1 — Traditional NR in Real Time

**Goal:** Audible noise reduction live; first DSP module ported and regression-validated.

No reference signal needed — NR is mic-input only.

| # | Task | Detail |
|---|---|---|
| 1.1 | `nr_traditional.py` | Translate LLD-5 pseudocode to NumPy: Hann window, zero-pad FFT, Wiener gain mask, overlap-add |
| 1.2 | Wire into callback | mic frame → NR → speaker frame |
| 1.3 | Console metrics | SNR-input / SNR-output printed every 10 frames (~160 ms) |
| 1.4 | Offline regression | Run same WAV through Python NR and MATLAB NR; compare output within ±0.5 dB RMS |

**Done when:**
- Stationary noise audibly reduced in live listen test
- Python NR output matches MATLAB offline output on Phase 1 regression WAV within ±0.5 dB RMS
- No xruns over 5-minute run

---

## Sprint 2 — AEC + Reference Routing in Real Time

**Goal:** Live echo cancellation; ERLE visible on screen; reference source abstracted.

| # | Task | Detail |
|---|---|---|
| 2.1 | `aec.py` | Translate LLD-4: NLMS adaptive filter, circular reference history, DTD |
| 2.2 | `reference.py` | Two backends: (a) synchronized file playback via `sounddevice.play()` + loopback capture, (b) WASAPI loopback as second capture stream. Swappable via config `reference.source_type` |
| 2.3 | AEC → NR chain | AEC residual feeds NR input |
| 2.4 | Console ERLE | Rolling 1-second ERLE printed live |
| 2.5 | Offline regression | ERLE in Python RT vs MATLAB offline baseline on same WAV — target within ±2 dB |

**Done when:**
- Speaking while far-end plays: echo visibly reduced in ERLE display
- NLMS converges within ~2 s on stationary echo path
- ERLE within ±2 dB of MATLAB Phase 1 baseline
- Reference source selectable via config field without code change

---

## Sprint 3 — Beamformer + Full Traditional Pipeline

**Goal:** Full BF → AEC → NR chain; config-driven stage enable/disable.

| # | Task | Detail |
|---|---|---|
| 3.1 | `beamformer.py` | Translate LLD-3: geometric delay computation, Lagrange FIR fractional delay, DAS accumulation |
| 3.2 | Multi-mic capture | `sounddevice` multi-channel input; deinterleave channels in callback |
| 3.3 | Config-driven enable | `beamformer.type`, `aec.enabled`, `nr.enabled` flags — each stage skips cleanly when disabled |
| 3.4 | Single-mic fallback | BF stage bypassed when `mic_count=1` (AD-02) |
| 3.5 | Full pipeline regression | End-to-end RT: ERLE ≥ 20 dB, SNR delta ≥ 5 dB on Phase 1 regression WAV |

**Done when:**
- Full Traditional chain runs live at `mic_count=1` (mandatory) and `mic_count=2` (if hardware available)
- All three stages individually enable/disable-able via config without restart
- No xruns over 5-minute run

---

## Sprint 4 — Live Visualization

**Goal:** Demo-ready GUI; output capturable for offline PESQ.

| # | Task | Detail |
|---|---|---|
| 4.1 | Live spectrogram | Input vs output side-by-side; `pyqtgraph` preferred over `matplotlib` for lower callback overhead |
| 4.2 | ERLE / SNR time plot | Scrolling 30-second window |
| 4.3 | DTD indicator | Green/red indicator driven by `dtd_active` flag from `aec.py` |
| 4.4 | GUI rate limiting | GUI thread reads from a lock-free queue populated by the audio callback; update every 10 frames (~160 ms) |
| 4.5 | Record to WAV | Button to capture a 30-second RT session to file |
| 4.6 | Offline PESQ score | Run captured WAV through Phase 1 MATLAB PESQ scorer; document MOS |

**Done when:**
- Full Traditional pipeline running with live spectrogram and metrics plots
- 30-second session recorded and PESQ-scored against Phase 1 MATLAB baseline
- GUI updates never cause xrun (xrun counter stays at 0)

---

## Sprint 5 — Hybrid DL Real Time (Conditional)

**Goal:** DL inference in the RT callback; ship if timing fits, document gate if not.

| # | Task | Detail |
|---|---|---|
| 5.1 | `nr_hybrid.py` | Translate LLD-6: STFT feature extraction, CRM mask via PyTorch or ONNX Runtime, overlap-add |
| 5.2 | Per-frame timing | Measure mean + p99 inference time over 1000 consecutive frames |
| 5.3 | Budget gate | Frame budget = 16 ms. Ship Hybrid RT if p99 < 8 ms. Otherwise produce timing report |
| 5.4 | Mode switching | Hot-switch Traditional ↔ Hybrid via GUI button (AD-04: topology unchanged only) |
| 5.5 | Graceful degrade | If inference overruns: auto-fallback to Traditional with console warning and GUI indicator |

**Done when (Gate PASS):** Hybrid RT demo running; live mode switch works; ERLE and SNR within ±2 dB of Traditional on same scenario.

**Done when (Gate FAIL):** Timing report delivered: measured p99, required model size/quantization to pass the 8 ms budget. Becomes an input to Phase 2 C/ONNX planning.

---

## Sprint 6 — RT Validation & Hardening

**Goal:** Demo certified; regression suite green; Python ready to serve as Phase 2 C reference.

| # | Task | Detail |
|---|---|---|
| 6.1 | 30-min stability run | Headless RT loop on looped WAV file; count xruns — target < 1 per minute |
| 6.2 | CPU profiling | `cProfile` per module per frame; flag any module consuming > 30% of frame budget |
| 6.3 | RT vs offline regression | All Phase 1 scenarios: ERLE ±2 dB, SNR-delta ±1 dB vs MATLAB baseline |
| 6.4 | Regression CI hook | Add Python RT offline-mode runner to `run_regression_suite` alongside MATLAB runner |
| 6.5 | Phase 2 handoff notes | Per-module time budget, reference source config, NumPy-to-C mapping notes |

**Done when:**
- All Phase 1 regression scenarios pass with Python engine
- 30-minute stability run meets xrun target
- CPU budget per module documented
- Handoff notes committed alongside code

---

## Sprint Summary

| Sprint | Deliverable | Audible / Measurable |
|---|---|---|
| 0 — Foundation | RT passthrough + latency number | Hear yourself live |
| 1 — NR | Traditional NR live | Noise audibly reduced |
| 2 — AEC | Echo cancellation live, ERLE on screen | Echo cancelled |
| 3 — Full Traditional | BF + AEC + NR, config-driven | Full pipeline live |
| 4 — GUI | Live spectrogram, metrics, WAV capture | Demo-ready |
| 5 — Hybrid DL | DL inference in RT (conditional) | Mode switch live |
| 6 — Validation | Regression green, stability certified | Certified demo |

---

## Phase Exit Criteria

The PC RT demo phase is complete when all of the following are true:

1. Full Traditional pipeline runs live with 0 xruns over 30 minutes
2. ERLE ≥ 20 dB on standard test scenario
3. SNR improvement ≥ 5 dB on standard test scenario
4. RT metrics within ±2 dB ERLE and ±1 dB SNR-delta of MATLAB Phase 1 baseline
5. All Phase 1 regression scenarios pass with Python engine
6. Hybrid RT either certified (p99 < 8 ms) or timing gate documented for Phase 2
7. Phase 2 handoff notes committed

---

## Risks

| Risk | Mitigation |
|---|---|
| WASAPI loopback not available on all Windows audio drivers | Fall back to synchronized file playback as reference; `reference.py` abstraction keeps switch config-only |
| Hybrid DL inference > 8 ms on CPU | Gate is explicit in Sprint 5; Traditional fallback keeps the demo shippable |
| 2-mic hardware not available | Sprint 3 delivers fully with `mic_count=1`; 2-mic is additive |
| GUI thread contention causing xruns | Lock-free queue between callback and GUI; rate-limited updates |

---

## Relationship to Overall Program

```
Phase 1 MATLAB (offline) ──► PC RT Demo (Python) ──► Phase 2 C / A53 Linux
        │                           │                          │
   Offline baseline            RT validation              Production embedded
   Regression WAVs             Golden reference            C port verified
   PESQ scoring                for Phase 2 C port          against Python output
```
