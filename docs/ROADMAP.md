# ECNR Program Roadmap

**Last updated:** 2026-06-04  
**Purpose:** Canonical phase roadmap and program-level decision trajectory.

---

## Phase Sequence

1. Phase 0 - Architecture and decisions
2. Phase 1A/B - MATLAB offline engine and GUI
3. Phase 1D - Python PC real-time demo
4. Phase 2 - C/C++ portable core on AM62x Linux
5. Phase 3 - DSP/NPU offload and optimization

---

## Current Status Snapshot

| Phase | Status | Notes |
|---|---|---|
| Phase 0 | Complete | Engine contract and phase strategy established. |
| Phase 1A/B | Complete | MATLAB traditional baseline, regression, and GUI complete. |
| Phase 1D | Complete | Regression pass and profiling captured; Hybrid deferred by gate. |
| Phase 2 | Not started | Handoff document ready; implementation not started. |
| Phase 3 | Not started | Depends on Phase 2 profiling and exit criteria. |

---

## Key Program Decisions

- Traditional processing path is the required baseline for embedded parity.
- Python Phase 1D is the behavioral reference before C/C++ porting.
- Hybrid DL remains gated by model availability and timing validation.
- Runtime config updates are split between hot-update and restart-required classes.
- DSP offload scope is profiling-driven, not predetermined.

See detailed design traceability in `docs/ARCHITECTURE_TRACEABILITY.md`.

---

## Execution Guidance

- Run procedures: `docs/RUNBOOK_OPERATIONS.md`
- Acceptance and phase gates: `docs/ACCEPTANCE_CRITERIA.md`
- Module-by-module implementation status: `docs/MODULES_STATUS.md`
- C-port technical handoff: `docs/PHASE2_HANDOFF.md`
