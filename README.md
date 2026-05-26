# ECNR — Embedded Concurrent Noise Reduction

End-to-end noise reduction pipeline progressing from MATLAB offline prototype → Python PC real-time demo → C/C++ embedded on AM62x Linux.

---

## Phase roadmap

```
Phase 1A/B  MATLAB offline engine + GUI          Complete
Phase 1D    Python PC real-time demo             Complete (Sprints 0-4, 6 done; Sprint 5 Hybrid deferred)
Phase 2     C/C++ portable core on AM62x Linux   Pending Phase 1D exit gate
Phase 3     DSP/NPU offload on C7x              Pending Phase 2 exit gate
```

---

## Repository layout

```
ecnr_python/              Python PC real-time demo (Phase 1D)
  config/                 EcnrConfig dataclass + JSON loader
  dsp/                    DSP modules: beamformer, AEC, NR (traditional + hybrid stub)
  io/                     RT audio (sounddevice) + reference source abstraction
  metrics/                ERLE / SNR / DTD per-frame metrics + CSV export
  gui/                    Live spectrogram + metrics plots (pyqtgraph)
  engine.py               Frame dispatcher: BF -> AEC -> NR
  rt_demo.py              CLI entry point (real-time)
  offline_runner.py       Offline WAV runner + CPU profiler
  regression.py           Regression suite runner + baseline comparison

phase1_matlab/            Phase 1 MATLAB offline engine
  aec/                    NLMS AEC + DTD
  beamformer/             DAS beamformer
  nr/                     Traditional NR (Wiener / spectral subtraction)
  metrics/                ERLE, SNR, convergence
  io/                     WAV I/O + live callback stub
  regression/             Scenario runner + baseline freeze
  gui/                    App Designer GUI

configs/                  Shared JSON config files
scenarios/                Phase 1 scenario descriptors (JSON) + suite definitions
metrics_baselines/        Frozen baseline CSVs (MATLAB + Python)
docs/                     All design and planning documents
```

---

## Prerequisites

### Python RT demo
```
Python 3.10+
pip install -r requirements.txt
```

`requirements.txt` includes: `numpy`, `sounddevice`, `soundfile`, `pyqtgraph`, `PyQt5`

### Phase 1 MATLAB
- MATLAB R2023b (or compatible)
- Signal Processing Toolbox

---

## Python — quick start

### List available audio devices
```sh
python -m ecnr_python.rt_demo --list-devices
```

### Real-time demo (full pipeline: BF + AEC + NR)
```sh
python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json
```

### Real-time demo with live GUI
```sh
python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json --gui
```
Opens spectrogram, ERLE/SNR time series, DTD indicator, and WAV record button.

### Specify custom duration or config
```sh
python -m ecnr_python.rt_demo --config configs/phase1_default.json --duration 120
```

### Acoustic round-trip latency measurement
```sh
python -m ecnr_python.rt_demo --latency-test
```
Requires speaker output looped back to mic input. Reports both sounddevice-reported and acoustic round-trip latency.

### Select specific audio devices
```sh
python -m ecnr_python.rt_demo --input-device "Microphone Array" --output-device "Speakers"
```

### CPU profiling (per-module timing)
```sh
python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json --profile
```
Or offline:
```sh
python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --profile
```
Reports mean and p99 processing time per DSP module against the frame budget.

### Offline stability / regression run (no audio device needed)
```sh
python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json
python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --loops 90
```
`--loops 90` processes 90x the WAV length (~30 minutes of audio equivalent).

### Run regression suite
```sh
python -m ecnr_python.regression
python -m ecnr_python.regression scenarios/phase1_suite.json
```
Exit code 0 = PASS, 1 = FAIL. Compares:
- ERLE vs frozen MATLAB baseline (tolerance ±2 dB)
- SNR-out vs frozen Python baseline (tolerance ±1 dB, self-consistency)

---

## MATLAB — quick reference

See [docs/PHASE1_RUNBOOK.md](docs/PHASE1_RUNBOOK.md) for full steps.

### Generate test assets and freeze baseline
```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch `
  "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); freeze_phase1_baseline();"
```

### Run regression suite
```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch `
  "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); s = run_phase1_suite_from_workspace(); disp(s);"
```

### Launch GUI
```powershell
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -r `
  "run('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/run_phase1_gui.m')"
```
Or from the MATLAB command window: `run('run_phase1_gui.m')`

---

## Configuration

All behaviour is driven by JSON config files in `configs/`. Example:

```json
{
  "sample_rate_hz": 16000,
  "mic_count": 2,
  "frame": { "length_samples": 320 },
  "beamformer": { "enabled": true, "algorithm": "das" },
  "aec":  { "enabled": true, "filter_length": 128, "step_size": 0.1 },
  "nr":   { "enabled": true, "algorithm": "traditional", "aggressiveness_db": 8 },
  "reference": { "source_type": "file" }
}
```

Scenarios in `scenarios/` extend a config with WAV file paths for offline use.

**Hot-updateable at runtime** (no restart needed): `aec.step_size`, `aec.double_talk_threshold_db`, `nr.aggressiveness_db`, `nr.noise_smooth_alpha`

**Restart required**: `sampling_rate`, `frame_size`, `mic_count`, `aec.filter_length`

---

## Documentation

| Document | Description |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements, phase gates, success metrics |
| [docs/SRS.md](docs/SRS.md) | System requirements, module interfaces |
| [docs/HLD.md](docs/HLD.md) | High-level architecture and design decisions |
| [docs/LLD.md](docs/LLD.md) | Low-level module specifications and pseudocode |
| [docs/ARCHITECTURE_DIAGRAMS.md](docs/ARCHITECTURE_DIAGRAMS.md) | Mermaid architecture + flowchart diagrams |
| [docs/ARCHITECTURE_TRACEABILITY.md](docs/ARCHITECTURE_TRACEABILITY.md) | PRD -> SRS -> HLD -> LLD traceability matrix |
| [docs/PHASE1_RUNBOOK.md](docs/PHASE1_RUNBOOK.md) | Step-by-step runbook for Phase 1 MATLAB |
| [docs/SPECTROGRAM_FEATURE.md](docs/SPECTROGRAM_FEATURE.md) | Spectrogram visualisation feature notes (MATLAB GUI) |
| [docs/PLAN_IMPLEMENTATION.md](docs/PLAN_IMPLEMENTATION.md) | Overall implementation roadmap with current status |
| [docs/PLAN_PC_RT_PYTHON.md](docs/PLAN_PC_RT_PYTHON.md) | Sprint-by-sprint plan for Python PC RT demo |
| [docs/PHASE2_HANDOFF.md](docs/PHASE2_HANDOFF.md) | Phase 2 handoff notes: NumPy->C mapping, time budgets, parity targets |
