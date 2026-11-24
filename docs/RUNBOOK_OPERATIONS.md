# ECNR Operations Runbook

**Last updated:** 2026-06-04  
**Purpose:** Single operational reference for running MATLAB Phase 1 and Python Phase 1D workflows.

---

## 1) MATLAB Operations (Phase 1A/B)

### Prerequisites
- MATLAB R2023b or compatible
- Base MATLAB + Signal Processing Toolbox

### 1.1 Generate deterministic test assets and baseline

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); freeze_phase1_baseline();"
```

Outputs:
- `scenarios/assets/phase1_mic.wav`
- `scenarios/assets/phase1_ref.wav`
- `metrics_baselines/phase1_offline_baseline.csv`

### 1.2 Run MATLAB regression suite

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); s = run_phase1_suite_from_workspace(); disp(s);"
```

Expected:
- `pass: 1`
- Refreshed `metrics_baselines/phase1_offline_current.csv`
- Generated `scenarios/results/phase1_offline_output.wav`

### 1.3 Launch MATLAB GUI

Option A - MATLAB command window:

```matlab
run('run_phase1_gui.m')
```

Option B - PowerShell interactive session:

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -r "run('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/run_phase1_gui.m')"
```

### 1.4 MATLAB smoke test

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); s = run_smoke_from_workspace(); disp(s.metrics);"
```

---

## 2) Python Operations (Phase 1D)

### Prerequisites

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2.1 List audio devices

```sh
python -m ecnr_python.rt_demo --list-devices
```

### 2.2 Real-time demo

```sh
python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json
python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json --gui
python -m ecnr_python.rt_demo --config configs/phase1_default.json --duration 120
python -m ecnr_python.rt_demo --latency-test
python -m ecnr_python.rt_demo --input-device "Microphone Array" --output-device "Speakers"
```

### 2.3 Offline runner and profiling

```sh
python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json
python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --loops 90
python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --profile
```

### 2.4 Regression suite

```sh
python -m ecnr_python.regression
python -m ecnr_python.regression scenarios/phase1_suite.json
```

Exit code convention:
- `0` = PASS
- `1` = FAIL

### 2.5 Smoke scripts

```sh
python test_simple.py
python test_audio_levels.py --device-in 1 --device-out 3
```

Notes:
- Device IDs vary by machine; use `--device-in` and `--device-out` for stable pairing.
- Console encoding/device handling fixes were completed in Phase 1D closeout.

---

## 3) Troubleshooting and Known Constraints

- Live MATLAB audio remains feasibility-gated in the Phase 1 baseline.
- Hybrid DL real-time in Python is deferred behind Phase 2 timing/model gates.
- For current measured CPU timing and C-port guidance, see `docs/PHASE2_HANDOFF.md`.

---

## 4) Related Canonical Documents

- Acceptance criteria and gates: `docs/ACCEPTANCE_CRITERIA.md`
- Program roadmap and decision trajectory: `docs/ROADMAP.md`
- Module implementation status by phase: `docs/MODULES_STATUS.md`
- Time-stamped integration snapshot: `docs/TASK_STATUS.md`
