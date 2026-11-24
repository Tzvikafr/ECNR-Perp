# ECNR Acceptance Criteria

**Last updated:** 2026-06-04  
**Purpose:** Canonical acceptance gates and verification criteria by phase.

---

## 1) Product-Level Quality Targets

Primary quality targets originate from PRD success metrics:

- ERLE target during far-end single talk
- Convergence behavior after path change
- Segmental SNR improvement
- Double-talk transparency
- Offline perceptual quality checks (where applicable)

Source: `docs/PRD.md` Section 8.

---

## 2) Phase 1A/B Gate (MATLAB Baseline)

Gate is considered met when:

1. MATLAB offline regression suite passes with frozen baseline artifacts.
2. Traditional pipeline stages operate in configured order and emit metrics.
3. GUI can run scenarios, show metrics, and export outputs.

Operational verification steps are in `docs/RUNBOOK_OPERATIONS.md`.

---

## 3) Phase 1D Gate (Python PC RT Demo)

Gate is considered met when:

1. Python regression suite returns PASS (exit code 0).
2. Offline profile shows processing within frame budget on target PC setup.
3. Full traditional RT pipeline is validated (BF, AEC, NR) with stable operation.
4. Hybrid remains explicitly deferred unless timing/model gate is passed.

Reference evidence is maintained in `docs/TASK_STATUS.md`.

---

## 4) Phase 2 Entry Gate

Phase 2 work may start when:

1. Phase 1D regression and profiling evidence is captured.
2. Python behavior is accepted as parity reference for C/C++ port.
3. Handoff notes include timing budget and known parity caveats.

Current handoff owner: `docs/PHASE2_HANDOFF.md`.

---

## 5) Phase 2 Exit Gate (Planned)

Phase 2 exit requires:

1. C/C++ core parity against Python reference scenarios within agreed deltas.
2. Real-time Linux integration on AM62x with stable frame processing.
3. Measured latency/CPU budget compliance for MVP scope.
4. Regression outputs and metrics export reproducibility.

---

## 6) Phase 3 Entry Principle (Planned)

Phase 3 offload scope is enabled only after profiling shows measurable gain opportunity and IPC overhead is bounded.

Architecture decision references: `docs/ARCHITECTURE_TRACEABILITY.md`.
