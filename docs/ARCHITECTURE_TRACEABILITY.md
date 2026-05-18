# ECNR Architecture Decision Traceability
## ECNR Pipeline – Decision-to-Phase-to-Module Mapping

**Version:** 1.0 | **Date:** March 23, 2026 | **Status:** Current

---

## 1. Purpose

This document maps the key architecture decisions in the ECNR document set to:

- affected product phases
- affected modules and implementation areas
- governing requirement/design documents
- intended implementation consequence

The goal is to keep PRD, SRS, HLD, and LLD aligned when architecture-level decisions are refined later.

---

## 2. Traceability Table

| Decision ID | Decision | Status | Phases Affected | Primary Modules / Areas | PRD Impact | SRS Impact | HLD Impact | LLD Impact | Implementation Consequence |
|---|---|---|---|---|---|---|---|---|---|
| AD-01 | Traditional mode is the guaranteed Phase 2 MVP; Hybrid is staged behind parity and latency validation | Resolved | Phase 1, Phase 2, Phase 3 | AEC, Traditional NR, Hybrid backend, embedded runtime | FR-12, phased delivery, embedded criteria | Phase 2 scope requirement | Phase 2 deployment scope, latency table | Hybrid module, embedded runtime backends | Embedded development can ship Traditional-first without blocking on DL deployment |
| AD-02 | DAS is the required first beamformer; MVDR-like methods are staged | Resolved | Phase 1, Phase 2 | Beamformer, config, GUI | FR-2 | Beamforming MVP expectation | Key design decisions | LLD-3 Beamformer | Multi-mic baseline can be built and validated without advanced beamforming complexity |
| AD-03 | Runtime parameters are split into hot-updateable vs restart-required classes | Resolved | Phase 1, Phase 2, Phase 3 | Config manager, GUI, runtime API, control plane | FR-7, FR-8, usability criteria | Runtime reconfiguration policy, API semantics | Configuration-driven behavior, mode switching | LLD-1 hot-parameter API | Prevents unsafe in-place mutation of topology-changing settings |
| AD-04 | Algorithm mode switching is seamless only when both backends are initialized and topology is unchanged | Resolved | Phase 1, Phase 2, Phase 3 | Mode selector, GUI, Hybrid init path, control runtime | FR-3, usability criteria | Runtime reconfiguration policy | Mode-switch design decision | LLD-1 parameter update semantics | Hybrid/Traditional switching becomes a guarded capability instead of an unconditional promise |
| AD-05 | Phase 1 live audio is feasibility-gated under the no-Audio-Toolbox constraint; offline WAV is the mandatory baseline | Resolved | Phase 1 | MATLAB I/O, GUI, test harness | FR-9, risks, phase delivery | Phase 1 audio I/O section | Phase 1 deployment architecture, risk section | LLD-10 MATLAB engine / I/O modules | Prevents Phase 1 delivery from being blocked by device integration issues |
| AD-06 | The far-end reference path must be explicitly configured rather than inferred | Resolved | Phase 1, Phase 2, Phase 3 | Config schema, ALSA I/O, offline runner, AEC input routing | FR-9, config management | Config schema and reference-source requirements | Data flow and design decisions | LLD-1 config structs, LLD-8 ALSA I/O | Eliminates ambiguity around loopback, file, and capture-channel reference acquisition |
| AD-07 | The public engine contract uses a base frame cadence; STFT overlap is internal to NR / Hybrid modules | Resolved | Phase 1, Phase 2, Phase 3 | Frame buffer manager, Traditional NR, Hybrid NR, MATLAB loop, ALSA loop | Indirectly affects FR-7/FR-9 and portability goals | Phase 1 frame-processing description | Top-level buffer architecture, data flow | LLD-2 frame buffer manager, LLD-5/6 overlap state | Prevents the whole engine API from inheriting STFT-specific overlap constraints |
| AD-08 | Phase 3 offload boundaries are profiling-driven rather than predetermined | Resolved | Phase 2, Phase 3 | A53 runtime, DSP offload, IPC, profiling | FR-13 | DSP offload requirements | Phase 3 key characteristics and latency notes | LLD-9 IPC/DSP offload | Only measured hotspots move to DSP, reducing wasted optimization effort |
| AD-09 | DSP-side Hybrid inference is optional and depends on export, memory fit, and timing feasibility | Resolved | Phase 2, Phase 3 | Hybrid backend, model export, DSP runtime | FR-13, risks | Hybrid deployment constraints | Phase 3 key characteristics | LLD-6 Hybrid module, LLD-9 IPC | Prevents Phase 3 from assuming a DL deployment path that may not fit target constraints |
| AD-10 | Single-core A53 execution is preferred for MVP simplicity but not a hard architectural constraint | Resolved | Phase 2 | Embedded runtime, ALSA loop, performance validation | Embedded acceptance criteria | Phase 2 scope wording | Phase 2 execution environment | LLD-8 processing loop policy | Allows performance tuning to choose affinity/scheduling pragmatically while preserving latency targets |
| AD-11 | Configuration profiles are schema-versioned and compatibility must be validated explicitly | Resolved | Phase 1, Phase 2, Phase 3 | Config manager, profile save/load, migration logic | FR-14 | Config schema and loader behavior | Configuration interface | LLD-1 config loading | Reduces cross-phase/profile drift and enables deterministic upgrade behavior |
| AD-12 | Offline PESQ is a validation metric, not a live processing dependency | Resolved | Phase 1, Phase 2 | Metrics, GUI, validation harness | FR-10, success metrics | Metrics computation | Deliverables and GUI behavior | LLD-7 metrics engine, LLD-10 GUI example | Keeps live paths simpler and avoids tying runtime behavior to offline-only scoring |

---

## 3. Module-Centric View

| Module / Area | Related Decisions |
|---|---|
| Configuration Manager | AD-03, AD-06, AD-11 |
| Frame Buffer Manager | AD-07 |
| Beamformer | AD-02 |
| AEC | AD-01, AD-06 |
| Traditional NR | AD-01, AD-07, AD-12 |
| Hybrid DL NR | AD-01, AD-04, AD-07, AD-09 |
| Metrics Engine | AD-12 |
| MATLAB GUI / Live I/O | AD-03, AD-04, AD-05 |
| ALSA I/O Manager | AD-06, AD-10 |
| IPC & DSP Offload | AD-08, AD-09 |
| Embedded Runtime / Daemon | AD-01, AD-10 |

---

## 4. Phase-Centric View

| Phase | Decisions With Highest Impact |
|---|---|
| Phase 1 – PC Prototyping | AD-03, AD-04, AD-05, AD-06, AD-07, AD-12 |
| Phase 2 – A53 Linux MVP | AD-01, AD-03, AD-06, AD-07, AD-10 |
| Phase 3 – DSP Optimization | AD-06, AD-08, AD-09, AD-10, AD-11 |

---

## 5. Maintenance Guidance

When a future change is proposed, review this table first and then update all linked documents together.

Examples:

- If Hybrid becomes mandatory in Phase 2, revisit AD-01, AD-04, AD-09.
- If the reference path changes from loopback to dedicated capture hardware, revisit AD-06.
- If the engine moves to a different frame contract, revisit AD-07.
- If single-core execution becomes mandatory again, revisit AD-10.

---

## 6. Current Outcome

At the time of this revision, the main architecture decisions are resolved well enough to support implementation planning. The remaining uncertainty is operational and platform-specific rather than structural:

- exact MATLAB live-audio adapter choice
- exact embedded Hybrid runtime/export path
- exact DSP IPC/runtime stack details within the TI-supported integration space

These should be handled as implementation-stage feasibility and profiling tasks rather than as open architecture contradictions.