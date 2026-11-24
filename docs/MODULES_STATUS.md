# ECNR Module Status

**Last updated:** 2026-06-04  
**Purpose:** Canonical module implementation status across MATLAB and Python phases.

---

## MATLAB Phase 1A/B

| Module Area | Status | Evidence |
|---|---|---|
| Config loader | Done | `phase1_matlab/ecnr_load_config.m` |
| Engine lifecycle and frame dispatcher | Done | `phase1_matlab/ecnr_init.m`, `phase1_matlab/ecnr_process_frame.m` |
| Beamformer (DAS) | Done | `phase1_matlab/beamformer/bf_init.m`, `phase1_matlab/beamformer/bf_process.m` |
| AEC (NLMS + DTD) | Done | `phase1_matlab/aec/aec_init.m`, `phase1_matlab/aec/aec_process.m`, `phase1_matlab/aec/dtd_compute.m` |
| Traditional NR | Done | `phase1_matlab/nr/nr_trad_init.m`, `phase1_matlab/nr/nr_trad_process.m` |
| Metrics | Done | `phase1_matlab/metrics/metrics_init.m`, `phase1_matlab/metrics/metrics_update.m` |
| Regression and baseline tooling | Done | `phase1_matlab/regression/` |
| GUI | Done | `phase1_matlab/gui/ecnr_gui_launch.m`, `run_phase1_gui.m` |
| Live I/O adapter | Feasibility-gated | `phase1_matlab/io/io_live_init.m`, `phase1_matlab/io/io_live_callback.m` |

---

## Python Phase 1D

| Module Area | Status | Evidence |
|---|---|---|
| Config loader | Done | `ecnr_python/config/ecnr_config.py` |
| Engine dispatcher | Done | `ecnr_python/engine.py` |
| Beamformer | Done | `ecnr_python/dsp/beamformer.py` |
| AEC | Done | `ecnr_python/dsp/aec.py` |
| Traditional NR | Done | `ecnr_python/dsp/nr_traditional.py` |
| Hybrid NR | Stub / deferred | `ecnr_python/dsp/nr_hybrid.py` |
| Real-time I/O | Done | `ecnr_python/io/rt_audio.py`, `ecnr_python/io/reference.py` |
| Metrics | Done | `ecnr_python/metrics/metrics.py` |
| Visualization GUI | Done | `ecnr_python/gui/rt_viz.py` |
| Offline runner | Done | `ecnr_python/offline_runner.py` |
| Regression runner | Done | `ecnr_python/regression.py` |

---

## Next Ownership Boundary

- Phase 2 implementation details and current constraints: `docs/PHASE2_HANDOFF.md`
- Program-level sequencing: `docs/ROADMAP.md`
- Run/verify commands: `docs/RUNBOOK_OPERATIONS.md`
- Integration snapshot and timestamps: `docs/TASK_STATUS.md`
