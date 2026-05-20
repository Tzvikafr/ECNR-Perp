# ECNR Architecture Diagrams

**Version:** 1.0 | **Date:** May 2026 | **Status:** Active

All diagrams use [Mermaid](https://mermaid.js.org/) syntax, rendered natively on GitHub and in VS Code with the Mermaid Preview extension.

---

## 1. System Architecture Overview — Three-Phase Deployment

```mermaid
graph TB
    subgraph P1["Phase 1 — PC Prototype"]
        direction TB
        P1A["Phase 1A/B\nMATLAB Offline Engine\n• Batch WAV processing\n• GUI tuning (App Designer)\n• Regression suite"]
        P1D["Phase 1D\nPython Real-Time Demo\n• sounddevice duplex stream\n• Sprint-gated DSP modules\n• Live metrics & visualization"]
        P1A -->|Freeze baseline CSVs\nValidated algorithms| P1D
    end

    subgraph P2["Phase 2 — Embedded MVP (TI AM62x)"]
        direction TB
        P2A["Cortex-A53 Linux\nC/C++ ECNR Pipeline\n• ALSA I/O\n• Portable DSP core\n• gRPC control interface"]
    end

    subgraph P3["Phase 3 — DSP Offload"]
        direction TB
        P3A["C7x TI DSP\nAccelerated NR/BF\n• CMSIS-DSP / TI DSPLIB\n• RPMsg IPC to A53\n• Fixed-point kernels"]
        P3B["Cortex-A53 Linux\nI/O Host + AEC\n• Sends frames via IPC\n• Collects results + metrics"]
        P3A <-->|RPMsg IPC| P3B
    end

    P1D -->|Port DSP logic to C\nValidate vs. MATLAB baseline| P2A
    P2A -->|Split: A53 hosts I/O+AEC\nOffload NR+BF to C7x| P3A
    P2A --> P3B

    style P1 fill:#e8f4fd,stroke:#2196F3
    style P2 fill:#e8f5e9,stroke:#4CAF50
    style P3 fill:#fff3e0,stroke:#FF9800
```

---

## 2. Real-Time Audio Processing Pipeline

```mermaid
flowchart LR
    MIC["🎤 Microphone Array\n(1, 2, or 4 ch)\n16 kHz / 48 kHz"]
    REF["📢 Reference Source\n(file / loopback /\ncapture channel)"]

    subgraph STREAM["RtAudio — sounddevice Duplex Stream"]
        CB["Frame Callback\nframe_size samples\n(e.g. 320 @ 16 kHz = 20 ms)"]
    end

    subgraph ENGINE["EcnrEngine.process_frame()"]
        BF["Beamformer\nDelay-and-Sum\n(N,M) → (N,)"]
        AEC["AEC\nNLMS adaptive filter\n+ DTD"]
        NR["Noise Reduction\nTraditional: Wiener / Spectral Sub\nHybrid: DL Complex Ratio Mask"]
        BF --> AEC --> NR
    end

    subgraph METRICS["Metrics Thread (non-blocking)"]
        M["Per-frame\nERLE · SNR · DTD flag"]
        CSV["CSV export"]
        GUI_M["GUI gauges\n(Sprint 4)"]
        M --> CSV
        M --> GUI_M
    end

    SPK["🔊 Speaker Output\nEnhanced speech\n(frame_size, 1)"]

    MIC --> CB
    REF --> CB
    CB --> ENGINE
    ENGINE --> SPK
    ENGINE --> METRICS
```

---

## 3. Python Module Architecture

```mermaid
graph TD
    CLI["rt_demo.py\n(CLI Entry Point)"]

    subgraph CONFIG["config/"]
        CFG["ecnr_config.py\nEcnrConfig dataclass\nload_config()\nload_scenario_config()"]
    end

    subgraph IO["io/"]
        RTA["rt_audio.py\nRtAudio\nstart() / stop()\nmeasure_latency()"]
        REFSRC["reference.py\nReferenceSource\n(file / loopback / capture)"]
    end

    subgraph DSP["dsp/"]
        BFM["beamformer.py\nBeamformer\nDAS algorithm"]
        AECM["aec.py\nAEC\nNLMS + DTD"]
        NRT["nr_traditional.py\nNrTraditional\nSTFT + Wiener filter\n50% OLA"]
        NRH["nr_hybrid.py\nNrHybrid\nDL model wrapper\nComplex Ratio Mask"]
    end

    subgraph METRICS["metrics/"]
        MET["metrics.py\nMetrics\nERLE / SNR / DTD"]
    end

    subgraph GUI["gui/"]
        VIZ["rt_viz.py\nRtViz\nLive spectrogram\nMetrics gauges"]
    end

    ENG["engine.py\nEcnrEngine\nprocess_frame()"]

    CLI --> CFG
    CLI --> RTA
    CLI --> ENG
    CFG --> ENG
    REFSRC --> ENG
    ENG --> BFM
    ENG --> AECM
    ENG --> NRT
    ENG --> NRH
    ENG --> MET
    MET --> VIZ
    VIZ --> CLI

    style DSP fill:#fff9c4,stroke:#F9A825
    style IO fill:#e1f5fe,stroke:#0288D1
    style CONFIG fill:#f3e5f5,stroke:#7B1FA2
    style METRICS fill:#e8f5e9,stroke:#388E3C
    style GUI fill:#fce4ec,stroke:#C62828
```

---

## 4. MATLAB Reference Engine Architecture

```mermaid
graph TD
    subgraph MATLAB_GUI["GUI (App Designer)"]
        GUI2["run_phase1_gui.m\nStart / Stop / Tune"]
    end

    subgraph MATLAB_IO["io/"]
        WAV_R["io_wav_read.m\nRead + resample WAV"]
        WAV_W["io_wav_write.m\nWrite output WAV"]
        REFRES["io_reference_resolve.m\nRoute reference signal"]
        LIVE["io_live_init.m\nLive audio adapter"]
    end

    subgraph MATLAB_CORE["Core Engine"]
        INIT["ecnr_init.m\nInitialize pipeline state"]
        PROC["ecnr_process_frame.m\nMain frame dispatcher"]
        GETM["ecnr_get_metrics.m\nExtract per-frame metrics"]
        LOADC["ecnr_load_config.m\nParse JSON config"]
    end

    subgraph MATLAB_BF["beamformer/"]
        BFI["bf_init.m\nDAS setup (weights 1/M)"]
        BFP["bf_process.m\nWeighted sum across mics"]
    end

    subgraph MATLAB_AEC["aec/"]
        AECI["aec_init.m\nNLMS state + DTD history"]
        AECP["aec_process.m\nNLMS update + ERLE"]
        DTD["dtd_compute.m\nPower ratio check"]
    end

    subgraph MATLAB_NR["nr/"]
        NRI["nr_trad_init.m\nSTFT buffers + Hann window"]
        NRP["nr_trad_process.m\nTwo 50%-OLA segments\nFFT → Wiener → IFFT → OLA"]
    end

    subgraph MATLAB_MET["metrics/"]
        METI["metrics_init.m"]
        METU["metrics_update.m\nERLE / SNR / DTD"]
        METE["metrics_export_csv.m"]
    end

    subgraph MATLAB_REG["regression/"]
        RS["run_scenario.m"]
        RSuite["run_phase1_suite_from_workspace.m"]
        Freeze["freeze_phase1_baseline.m"]
    end

    GUI2 --> INIT
    LOADC --> INIT
    WAV_R --> INIT
    REFRES --> INIT
    INIT --> PROC
    PROC --> BFI
    PROC --> AECI
    PROC --> NRI
    BFP --> PROC
    AECP --> PROC
    NRP --> PROC
    DTD --> AECP
    PROC --> GETM
    GETM --> METU
    METU --> METE
    METE --> WAV_W
    RS --> RSuite
    RSuite --> Freeze

    style MATLAB_CORE fill:#e3f2fd,stroke:#1565C0
    style MATLAB_AEC fill:#fce4ec,stroke:#AD1457
    style MATLAB_NR fill:#fff9c4,stroke:#F57F17
    style MATLAB_BF fill:#e8eaf6,stroke:#3949AB
    style MATLAB_MET fill:#e8f5e9,stroke:#2E7D32
    style MATLAB_REG fill:#f3e5f5,stroke:#6A1B9A
```

---

## 5. AEC — NLMS Frame Processing Flowchart

```mermaid
flowchart TD
    START(["Frame In\nmic_signal (N,)\nref_signal (N,)"])

    DTD_CHECK{"DTD Check\nP_mic / P_ref\n> threshold?"}
    FREEZE["Freeze NLMS weights\n(double-talk detected)"]
    UPDATE["NLMS weight update\nw ← w + (μ / ‖x‖²) · e(n) · x_hist"]

    ERLE_CALC["Compute ERLE\n10·log10(P_mic / P_res)\nrolling 25-frame window"]

    OUT(["Frame Out\nresidual (N,)\nDTD flag\nERLE dB"])

    START --> DTD_CHECK
    DTD_CHECK -- Yes: double-talk --> FREEZE
    DTD_CHECK -- No: single-talk --> UPDATE
    FREEZE --> ERLE_CALC
    UPDATE --> ERLE_CALC
    ERLE_CALC --> OUT
```

---

## 6. Traditional NR — STFT / OLA Processing Flowchart

```mermaid
flowchart TD
    START(["Frame In (N samples)\naec_residual"])

    SEG["Split into 2 × 50%-OLA segments\n(each N/2 samples)"]

    subgraph OLA_LOOP["For each segment"]
        WIN["Apply Hann window"]
        FFT["FFT → X[k]"]
        NOISE["Noise PSD estimate\nα·Ψ_old + (1−α)·|X[k]|² (gated)"]
        SNR_POST["Post-SNR per bin\nSNR[k] = |X[k]|² / Ψ[k] − 1"]
        GAIN["Wiener gain\nG[k] = max(floor, 1 − λ/(SNR[k]+1))\nλ = 1 + (agg_dB/24)·1.5"]
        APPLY["Apply gain: Y[k] = G[k]·X[k]"]
        IFFT["IFFT → y_seg"]
        OLA_ADD["Overlap-add to output buffer"]
        WIN --> FFT --> NOISE --> SNR_POST --> GAIN --> APPLY --> IFFT --> OLA_ADD
    end

    SEG --> OLA_LOOP
    OLA_LOOP --> OUT(["Frame Out (N samples)\nenhanced_signal"])
```

---

## 7. Configuration & Scenario Loading Flow

```mermaid
flowchart TD
    CLI2(["rt_demo.py\nCLI args"])

    ARGS{"--scenario\nprovided?"}

    LOAD_SCEN["load_scenario_config()\nParse scenario JSON\n→ config path + WAV paths"]
    LOAD_CFG["load_config()\nParse config JSON\n→ EcnrConfig dataclass"]

    VALIDATE{"Validate:\n• sample_rate ∈ {16k, 48k}\n• mic_count ∈ {1,2,4}\n• frame_size 128–512\n• aec.filter_length 64–1024\n• step_size 0.001–1.0\n• agg_dB 0–24"}

    ERR(["ValueError\n(invalid config)"])

    AUTO_DISABLE["Auto-disable beamformer\nif mic_count == 1"]

    INIT_ENG["EcnrEngine.__init__()\nInstantiate DSP modules\nbased on config flags"]

    INIT_IO["RtAudio.start()\nOpen duplex stream\nRegister frame callback"]

    INIT_REF["ReferenceSource\nOpen file / loopback / capture\nApply delay compensation"]

    RUN(["Real-time loop running"])

    CLI2 --> ARGS
    ARGS -- Yes --> LOAD_SCEN --> LOAD_CFG
    ARGS -- No --> LOAD_CFG
    LOAD_CFG --> VALIDATE
    VALIDATE -- Invalid --> ERR
    VALIDATE -- Valid --> AUTO_DISABLE --> INIT_ENG
    INIT_ENG --> INIT_IO
    INIT_ENG --> INIT_REF
    INIT_IO --> RUN
    INIT_REF --> RUN
```

---

## 8. Phase 3 — Embedded IPC Architecture (Future)

```mermaid
graph LR
    subgraph A53["Cortex-A53 (Linux)"]
        ALSA["ALSA Driver\nI/O"]
        AEC_C["AEC Module\n(C, NLMS)"]
        IPC_TX["RPMsg TX\nFrame → C7x"]
        IPC_RX["RPMsg RX\nResult ← C7x"]
        METRICS_C["Metrics Logger\n(gRPC / CSV)"]
        ALSA --> AEC_C --> IPC_TX
        IPC_RX --> ALSA
        IPC_RX --> METRICS_C
    end

    subgraph C7X["C7x DSP (RTOS)"]
        IPC_C7_RX["RPMsg RX"]
        BF_DSP["Beamformer\n(DSPLIB / CMSIS)"]
        NR_DSP["Noise Reduction\n(Fixed-point STFT)"]
        IPC_C7_TX["RPMsg TX"]
        IPC_C7_RX --> BF_DSP --> NR_DSP --> IPC_C7_TX
    end

    IPC_TX <-->|RPMsg IPC\n~1 ms round-trip| IPC_C7_RX
    IPC_C7_TX --> IPC_RX

    style A53 fill:#e3f2fd,stroke:#1565C0
    style C7X fill:#fff3e0,stroke:#E65100
```
