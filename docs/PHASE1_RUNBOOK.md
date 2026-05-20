# Phase 1 MATLAB Traditional Runbook

This runbook describes the completed Phase 1 baseline implementation:
- Traditional ECNR pipeline in MATLAB
- Offline WAV scenario execution
- Regression suite with baseline comparison
- MATLAB GUI for tuning and visualization

## Prerequisites
- MATLAB R2023b or compatible
- Base MATLAB + Signal Processing Toolbox

## 1) Generate deterministic test assets and baseline
Run from workspace root:

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); freeze_phase1_baseline();"
```

Outputs:
- `scenarios/assets/phase1_mic.wav`
- `scenarios/assets/phase1_ref.wav`
- `metrics_baselines/phase1_offline_baseline.csv`

## 2) Run the Phase 1 regression suite

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); s = run_phase1_suite_from_workspace(); disp(s);"
```

Expected:
- `pass: 1`
- metrics CSV refreshed at `metrics_baselines/phase1_offline_current.csv`
- output WAV at `scenarios/results/phase1_offline_output.wav`

## 3) Launch GUI

### Option A — From MATLAB command window (workspace root)
```matlab
run('run_phase1_gui.m')
```
Or equivalently:
```matlab
addpath(genpath('phase1_matlab'));
ecnr_gui_launch();
```

### Option B — From PowerShell (opens interactive MATLAB session)
> Note: use `-r` (not `-batch`) — GUI requires an interactive MATLAB session with a display.

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -r "run('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/run_phase1_gui.m')"
```

### Script: `run_phase1_gui.m`
Located at the repository root. Sets the working directory, adds `phase1_matlab` to path, then calls `ecnr_gui_launch()`. Safe to run from any MATLAB working directory.

### GUI capabilities
| Panel | Controls |
|---|---|
| **Input** | Mode: Scenario JSON or Direct WAV; file pickers for scenario, base config, mic WAV, ref WAV, output WAV, metrics CSV |
| **Modules** | Beamformer (Off / DAS), AEC (Bypass / NLMS), NR (Bypass / Traditional / Hybrid placeholder), Reference source |
| **Tuning** | All Phase 1 parameters; Reinitialize button for restart-required changes |
| **Metrics** | ERLE inst/window, SNR in/out, DTD, convergence time; run history table |
| **Plots** | Waveform before/after, ERLE trend, SNR+DTD timeline |
| **Spectrograms** | With algorithm, modules-off reference, and dB-difference panels |
| **Audio** | Play before/after ECNR, mic WAV, ref WAV, output WAV; Stop button |

### Restart-required controls (click **Reinitialize** before next run)
- Sample rate, frame size, mic count
- AEC filter length, ERLE window frames
- Algorithm selections (BF / AEC / NR)

### Hot-update controls (take effect on next run immediately)
- Module enable flags
- Reference delay, AEC step size, AEC regularization, DTD threshold
- NR aggressiveness

## 4) Smoke test

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); s = run_smoke_from_workspace(); disp(s.metrics);"
```

## Notes
- Live device I/O remains feasibility-gated for Phase 1 in this baseline and is intentionally stubbed.
- Baseline comparison thresholds are defined in `scenarios/phase1_suite.json`.
