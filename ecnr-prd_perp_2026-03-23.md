# Product Requirements Document (PRD)
**Echo Cancellation and Noise Reduction (ECNR) Pipeline – Automotive & Consumer**

## 1. Product Overview

The product is a multi-phase Echo Cancellation and Noise Reduction (ECNR) pipeline targeting both **automotive cabins** (hands‑free, in‑vehicle voice) and **consumer speaker/smart‑speaker** scenarios. The pipeline shall support **1, 2, or 4 microphones** with an optional beamformer, and be robust to **20–120 cm** acoustic path distances between microphones and loudspeakers.

Development is organized into three phases:

- **Phase 1 – PC Prototyping & Tuning:**
  - Implementation in **MATLAB** (for traditional DSP ECNR) as the primary environment.
  - MATLAB implementation shall use only **base MATLAB and Signal Processing Toolbox**; no Audio Toolbox or other optional MATLAB toolboxes are allowed.
  - Optional **Python** implementation to host deep‑learning components for Hybrid mode.
  - Rich **GUI** for algorithm selection, parameter tuning, visualization, and metric reporting.
  - I/O via **WAV files** and **real‑time capture/playback** using PC audio devices and **RME Fireface** (within the constraints of base MATLAB and Signal Processing Toolbox).

- **Phase 2 – Simple Embedded Deployment (MVP):**
  - Port the proven ECNR pipeline to a **TI AM62x “Symphony” evaluation board** as a Linux user‑space application on the **Arm Cortex‑A53** cores, using standard audio interfaces (e.g., ALSA).
  - Focus on **functional correctness** and feature parity with Phase 1, accepting moderate latency.
  - AM62x is a Sitara-class SoC with quad Cortex‑A53 cores and audio‑focused collateral for implementing echo cancellation and related algorithms.

- **Phase 3 – Optimized Embedded Deployment:**
  - Performance‑orient the implementation for **low latency** and **power efficiency** by offloading heavy ECNR processing to the **C7x DSP / accelerator** where available on the AM62 family.
  - Introduce RTOS/IPC as needed to run the DSP core and integrate it with the A53 Linux system.

---

## 2. Goals and Non‑Goals

### 2.1 Goals

- Provide a **configurable ECNR pipeline** suitable for automotive and consumer devices with up to 4 microphones and an optional beamformer.
- Deliver a **Phase 1 tool** that enables algorithm research, tuning, and QA through a unified GUI with detailed performance metrics and visualizations.
- Enable **Phase 2 embedded deployment** on TI AM62x with minimal porting effort from Phase 1.
- Optimize **Phase 3** for low latency and power while preserving (or improving) ECNR performance.

### 2.2 Non‑Goals

- No requirement to support **non‑TI** embedded platforms in this project scope.
- No requirement to implement a **pure DL‑only** pipeline without linear AEC (Hybrid is always Linear AEC + DL).
- No requirement for **multi‑room** or distributed microphone architectures beyond 4 mics on a single board.

---

## 3. Target Environments and Configurations

### 3.1 Acoustic Environments

- **Automotive cabin:**
  - Hands‑free calling, voice assistant, and in‑vehicle communication.
  - High background noise variability (engine, road, wind).
- **Consumer speaker / smart speaker:**
  - Stationary room environment with reverberation and household noises.

### 3.2 Microphone & Loudspeaker Topology

- **Microphone options:**
  - 1 mic
  - 2 mics (e.g., spaced linear array)
  - 4 mics (e.g., circular or linear array)
- **Beamformer:**
  - Optional **Delay‑and‑Sum (DAS)** and/or **MVDR‑like** beamforming for multi‑mic modes.
- **Distance constraints:**
  - Mic–speaker distance configurable in the range **20–120 cm**.

---

## 4. User Personas

- **Audio Tuning Engineer**
  - Uses Phase 1 GUI to tune filters and parameters for specific vehicle or device configurations.
- **Algorithm Researcher**
  - Compares Traditional vs Hybrid pipelines, experiments with DL models, and inspects artifacts.
- **QA / Validation Engineer**
  - Runs regression test suites, verifies objective metrics and listens to reference scenarios.
- **Embedded Software Engineer**
  - Integrates, ports, and debugs ECNR on TI AM62x (Phase 2 and 3).
- **Systems Architect**
  - Ensures architecture supports future feature extensions and other TI platforms.

---

## 5. User Stories

- **US‑01:** As an Audio Tuning Engineer, I want to select **1, 2, or 4 microphones** and enable/disable the beamformer in the GUI so I can quickly adapt the pipeline to different hardware setups.
- **US‑02:** As an Algorithm Researcher, I want to dynamically switch between **Traditional (NLMS + Spectral Subtraction)** and **Hybrid (Linear AEC + DL Noise/Echo Suppression)** modes in the GUI so I can compare their audio quality, convergence behavior, and residual echo/noise.
- **US‑03:** As a QA Engineer, I want to run both **offline WAV** test suites and **real‑time audio** via PC audio / RME Fireface so I can validate corner cases and live behavior.
- **US‑04:** As an Embedded Engineer, I want the Phase 2 implementation on **Arm Cortex‑A53 / Linux** to use standard audio APIs (e.g., ALSA) so I can integrate it into existing pipelines with minimal changes.
- **US‑05:** As a Systems Architect, I want Phase 3 to offload heavy DSP work to the **C7x DSP/accelerator** to achieve tight latency and power budgets without changing the high‑level API.

---

## 6. Functional Requirements

### 6.1 Feature Table

| ID | Feature | Description | Notes for Implementation |
|---|---|---|---|
| **FR‑1** | Mic configuration management | Support **1, 2, or 4** microphones as input channels with selectable array geometry (e.g., linear, circular) per profile. | Geometry parameters (mic spacing, angles) stored in configuration files. |
| **FR‑2** | Beamformer | Optional beamformer stage for multi‑mic configurations (DAS and/or MVDR‑style). | Initial implementation shall support DAS; advanced beamforming such as MVDR‑like processing may be staged after baseline multi‑mic support is stable. |
| **FR‑3** | Algorithm modes | Implement **two selectable modes**: (1) **Traditional**: Linear adaptive AEC (e.g., NLMS) followed by classical noise reduction (e.g., spectral subtraction or Wiener‑type post‑filter). (2) **Hybrid**: Same linear AEC followed by a **DL‑based noise reduction/echo suppression** module operating on the residual signal. | Mode switching shall be seamless only when both processing backends are already initialized and the active topology is unchanged. Otherwise, the system may perform controlled reinitialization rather than unsafe in‑place switching. Each mode is represented as a pluggable processing chain (Strategy pattern). |
| **FR‑4** | Acoustic path coverage | Support mic–speaker distances of **20–120 cm** by configuring adaptive filter length and algorithm parameters. | Filter length (taps) must be configurable (e.g., up to 1024 taps at 16 kHz) to cover room and system delay. |
| **FR‑5** | Phase 1 MATLAB pipeline | Implement full **Traditional** ECNR chain in MATLAB, including: adaptive AEC, noise reduction, optional beamformer, metric computation, and GUI binding. Implementation shall use only **base MATLAB and Signal Processing Toolbox** (no Audio Toolbox or other optional MathWorks toolboxes). | MATLAB acts as the reference implementation for later C/C++ port. |
| **FR‑6** | Phase 1 Python pipeline (DL) | Provide Python pipeline hosting the **DL component** used in Hybrid mode; may reuse C/C++ core for AEC when feasible. | Python used for model training/inference experiments and integration into Hybrid mode. |
| **FR‑7** | Unified GUI / Tuning | GUI (primarily MATLAB; optional Python/combined front‑end) to control: mic count, beamformer on/off, algorithm mode (Traditional/Hybrid), sampling rate, frame size, and all key tuning params. | Safe tuning parameters shall be adjustable in real time. Topology‑changing parameters such as sample rate, frame size, mic count, and model binary may use controlled reinitialization rather than in‑place update. |
| **FR‑8** | Tuning parameters | Expose at minimum: adaptive filter step size, filter length, double‑talk detection thresholds, noise suppression aggressiveness, beamformer steering, DL aggressiveness/model selection (Hybrid only). | Parameters shall be classified as either hot‑updateable or restart‑required, with the policy documented and enforced consistently in the GUI and runtime API. |
| **FR‑9** | I/O modes | Support: (1) Offline processing of one or more WAV files. (2) Real‑time capture/playback from **PC audio devices** and **RME Fireface**. | Support at least 16 kHz and 48 kHz sample rates. The design shall define an explicit far-end reference acquisition/routing method for AEC. Phase 1 live device support shall be validated by an early feasibility spike under the no‑Audio‑Toolbox constraint; offline WAV processing remains the mandatory baseline. |
| **FR‑10** | Metric computation | Compute and log objective metrics: ERLE, convergence time, PESQ (offline), segmental SNR, and double‑talk behavior statistics. | Metrics accessible in GUI and saved to disk (e.g., CSV). |
| **FR‑11** | Visualization | GUI plots: time‑domain waveforms (mic, reference, output), ERLE over time, spectrograms (before/after ECNR), and VAD/double‑talk indicators. | Real‑time plotting must not cause buffer under‑runs. |
| **FR‑12** | Phase 2 AM62x port | Port core ECNR logic to **C/C++** and run as a Linux user‑space process on AM62x A53 cores, interfacing via ALSA (or TI audio framework). | Phase 2 MVP shall guarantee Traditional mode parity first. Hybrid support is preferred but may be added only after parity and latency targets are met. |
| **FR‑13** | Phase 3 DSP offload | Offload ECNR processing (AEC, noise reduction, optionally DL) to **C7x DSP/accelerator** as appropriate, using TI’s recommended audio and IPC framework. | Offload scope shall be profiling‑driven so only stages that materially improve latency and/or power are moved to DSP. |
| **FR‑14** | Configuration management | Support loading/saving configuration profiles (vehicle model, room, mic layout, chosen mode, parameters). | Config as JSON/YAML or MATLAB structs in Phase 1; mirrored in Phase 2/3. Profiles shall include schema versioning and compatibility rules. |

---

## 7. Non‑Functional Requirements

- **NFR‑1 – Latency:**
  - Phase 1 (PC): Latency is non‑critical but should be **< 80 ms** for realistic tuning.
  - Phase 2 (A53/Linux): End‑to‑end latency **< 40 ms** for acceptable user experience.
  - Phase 3 (DSP): End‑to‑end latency **< 15 ms** for high‑quality interactive communication.

- **NFR‑2 – Audio Quality:**
  - No excessive musical noise or speech distortion in Traditional mode.
  - Hybrid mode must not degrade PESQ relative to Traditional, and ideally must improve it.

- **NFR‑3 – Portability & Code Quality:**
  - Core DSP logic implemented in clean, portable **C/C++** with well‑defined interfaces and no platform‑specific assumptions.
  - Python and MATLAB are used primarily as wrappers and experimentation environments.

- **NFR‑4 – Resource Usage (Phase 3):**
  - DSP/MMA utilization and memory footprint shall fit within AM62x platform constraints while maintaining real‑time operation.

- **NFR‑5 – Robustness:**
  - Stable under varying input levels, sample drops, and real‑time stress; must fail gracefully with clear logging.

---

## 8. Success Metrics and Acceptance Criteria

### 8.1 Objective Metrics

| Metric | Target | Notes |
|---|---|---|
| **ERLE** | ≥ 40 dB during far‑end single‑talk | Computed over steady segments without near‑end speech. |
| **Convergence Time** | ≤ 1.0 s to reach 20 dB ERLE from cold start | Measured after echo path changes. |
| **PESQ (P.862)** | ≥ 3.5 MOS equivalent for near‑end speech | Evaluated on standardized test suites. |
| **Segmental SNR Improvement** | ≥ 5 dB vs. noisy input in Hybrid mode | For typical automotive and domestic noise recordings. |
| **Double‑Talk Transparency** | < 3 dB average attenuation of near‑end speech | During overlapping near‑end/far‑end speech. |

### 8.2 Usability & Tooling Criteria

- GUI can switch algorithm mode and safe tuning parameters during operation without audible interruption only when the processing topology remains unchanged and the required backend is already initialized.
- Topology‑changing updates such as mic count, frame size, sample rate, or model binary may use controlled reinitialization, provided the behavior is explicit to the user and does not corrupt engine state.
- Real‑time plots are responsive (≥ 30 FPS perceived interaction) and do not cause underruns.
- Configuration save/load is reliable and round‑trippable across sessions.

### 8.3 Embedded Criteria

- Phase 2 AM62x build runs in real time at target sample rates within the target A53 CPU budget; single-core execution is preferred for MVP simplicity but is not mandatory if measured latency and integration constraints justify a different core allocation.
- Phase 3 offloaded version meets latency targets and shows measurable power reduction vs. A53‑only.

---

## 9. Phased Delivery Plan

- **Phase 1 – PC Prototyping**
  - Deliver MATLAB Traditional pipeline + GUI using only base MATLAB and Signal Processing Toolbox.
  - Deliver Python DL component + Hybrid integration for experiments, with offline integration as the required baseline and real‑time integration added only if feasible.
  - Complete metric computation and visualization.

- **Phase 2 – Simple Embedded Deployment (A53/Linux)**
  - Port core ECNR to C/C++.
  - Integrate with ALSA on AM62x evaluation board.
  - Verify functional parity with Phase 1 Traditional mode and acceptable latency before enabling staged Hybrid support.

- **Phase 3 – Optimized Embedded Deployment (DSP)**
  - Migrate compute‑intensive blocks to C7x DSP/accelerator based on measured hotspots and IPC overhead.
  - Tune for low latency and power.
  - Finalize production‑ready configuration profiles for target products.

---

## 10. Risks and Assumptions

- **Assumptions**
  - TI AM62x board, toolchains, and audio drivers are available and stable.
  - Access to representative **automotive** and **consumer room** noise/echo datasets.

- **Risks**
  - DL model complexity may exceed DSP resource limits, requiring architecture simplification.
  - Integration of real‑time plotting and audio I/O on lower‑end PCs may cause underruns if not optimized.
  - Phase 1 live audio and RME Fireface support may require a native helper or phased rollout because of the no‑Audio‑Toolbox constraint.
