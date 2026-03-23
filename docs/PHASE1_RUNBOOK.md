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
In MATLAB command window (workspace root):

```matlab
addpath(genpath('phase1_matlab'));
ecnr_gui_launch();
```

GUI capabilities:
- Input mode selection: Scenario JSON or Direct WAV
- File pickers for scenario, base config, mic WAV, reference WAV, output WAV, and metrics CSV
- Module enable and algorithm selection:
	- Beamformer: Off / DAS
	- AEC: Bypass / NLMS
	- NR: Bypass / Traditional / Hybrid placeholder
- Tuning controls for current Phase 1 parameters
- Explicit `Reinitialize` flow for restart-required controls
- Metrics panel, summary table, run history, waveform plot, ERLE trend, SNR/DTD trend
- CSV export for the latest run

Restart-required controls:
- sample rate
- frame size
- mic count
- AEC filter length
- ERLE window frames
- algorithm selections

Hot-update controls:
- module enable flags
- reference delay
- AEC step size
- AEC regularization
- DTD threshold
- NR aggressiveness

## 4) Smoke test

```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); s = run_smoke_from_workspace(); disp(s.metrics);"
```

## Notes
- Live device I/O remains feasibility-gated for Phase 1 in this baseline and is intentionally stubbed.
- Baseline comparison thresholds are defined in `scenarios/phase1_suite.json`.
