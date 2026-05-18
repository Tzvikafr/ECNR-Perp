# High-Level Design (HLD)
## ECNR Pipeline – Automotive & Consumer Multi-Phase Deployment

**Version:** 2.0 | **Date:** March 23, 2026 | **Status:** Complete

---

## 1. Executive Summary

This High-Level Design (HLD) document defines the complete system architecture for the Echo Cancellation and Noise Reduction (ECNR) pipeline across three deployment phases:

- **Phase 1:** PC-based prototyping in MATLAB and Python with GUI tuning environment
- **Phase 2:** Embedded MVP deployment on TI AM62x Cortex-A53 Linux
- **Phase 3:** Optimized DSP offload to TI C7x accelerator with RPMsg IPC

The architecture is driven by five non-negotiable principles: separation of concerns, strategy pattern for algorithm selection, pre-allocated memory (no dynamic allocation in hot paths), configuration-driven behavior, and portable core DSP logic.

---

## 2. Architectural Principles

### 2.1 Separation of Concerns

The system is divided into three orthogonal layers:

1. **I/O & Control Layer** (platform-specific, replaceable per phase)
2. **Core DSP Engine** (portable C/C++ for embedded phases, with equivalent module behavior across phases)
3. **Metrics & Output Layer** (decoupled, non-blocking logger thread)

This separation enables low-friction porting from Phase 1 (MATLAB) to Phase 2 (Linux A53) to Phase 3 (DSP offload) while preserving the same engine contract, configuration semantics, and validation flow.

### 2.2 Strategy Pattern for Processing Chains

Traditional (spectral subtraction) and Hybrid (DL-based) noise reduction chains are pluggable backends behind a unified `ecnr_process_frame()` interface. Runtime mode switching is a design goal for safe same-topology changes; topology-changing updates such as sample rate, frame size, mic count, and model binary may require controlled reinitialization.

### 2.3 No Dynamic Allocation in Hot Path

All module state is pre-allocated during `ecnr_create()` initialization. The real-time processing loop (`ecnr_process_frame()`) uses only stack and statically allocated buffers—guaranteeing deterministic latency and no memory fragmentation.

### 2.4 Configuration-Driven Behavior

A versioned JSON/YAML configuration file parameterizes the entire pipeline. Configuration is validated at startup, safe tuning updates are applied atomically at frame boundaries, and structural changes use controlled reinitialization rather than in-place mutation.

### 2.5 Portable Core DSP Logic

Core DSP logic is implemented as a portable C/C++ engine for embedded deployment, with MATLAB serving as the reference algorithm environment in Phase 1. Equivalent module boundaries and configuration semantics are preserved across phases even when the exact implementation language differs.

---

## 3. Top-Level System Architecture

### 3.1 Three-Layer Block Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   I/O & CONTROL LAYER                           │
│              (Platform-Specific per Phase)                       │
│                                                                 │
│  Mic Input  Reference Input  Config File  GUI / CLI Controls    │
│      │            │               │              │              │
│      └────────────┴───────────────┴──────────────┘              │
│                       │                                         │
│              ┌────────▼────────────┐                           │
│              │  Frame Buffer Mgr   │                           │
│              │  (Ring Buffers,     │                           │
│              │   Fixed Frame Cadence)│                         │
│              └────────┬────────────┘                           │
└─────────────────────────┼──────────────────────────────────────┘
                          │ ecnr_frame_t
        ┌─────────────────▼─────────────────┐
        │   CORE DSP ENGINE (Portable C)     │
        │                                   │
        │  ┌─────────────────────────────┐  │
        │  │ Beamformer (DAS, optional)  │  │
        │  │ 1/2/4 ch → 1 ch             │  │
        │  └────────┬────────────────────┘  │
        │           │                       │
        │  ┌────────▼────────────────────┐  │
        │  │ Linear AEC (NLMS + DTD)     │  │
        │  │ Echo-cancelled residual     │  │
        │  └────────┬────────────────────┘  │
        │           │                       │
        │      ┌────▼────┐                  │
        │      │   Mode  │                  │
        │      │ Selector│                  │
        │      └─┬──────┬┘                  │
        │    ┌───▼┐  ┌──▼────┐              │
        │    │Trad│  │Hybrid │              │
        │    │ NR │  │DL NR  │              │
        │    └─┬──┘  └───┬───┘              │
        │      └────┬────┘                  │
        │  ┌────────▼────────────────────┐  │
        │  │ Output Stage                │  │
        │  │ (Overlap-Add + CNoise)      │  │
        │  └────────┬────────────────────┘  │
        └───────────┼──────────────────────┘
                    │ enhanced_out
    ┌───────────────▼───────────────┐
    │  OUTPUT & METRICS LAYER       │
    │  ┌──────────────────────────┐ │
    │  │ Audio Output             │ │
    │  │ ALSA / WAV / PC Audio    │ │
    │  └──────────────────────────┘ │
    │  ┌──────────────────────────┐ │
    │  │ Metrics Engine (ERLE,    │ │
    │  │ SNR, DTD) → CSV/GUI      │ │
    │  └──────────────────────────┘ │
    └───────────────────────────────┘
```

---

## 4. Deployment Architecture by Phase

### 4.1 Phase 1 — PC (MATLAB + Python)

**Execution Environment:**
- MATLAB process: App Designer GUI, offline batch runner, and optional real-time loop
- Python process (Hybrid only): PyTorch/TensorFlow DL inference
- Communication: offline file exchange or other simple bridge first; real-time IPC only after feasibility and interface stability are proven

**Key Characteristics:**
- All modules implemented in MATLAB using only base MATLAB + Signal Processing Toolbox (no Audio Toolbox)
- Python wraps DL components for Hybrid experiments, with offline integration as the baseline
- Real-time frame loop may use a timer or another MATLAB-compatible callback/helper approach depending on Phase 1 feasibility results
- Latency non-critical (target < 80 ms)

**Typical Configuration:**
```
Phase 1 PC
├── MATLAB Process
│   ├── ECNR_GUI (App Designer uifigure)
│   ├── IO_Manager (WAV offline OR validated live audio adapter)
│   ├── ECNREngine.m
│   │   ├── Beamformer.m
│   │   ├── AEC_NLMS.m
│   │   ├── NR_Traditional.m or NR_Hybrid.m
│   │   └── MetricsEngine.m
│   └── Plots: ERLE, Spectrograms, Metrics
└── Python Process (Optional)
    ├── dl_model.py (PyTorch inference)
  └── hybrid_wrapper.py (offline bridge first, real-time bridge optional)
```

### 4.2 Phase 2 — AM62x Cortex-A53 Linux (Functional MVP)

**Execution Environment:**
- Single `ecnr_daemon` C/C++ process with Linux real-time tuning as needed
- Core allocation, CPU affinity, and scheduler policy applied as part of performance tuning, with single-core execution preferred but not architecturally mandatory
- Standard ALSA audio I/O
- No DSP involvement (all compute on A53)

**Key Characteristics:**
- Full feature parity target with Phase 1 Traditional mode (Hybrid staged for later)
- Portable C core compiled with ARM GCC
- End-to-end latency target: < 40 ms
- Configuration and log locations are deployment-specific

**Typical Deployment:**
```
AM62x Linux (Phase 2)
├── ecnr_daemon (C binary with Linux real-time tuning as required)
│   ├── alsa_io.c (ALSA capture/playback)
│   ├── processing_loop.c (real-time frame loop)
│   ├── libecnr.a (portable core: BF, AEC, NR, Metrics)
│   └── metrics_logger.c (background thread)
├── /etc/ecnr/ecnr_config.json
└── /var/log/ecnr_metrics.csv
```

### 4.3 Phase 3 — AM62x + C7x DSP (Optimized Deployment)

**Execution Environment:**
- A53 side: ALSA I/O, configuration, control via RPMsg
- C7x DSP side: Core ECNR processing (AEC, NR) via ping-pong DDR buffers
- IPC: TI RPMsg over carveout DDR shared memory

**Key Characteristics:**
- Heavy DSP work is offloaded to C7x only for stages that show measurable benefit after profiling
- A53 side uses optimized C core for lightweight tasks (copy, format)
- End-to-end latency target: < 15 ms
- DL inference on DSP is optional and depends on proven model export, memory fit, and timing budget; if not feasible, Hybrid remains on A53 or is staged out
- Power efficiency: significant reduction vs. A53-only Phase 2

**Typical Architecture:**
```
AM62x (Phase 3)
├── A53 Linux Host (ecnr_host binary)
│   ├── alsa_io.c (ALSA I/O)
│   ├── ipc_host.c (RPMsg + DDR buffer management)
│   ├── control_server.c (Unix socket for ECNR_SET_PARAM)
│   └── metrics_logger.c (CSV from shared memory)
│
└── C7x DSP (ecnr_dsp_fw, TI RTOS/runtime selected during platform integration)
    ├── ipc_dsp.c (RPMsg mailbox handlers)
    ├── libecnr_c7x.a (optimized core)
    │   ├── AEC: MMA/VCOP intrinsics for filter inner loop
    │   └── NR: DSPLIB optimized real FFT
  └── dl_infer.c (optional backend if Hybrid is offloaded)
```

---

## 5. Data Flow (End-to-End)

### 5.1 Typical Processing Loop

```
[Loudspeaker outputs far-end audio]
         │
         ├──────────────────┐
         │ Acoustic Echo    │ (20–120 cm path,
         │ Path             │  room reverb)
         │                  │
[Mic Array] ◄──────────────┘  [Reference Signal (DAC tap)]
    │                              │
    └──────┬────────────────────────┘
           │
           ▼
    ┌─────────────────┐
    │ Frame Buffer    │ (Ring buffers, fixed engine frame cadence)
    └────────┬────────┘
             │ Fixed-size frames
             ▼
    ┌─────────────────────────┐
    │ Beamformer              │ (N ch → 1 ch)
    │ (if enabled)            │
    └────────┬────────────────┘
             │ Single enhanced channel
             ▼
    ┌──────────────────────────────┐
    │ Linear AEC (NLMS)            │
    │ with Double-Talk Detection   │
    └────────┬─────────────────────┘
             │ Echo-cancelled residual
             ▼
    ┌────────────────────────┐
    │ Mode Decision          │
    │ (Traditional/Hybrid)   │
    └┬──────────────────────┬┘
     │                      │
     ▼ (Traditional)        ▼ (Hybrid)
┌──────────────┐      ┌──────────────────┐
│Spectral      │      │Feature Extract   │
│Subtraction   │      │  ↓               │
│Wiener Filter │      │DL Model Inference│
│(STFT domain) │      │  ↓               │
└──────┬───────┘      │Mask Application  │
       │              └────────┬─────────┘
       │                       │
       └───────────┬───────────┘
                   │ Enhanced speech
                   ▼
         ┌──────────────────────┐
         │ Output Stage         │
         │ (Overlap-Add, CNoise)│
         └──────────┬───────────┘
                    │ Enhanced PCM
                    ▼
         ┌──────────────────────┐
         │ Audio Output         │
         │ (ALSA/WAV/PC Audio)  │
         └──────────────────────┘

         ┌──────────────────────┐
         │ Metrics (async)      │
         │ ERLE, SNR, DTD       │
         │ → CSV / GUI          │
         └──────────────────────┘
```

---

## 6. Technology Stack

### 6.1 By Phase and Concern

| Concern | Phase 1 | Phase 2 | Phase 3 |
|---------|---------|---------|---------|
| **Language (Core)** | MATLAB + Python | C/C++ (GCC ARM) | C/C++ (TI CGT C7x) |
| **GUI** | MATLAB App Designer | — | — |
| **DL Inference** | PyTorch / TensorFlow | Optional runtime selected after export feasibility | Optional DSP-capable runtime if justified |
| **Audio I/O** | WAV + validated live audio adapter | ALSA (libasound) | ALSA (A53) + IPC to DSP |
| **IPC** | TCP socket / files | — | RPMsg + Carveout DDR |
| **Config Format** | JSON (jsondecode) | JSON (cJSON) | JSON (cJSON) |
| **Metrics Output** | MATLAB GUI + CSV | CSV + syslog | CSV via A53 host |
| **Build System** | MATLAB project | CMake + AM62x SDK | CMake + TI Code Composer |
| **RTOS (DSP)** | — | — | TI-supported runtime selected during bring-up |

---

## 7. Latency Budget & Real-Time Constraints

### 7.1 Latency Breakdown (illustrative milliseconds)

| Processing Stage | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Audio driver buffering | ~20 | ~10 | ~5 |
| Frame buffering (256 samples @ 16 kHz = 16 ms) | 16 | 10 | 5 |
| Beamformer | ~1 | ~1 | ~0.2 |
| AEC (NLMS, 512 taps) | ~3 | ~5 | ~0.5 |
| Traditional NR (FFT + Spectral Sub) | ~2 | ~4 | ~0.5 |
| Hybrid DL NR | ~20 | staged, not part of MVP budget | target-dependent |
| IPC overhead | — | — | ~1 |
| **Total (Traditional)** | **~42 ms** | **~30 ms** | **~12 ms** |
| **Total (Hybrid)** | **~62 ms** | **not committed for Phase 2 MVP** | **target-dependent** |
| **Requirement** | **< 80 ms** | **< 40 ms** | **< 15 ms** |

These figures are planning estimates, not contractual guarantees. Final budgets depend on chosen frame size, sample rate, model complexity, and IPC behavior measured on the target platform.

### 7.2 Real-Time Safety Measures

- **Phase 1:** Non-blocking GUI updates and rate-limited plotting, with the exact callback mechanism chosen after feasibility validation
- **Phase 2:** Pre-allocated buffers, minimal blocking in the processing path, and Linux scheduling/affinity tuning as required by profiling
- **Phase 3:** IPC designed around bounded queueing and measured buffer ownership/latency; exact message sizes and transport details are implementation-specific

---

## 8. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Adaptive filter algorithm | NLMS | O(L) complexity; sufficient convergence for 20–120 cm path; simpler tuning than RLS |
| NR processing domain | STFT (frequency) | Per-bin gain control; works for both spectral subtraction and DL CRM mask application |
| DL integration point | Post-AEC residual | Prevents DL from undoing AEC; guarantees baseline ERLE floor from linear filter |
| IPC mechanism (Phase 3) | RPMsg + carveout DDR | TI standard for AM62x; DDR transfer avoids serialization overhead; ping-pong avoids stall |
| Mode switching | Strategy pattern with guarded hot-switching | Preserves audio continuity only when the target backend is already initialized and topology is unchanged, while allowing controlled reinitialization for structural updates |
| Reference routing | Explicit configured reference source | AEC correctness depends on a synchronized far-end reference rather than implicit microphone-channel reuse |
| Config format | JSON | Same schema MATLAB → C; round-trippable; human-readable; toolchain-agnostic |
| Beamformer type | Delay-and-Sum (DAS) | Simpler than MVDR; sufficient for 2/4-mic arrays; low latency (fractional-delay FIR) |
| Double-talk strategy | Freeze weights during DT | Prevents AEC divergence; simpler than spectral subtraction or RLS variance tracking |

---

## 9. Cross-Phase Portability

### 9.1 Code Reuse Strategy

```
Phase 1 (MATLAB)
    ↓
    ├─ Reference implementation (algorithm validation)
    ├─ Prototype DL models (PyTorch)
    └─ GUI framework + tuning workflow

    ↓ Porting

Phase 2 (C/C++ on A53)
  ├─ Portable core DSP matched to MATLAB reference behavior
    ├─ ALSA I/O wrapper
    ├─ CLI control + metrics logging
    └─ Functional parity with Phase 1 Traditional

    ↓ Optimization + Offload

Phase 3 (C/C++ on A53 + C7x DSP)
    ├─ Portable core DSP (same algorithms, optimized for C7x)
    ├─ A53: I/O, formatting, control
    ├─ DSP: AEC + NR compute (VCOP, MMA intrinsics)
    ├─ RPMsg IPC layer
    └─ Latency / power improvement maintained
```

### 9.2 Minimal Porting Effort

- Core `ecnr_create()`, `ecnr_process_frame()`, `ecnr_destroy()` API is preserved across embedded phases and mirrored by the MATLAB reference wrapper
- I/O and platform integration layers are replaced per phase while preserving the engine contract
- Configuration schema is **identical** JSON/YAML across all phases
- Unit tests written in Phase 1 remain valid in Phase 2/3 (with platform-specific test harness)

---

## 10. System Interfaces

### 10.1 External API Contract (Language-Neutral)

```c
// Core Processing
ecnr_handle_t ecnr_create(const ecnr_config_t *cfg);
int ecnr_process_frame(ecnr_handle_t h, 
                       const ecnr_frame_t *in, 
                       ecnr_frame_t *out);
int ecnr_set_param(ecnr_handle_t h, 
                   const char *key, 
                   float value);
int ecnr_get_metrics(ecnr_handle_t h, 
                     metrics_record_t *out);
void ecnr_destroy(ecnr_handle_t h);
```

### 10.2 Configuration Interface

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
  "mode": "traditional",
  "aec": {
    "filter_length": 512,
    "step_size": 0.1,
    "regularization": 0.001,
    "double_talk_threshold_db": -20
  },
  "nr": {
    "type": "spectral_subtraction",
    "aggressiveness_db": 12,
    "spectral_floor_db": -30,
    "noise_smooth_alpha": 0.95
  },
  "dl": {
    "model_id": "ecnr_crn_v1",
    "model_path": "/models/ecnr_crn_v1.tflite",
    "operating_point": 0.5
  }
}
```

---

## 11. Risk Mitigation & Assumptions

### 11.1 Assumptions

- TI AM62x board, toolchains, and Linux drivers are stable and available
- Representative automotive + consumer room noise/echo datasets available for tuning
- A deployable Hybrid model can be identified that fits the selected runtime and measured platform budget, or the release can fall back to Traditional-only where needed

### 11.2 Key Risks & Mitigation

| Risk | Mitigation |
|---|---|
| DL model size exceeds C7x SRAM | Model quantization (INT8); architecture simplification (depthwise convolutions) |
| Real-time plotting causes underruns (Phase 1) | Rate-limit GUI updates to 10-frame intervals (160 ms) |
| A53 CPU insufficient for Hybrid mode | Stage Hybrid support after Phase 2 MVP; fall back to Traditional on A53 if needed |
| Phase 1 live audio path under no-Audio-Toolbox constraint is unstable | Run a feasibility spike early; keep offline WAV processing as the guaranteed baseline |
| DSP-side Hybrid inference fails timing or memory budget | Keep Hybrid on A53 or stage it out of the DSP release |

---

## 12. Deliverables & Success Criteria

### 12.1 Phase 1 Deliverables
- ✓ Full MATLAB Traditional pipeline (base MATLAB + Signal Processing Toolbox only)
- ✓ Python DL component with Hybrid integration, with offline bridging as the required baseline
- ✓ GUI with real-time metric visualization
- ✓ Unit test suite (AEC ERLE ≥ 40 dB, NR SNR ≥ 5 dB)

### 12.2 Phase 2 Deliverables
- ✓ Portable C core (compilable for ARM GCC + TI CGT)
- ✓ ALSA I/O integration on AM62x
- ✓ Functional parity with Phase 1 Traditional
- ✓ End-to-end latency < 40 ms verified
- ✓ Regression test suite (MATLAB vs. C output comparison)

### 12.3 Phase 3 Deliverables
- ✓ C7x DSP kernel (AEC + NR with VCOP/MMA optimization)
- ✓ RPMsg IPC layer (A53 ↔ DSP)
- ✓ End-to-end latency < 15 ms verified
- ✓ Power measurement showing meaningful improvement vs. Phase 2 A53-only where offload is enabled
- ✓ Production-ready configuration profiles (automotive, consumer room)

---

## 13. Conclusion

This HLD defines a scalable, portable ECNR pipeline engineered for seamless progression from PC-based prototyping to embedded optimization. By adhering to five core architectural principles and maintaining a clean separation of concerns, the system achieves:

- **Rapid prototyping** in Phase 1 with full algorithm flexibility
- **Functional embedded MVP** in Phase 2 with minimal porting effort
- **Production-grade optimization** in Phase 3 via DSP offload and power tuning

The architecture is intended to be implementation-ready: module boundaries, interfaces, and phase gates are explicit, while selected low-level deployment choices remain subject to platform feasibility and profiling results.
