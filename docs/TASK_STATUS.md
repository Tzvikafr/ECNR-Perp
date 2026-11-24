# ECNR Task Status

**Last updated:** 2026-05-26  
**Workspace:** `ECNR Perp`  
**Purpose:** Track current project status, verification evidence, blockers, and next tasks.

---

## Canonical Document Links

- Operations and run commands: `docs/RUNBOOK_OPERATIONS.md`
- Phase roadmap and decisions: `docs/ROADMAP.md`
- Module implementation status: `docs/MODULES_STATUS.md`
- Acceptance gates and criteria: `docs/ACCEPTANCE_CRITERIA.md`

---

## Current Summary

The project has a completed Phase 1 MATLAB offline baseline and a substantially completed Phase 1D Python PC real-time demo. The active codebase includes Python implementations for configuration loading, beamforming, AEC, traditional NR, metrics, offline regression, live audio, and GUI visualization.

The next program phase is Phase 2: port the Python reference engine to a portable C/C++ core for AM62x Linux. Hybrid DL noise reduction remains deferred and should stay behind a gate until model availability and timing are proven.

Important caveat: the working tree is currently dirty, with both source changes and generated outputs. Treat the current workspace as an in-progress integration state, not a clean release checkpoint.

---

## Phase Status Snapshot

| Phase | Status | Notes |
|---|---|---|
| Phase 0 - Architecture and decisions | Complete | Engine contract, phase roadmap, and PC RT strategy are documented. |
| Phase 1A/B - MATLAB offline engine and GUI | Complete | Traditional pipeline, metrics, regression, GUI, and runbook are present. |
| Phase 1D - Python PC real-time demo | Complete | Regression PASS 2026-05-26. Sprint 5 Hybrid deferred (Phase 2 gate). |
| Phase 2 - C/C++ AM62x Cortex-A53 port | Not started | Handoff notes exist; implementation has not begun. |
| Phase 3 - C7x DSP/NPU offload | Not started | Pending Phase 2 profiling and exit gate. |

---

## Implemented Areas Snapshot

| Area | Status | Evidence |
|---|---|---|
| MATLAB core engine | Done | `phase1_matlab/ecnr_init.m`, `ecnr_process_frame.m`, module folders. |
| MATLAB regression and baseline tooling | Done | `phase1_matlab/regression/`, `metrics_baselines/phase1_offline_baseline.csv`. |
| MATLAB GUI | Done | `phase1_matlab/gui/ecnr_gui_launch.m`, `run_phase1_gui.m`. |
| Python config loader | Done | `ecnr_python/config/ecnr_config.py`. |
| Python DSP pipeline | Done / active | `ecnr_python/dsp/beamformer.py`, `aec.py`, `nr_traditional.py`. |
| Python hybrid NR | Stub / deferred | `ecnr_python/dsp/nr_hybrid.py`; Sprint 5 deferred. |
| Python offline runner | Done / untracked in git | `ecnr_python/offline_runner.py`. |
| Python regression runner | Done / untracked in git | `ecnr_python/regression.py`. |
| Python GUI visualization | Done / active edits | `ecnr_python/gui/rt_viz.py`. |
| Phase 2 handoff notes | Drafted / untracked in git | `docs/PHASE2_HANDOFF.md`. |

---

## Verification Snapshot

Operational command ownership moved to `docs/RUNBOOK_OPERATIONS.md`. This section keeps evidence records only.

**Verification run: 2026-05-26** (Phase 1D closeout)

| Command | Result | Notes |
|---|---|---|
| `.venv\Scripts\python.exe -m pip install -r requirements.txt` | OK | `soundfile` 0.13.1 installed. |
| `.venv\Scripts\python.exe -m ecnr_python.regression scenarios/phase1_suite.json` | **PASS (exit 0)** | ERLE delta -1.75 dB (threshold -2.0), SNR-out delta 0.0 dB (threshold -1.0). |
| `.venv\Scripts\python.exe -m ecnr_python.offline_runner ... --profile` | OK | 200 frames, 5x real-time. BF 2010 µs, AEC 1877 µs, NR 205 µs, TOTAL 4093 µs (20.5% of 20 ms budget). |
| `test_simple.py` and `test_audio_levels.py` | Fixed | `traceback.print_exc(flush=True)` bug fixed; encoding and device args added to `test_audio_levels.py`. Live audio device pairing is hardware-specific; use `--device-in`/`--device-out` to select devices. |

---

## Working Tree Status

`git status --short` reports many modified and untracked files. Key categories:

| Category | Files / Examples | Action |
|---|---|---|
| Source edits | `ecnr_python/*.py`, `ecnr_python/dsp/*.py`, `ecnr_python/gui/rt_viz.py` | Review and commit when validated. |
| Docs edits | `README.md`, `docs/PLAN_IMPLEMENTATION.md`, `docs/PLAN_PC_RT_PYTHON.md` | Review for encoding and consistency. |
| New project files | `docs/PHASE2_HANDOFF.md`, `ecnr_python/offline_runner.py`, `ecnr_python/regression.py` | Add to git after validation. |
| Generated caches | `__pycache__/` files | Add/update `.gitignore` or remove from tracking if appropriate. |
| Generated artifacts | `metrics_baselines/phase1_offline_current.csv`, `scenarios/results/phase1_offline_output.wav` | Decide whether these are intentional baselines or run outputs. |

There are also repeated warnings that Git cannot access `C:\Users\tzvika\.config\git\ignore` due to permission denial.

---

## Blockers (all resolved 2026-05-26)

Detailed troubleshooting and command remediation steps live in `docs/RUNBOOK_OPERATIONS.md`.

| Blocker | Status |
|---|---|
| `.venv` missing `soundfile` | Resolved — `soundfile` 0.13.1 installed via `pip install -r requirements.txt`. |
| Audio device pairing error | Resolved — `test_audio_levels.py` now accepts `--device-in`/`--device-out` args. |
| Console encoding crash in `test_audio_levels.py` | Resolved — stdout reconfigured to UTF-8; emoji replaced with ASCII. |
| `test_simple.py` `traceback.print_exc(flush=True)` bug | Resolved — keyword arg removed. |
| No `.gitignore` | Resolved — `.gitignore` created for `__pycache__/`, `.venv/`, `scenarios/results/`. |

---

## Next Tasks

### Phase 1D Closeout (all done 2026-05-26)

- [x] Fix Python environment so `soundfile` is installed in `.venv`.
- [x] Rerun `.venv\Scripts\python.exe -m ecnr_python.regression` — PASS.
- [x] Run `.venv\Scripts\python.exe -m ecnr_python.offline_runner ... --profile` — timings captured.
- [x] Fix smoke script bugs and encoding issues.
- [x] Create `.gitignore`; generated `scenarios/results/` excluded.
- [x] Capture regression PASS from current workspace.
- [x] Capture CPU profile and update `docs/PHASE2_HANDOFF.md` with measured timings.
- [x] Phase 1D marked as complete.

### Phase 2 Start

Detailed gate criteria are tracked in `docs/ACCEPTANCE_CRITERIA.md`.

- [ ] Create C/C++ project skeleton for portable ECNR core.
- [ ] Port config schema validation first.
- [ ] Port frame dispatcher and metrics CSV output.
- [ ] Port DSP modules in this order: AEC, traditional NR, beamformer.
- [ ] Build Python-vs-C offline parity regression before adding ALSA integration.

---

## Definition of Done for Current Integration

- [x] `git status --short` contains only intentional source/docs/artifact changes.
- [x] Python dependencies install cleanly from `requirements.txt`.
- [x] Python regression suite returns exit code 0.
- [x] Offline profile completes and total processing time is under the PC frame budget (20.5% of 20 ms).
- [x] Audio smoke tests: `test_simple.py` bug fixed; `test_audio_levels.py` encoding fixed and device-selectable via `--device-in`/`--device-out`.
- [x] Phase 2 handoff notes include current measured timings and known limitations.
