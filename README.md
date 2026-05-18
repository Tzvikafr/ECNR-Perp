# ECNR — Embedded Concurrent Noise Reduction

End-to-end noise reduction pipeline progressing from MATLAB offline prototype → Python PC real-time demo → C/C++ embedded on AM62x Linux.

---

## Repository layout

```
ecnr_python/          Python PC real-time demo (Phase 1D)
  config/             EcnrConfig dataclass + JSON loader
  dsp/                DSP modules: beamformer, AEC, NR (traditional + hybrid)
  io/                 RT audio (sounddevice) + reference source abstraction
  metrics/            ERLE / SNR / DTD metrics
  gui/                Live spectrogram + metrics plots (Sprint 4)
  engine.py           Frame dispatcher: BF → AEC → NR
  rt_demo.py          CLI entry point

phase1_matlab/        Phase 1 MATLAB offline engine
  aec/                NLMS AEC + DTD
  beamformer/         DAS beamformer
  nr/                 Traditional NR (Wiener / spectral subtraction)
  metrics/            ERLE, SNR, convergence
  io/                 WAV I/O + live callback
  regression/         Scenario runner + baseline freeze
  gui/                App Designer GUI

configs/              Shared JSON config files
scenarios/            Phase 1 scenario descriptors (JSON)
metrics_baselines/    Frozen MATLAB baseline CSVs
docs/                 All design and planning documents
```

---

## Prerequisites

### Python RT demo
```
Python 3.10+
pip install sounddevice numpy
```
Sprint 4 GUI additionally requires:
```
pip install pyqtgraph PyQt5
```
Or install everything at once:
```
pip install -r requirements.txt
```

### Phase 1 MATLAB
- MATLAB R2023b (or compatible)
- Signal Processing Toolbox

---

## Running the Python RT demo

### List available audio devices
```sh
python -m ecnr_python.rt_demo --list-devices
```

### 60-second passthrough (mic → speaker, no DSP)
```sh
python -m ecnr_python.rt_demo
```
Loads `scenarios/phase1_offline_wav.json` → `configs/phase1_default.json` by default.

### Custom config or duration
```sh
python -m ecnr_python.rt_demo --config configs/phase1_default.json --duration 120
```

### Load a Phase 1 scenario directly
```sh
python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json
```

### Acoustic round-trip latency measurement
Requires the speaker output to be looped back into the mic (physically or electrically).
```sh
python -m ecnr_python.rt_demo --latency-test
```
The stream always prints sounddevice-reported input + output latency at startup.
The `--latency-test` flag additionally injects a click and measures the acoustic round-trip.

### Select specific audio devices
```sh
python -m ecnr_python.rt_demo --input-device "Microphone Array" --output-device "Speakers"
```

---

## Running the Phase 1 MATLAB pipeline

See [docs/PHASE1_RUNBOOK.md](docs/PHASE1_RUNBOOK.md) for full steps. Quick reference:

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
& "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -batch `
  "cd('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp'); addpath(genpath('phase1_matlab')); ecnr_gui_launch();"
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements, phase gates, success metrics |
| [docs/SRS.md](docs/SRS.md) | System requirements, module interfaces |
| [docs/HLD.md](docs/HLD.md) | High-level architecture and design decisions |
| [docs/LLD.md](docs/LLD.md) | Low-level module specifications and pseudocode |
| [docs/ARCHITECTURE_TRACEABILITY.md](docs/ARCHITECTURE_TRACEABILITY.md) | PRD → SRS → HLD → LLD traceability matrix |
| [docs/PHASE1_RUNBOOK.md](docs/PHASE1_RUNBOOK.md) | Step-by-step runbook for Phase 1 MATLAB |
| [docs/SPECTROGRAM_FEATURE.md](docs/SPECTROGRAM_FEATURE.md) | Spectrogram visualisation feature notes |
| [docs/PLAN_IMPLEMENTATION.md](docs/PLAN_IMPLEMENTATION.md) | Overall implementation roadmap (all phases) |
| [docs/PLAN_PC_RT_PYTHON.md](docs/PLAN_PC_RT_PYTHON.md) | Sprint-by-sprint plan for Python PC RT demo |

---

## Phase roadmap

```
Phase 1A/B  MATLAB offline engine + GUI          ✅ Complete
Phase 1D    Python PC real-time demo             🔄 Sprint 0 complete (passthrough)
Phase 2     C/C++ portable core on AM62x Linux   ⏳ Pending Phase 1D exit gate
Phase 3     DSP/NPU offload on C7x              ⏳ Pending Phase 2 exit gate
```
