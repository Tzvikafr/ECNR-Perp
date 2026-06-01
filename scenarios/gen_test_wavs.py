"""Generate WAV test pairs for ECNR algorithm validation.

Uses AI-generated speech assets when present and builds scenario pairs
(mic + ref WAV) and matching scenario JSON files. Cases include:
speech-only, echo/single-talk, DTD overlap variants, noise stress,
silence guards, AEC convergence, and high-SNR speech.

Usage:
    python scenarios/gen_test_wavs.py
    python scenarios/gen_test_wavs.py --duration 9

All outputs go to:
    scenarios/assets/  (WAV files)
    scenarios/         (scenario JSON files)
    scenarios/ecnr_test_suite.json  (master suite)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 16_000          # sample rate Hz
FRAME = 320          # samples per frame (20 ms)
DURATION = 9.0       # default duration in seconds
ECHO_DELAY = 32      # samples (2 ms)
ECHO_ATT_DB = -25    # echo attenuation relative to reference
SILENCE_HEAD_S = 2.0
SILENCE_TAIL_S = 2.0

AI_SPEECH_FILES = [
    "ai_speech_01.wav",
    "ai_speech_02.wav",
    "ai_speech_03.wav",
]


# ---------------------------------------------------------------------------
# Signal synthesis helpers
# ---------------------------------------------------------------------------

def _fir_bandpass(low_hz: float, high_hz: float, num_taps: int = 255) -> np.ndarray:
    """Windowed-sinc FIR bandpass filter (pure numpy)."""
    n = np.arange(num_taps) - (num_taps - 1) / 2
    wl = 2 * np.pi * low_hz / SR
    wh = 2 * np.pi * high_hz / SR
    # avoid divide-by-zero at center tap; patch it afterwards
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(n == 0,
                     (wh - wl) / np.pi,
                     (np.sin(wh * n) - np.sin(wl * n)) / (np.pi * n))
    h = np.nan_to_num(h, nan=(wh - wl) / np.pi)
    h *= np.hanning(num_taps)
    return h.astype(np.float32)


def _fir_lowpass(cutoff_hz: float, num_taps: int = 255) -> np.ndarray:
    """Windowed-sinc FIR lowpass filter (pure numpy)."""
    n = np.arange(num_taps) - (num_taps - 1) / 2
    wc = 2 * np.pi * cutoff_hz / SR
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(n == 0, wc / np.pi, np.sin(wc * n) / (np.pi * n))
    h = np.nan_to_num(h, nan=wc / np.pi)
    h *= np.hanning(num_taps)
    return h.astype(np.float32)


def _apply_fir(signal: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Overlap-add FIR convolution via numpy (linear phase)."""
    out = np.convolve(signal.astype(np.float64), h.astype(np.float64), mode="same")
    return out.astype(np.float32)


# Pre-compute filter kernels once
_BP_SPEECH  = _fir_bandpass(300, 3400)
_BP_ROAD    = _fir_bandpass(50, 1200)
_LP_WIND    = _fir_lowpass(200)


def _pink_noise(rng, n):
    """Approximate pink noise via IIR (Paul Kellett method, adapted)."""
    white = rng.standard_normal(n)
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    out = np.empty(n, dtype=np.float64)
    for i, s in enumerate(white):
        b0 = 0.99886 * b0 + s * 0.0555179
        b1 = 0.99332 * b1 + s * 0.0750759
        b2 = 0.96900 * b2 + s * 0.1538520
        b3 = 0.86650 * b3 + s * 0.3104856
        b4 = 0.55000 * b4 + s * 0.5329522
        b5 = -0.7616 * b5 - s * 0.0168980
        out[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + s * 0.5362
        b6 = s * 0.115926
    return out


def synth_speech(rng: np.random.Generator, duration: float) -> np.ndarray:
    """Bandpass noise (300–3400 Hz) with 4 Hz syllable-cadence AM envelope."""
    n = int(duration * SR)
    noise = rng.standard_normal(n).astype(np.float32)
    speech = _apply_fir(noise, _BP_SPEECH)
    t = np.arange(n) / SR
    envelope = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t))
    return (speech * envelope).astype(np.float32)


def synth_road_noise(rng: np.random.Generator, duration: float) -> np.ndarray:
    """Pink-shaped noise bandpass 50–1200 Hz (tyre rumble + engine)."""
    n = int(duration * SR)
    pink = _pink_noise(rng, n).astype(np.float32)
    return _apply_fir(pink, _BP_ROAD)


def synth_wind_noise(rng: np.random.Generator, duration: float) -> np.ndarray:
    """Low-pass (<200 Hz) noise with slow gust envelope (0.3 Hz AM)."""
    n = int(duration * SR)
    noise = rng.standard_normal(n).astype(np.float32)
    wind = _apply_fir(noise, _LP_WIND)
    t = np.arange(n) / SR
    gust = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t))
    return (wind * gust).astype(np.float32)


def add_echo(mic: np.ndarray, ref: np.ndarray,
             delay_samples: int = ECHO_DELAY,
             attenuation_db: float = ECHO_ATT_DB) -> np.ndarray:
    """Add a delayed, attenuated copy of ref into mic (acoustic echo model)."""
    gain = 10 ** (attenuation_db / 20.0)
    echo = np.zeros_like(ref)
    echo[delay_samples:] = ref[:-delay_samples] * gain
    return mic + echo


def normalize(sig: np.ndarray, peak_db: float = -12.0) -> np.ndarray:
    """Scale signal so its peak is at peak_db dBFS."""
    peak = np.max(np.abs(sig))
    if peak < 1e-9:
        return sig.copy()
    target = 10 ** (peak_db / 20.0)
    return (sig * (target / peak)).astype(np.float32)


def mix_at_snr(signal: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """Mix noise into signal at a given SNR (dB). Returns signal + scaled noise."""
    p_sig = np.mean(signal ** 2) + 1e-12
    p_noi = np.mean(noise ** 2) + 1e-12
    snr_lin = 10 ** (snr_db / 10.0)
    scale = np.sqrt(p_sig / (p_noi * snr_lin))
    return signal + noise * scale


def zeros(duration: float) -> np.ndarray:
    return np.zeros(int(duration * SR), dtype=np.float32)


def _fit_signal(sig: np.ndarray, target_n: int) -> np.ndarray:
    """Repeat/trim signal to target length."""
    if target_n <= 0:
        return np.zeros(0, dtype=np.float32)
    if len(sig) == 0:
        return np.zeros(target_n, dtype=np.float32)
    reps = int(np.ceil(target_n / len(sig)))
    return np.tile(sig, reps)[:target_n].astype(np.float32)


def _read_mono_wav(path: Path) -> np.ndarray:
    """Read WAV and return mono float32."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data[:, 0].astype(np.float32)
    if sr == SR:
        return mono

    # Linear-resample external assets to match scenario sample rate.
    src_n = len(mono)
    if src_n == 0:
        return mono
    dst_n = int(round(src_n * (SR / sr)))
    if dst_n <= 0:
        return np.zeros(0, dtype=np.float32)
    x_src = np.linspace(0.0, 1.0, src_n, endpoint=False)
    x_dst = np.linspace(0.0, 1.0, dst_n, endpoint=False)
    return np.interp(x_dst, x_src, mono).astype(np.float32)


def _load_speech_pool(assets_dir: Path, rng: np.random.Generator, duration: float) -> list[np.ndarray]:
    """Load AI speech WAVs from assets; fallback to synthesized speech."""
    pool: list[np.ndarray] = []
    for filename in AI_SPEECH_FILES:
        p = assets_dir / filename
        if p.exists():
            clip = _read_mono_wav(p)
            if np.max(np.abs(clip)) > 1e-9:
                pool.append(normalize(clip, peak_db=-10.0))
    if not pool:
        # Keep generator usable even if AI assets are missing.
        for _ in range(3):
            pool.append(normalize(synth_speech(rng, duration), peak_db=-10.0))
    return pool


def _segment(total_n: int, start_n: int, seg: np.ndarray) -> np.ndarray:
    """Place seg into a zero vector at start_n, clipping to bounds."""
    out = np.zeros(total_n, dtype=np.float32)
    if len(seg) == 0:
        return out
    s = max(0, start_n)
    e = min(total_n, s + len(seg))
    if e > s:
        out[s:e] = seg[: e - s]
    return out


def _timeline(duration: float) -> tuple[int, int, int, int, int]:
    """Return (total_n, lead_n, tail_n, active_start, active_n)."""
    total_n = int(duration * SR)
    lead_n = int(SILENCE_HEAD_S * SR)
    tail_n = int(SILENCE_TAIL_S * SR)
    active_start = lead_n
    active_end = max(active_start, total_n - tail_n)
    active_n = max(0, active_end - active_start)
    return total_n, lead_n, tail_n, active_start, active_n


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def write_pair(assets_dir: Path, name: str,
               mic_mono: np.ndarray, ref_mono: np.ndarray) -> None:
    """Write 2-channel mic WAV and 1-channel ref WAV."""
    mic_stereo = np.stack([mic_mono, mic_mono], axis=1)
    mic_path = assets_dir / f"{name}_mic.wav"
    ref_path = assets_dir / f"{name}_ref.wav"
    sf.write(str(mic_path), mic_stereo, SR, subtype="FLOAT")
    sf.write(str(ref_path), ref_mono, SR, subtype="FLOAT")
    print(f"  WAV {name}: {len(mic_mono)/SR:.1f}s  mic={mic_path.name}  ref={ref_path.name}", flush=True)


def write_scenario(scenarios_dir: Path, name: str, expected: dict) -> dict:
    """Write scenario JSON and return its descriptor for the master suite."""
    desc = {
        "name": name,
        "config": "configs/phase1_default.json",
        "mic_wav": f"scenarios/assets/{name}_mic.wav",
        "ref_wav": f"scenarios/assets/{name}_ref.wav",
        "output_wav": f"scenarios/results/{name}_output.wav",
        "metrics_csv": f"scenarios/results/{name}_metrics.csv",
        "expected": expected,
    }
    path = scenarios_dir / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(desc, f, indent=2)
    return f"scenarios/{name}.json"


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

def generate(duration: float, scenarios_dir: Path) -> None:
    assets_dir = scenarios_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "results").mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed=42)
    suite_scenarios = []
    speech_pool = _load_speech_pool(assets_dir, rng, duration)
    n, _, _, active_start, active_n = _timeline(duration)

    if active_n <= FRAME:
        raise ValueError(
            "Duration too short for configured silence windows. "
            f"Need > {SILENCE_HEAD_S + SILENCE_TAIL_S + FRAME / SR:.2f}s"
        )

    def speech_seg(pool_idx: int, peak_db: float, seg_n: int) -> np.ndarray:
        return normalize(_fit_signal(speech_pool[pool_idx % len(speech_pool)], seg_n), peak_db=peak_db)

    # --- TC01: speech only ---------------------------------------------------
    name = "tc01_speech_only"
    near = _segment(n, active_start, speech_seg(0, -8.0, active_n))
    ref = np.zeros(n, dtype=np.float32)
    write_pair(assets_dir, name, near, ref)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"no_crash": True,
         "description": "AI speech near-end only with 2s head/tail silence in both channels"}))

    # --- TC02: echo single-talk (no near-end speech) -------------------------
    name = "tc02_echo_single_talk"
    far = _segment(n, active_start, speech_seg(1, -14.0, active_n))
    mic = add_echo(np.zeros(n, dtype=np.float32), far)
    write_pair(assets_dir, name, mic, far)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"erle_mean_db_min": 10.0,
         "dtd_frames_max_pct": 10.0,
         "description": "Far-end AI speech with silent head/tail; AEC converges while DTD stays mostly off"}))

    # --- TC03: double-talk (near-end + echo simultaneously) ------------------
    # Near-end is 12 dB louder than far-end so p_mic/p_ref > 6 dB threshold
    name = "tc03_double_talk"
    far2 = _segment(n, active_start, speech_seg(2, -18.0, active_n))
    near2 = _segment(n, active_start, speech_seg(0, -8.0, active_n))
    mic3 = add_echo(near2, far2)
    mic3 = np.clip(mic3, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic3, far2)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"dtd_frames_min_pct": 30.0,
         "description": "Aggressive overlap: near-end AI speech dominates far-end during active window"}))

    # --- TC04: speech + road noise (SNR 0 dB) --------------------------------
    name = "tc04_speech_road_noise"
    speech4 = speech_seg(0, -10.0, active_n)
    road4 = normalize(_fit_signal(synth_road_noise(rng, duration), active_n), peak_db=-14.0)
    mix4 = normalize(mix_at_snr(speech4, road4, snr_db=0.0))
    mic4 = _segment(n, active_start, mix4)
    ref4 = np.zeros(n, dtype=np.float32)
    write_pair(assets_dir, name, mic4, ref4)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"snr_delta_mean_db_max": -3.0,
         "description": "AI speech plus road noise in active window with silent head/tail"}))

    # --- TC05: speech + wind noise (SNR 0 dB) --------------------------------
    name = "tc05_speech_wind_noise"
    speech5 = speech_seg(1, -10.0, active_n)
    wind5 = normalize(_fit_signal(synth_wind_noise(rng, duration), active_n), peak_db=-14.0)
    mix5 = normalize(mix_at_snr(speech5, wind5, snr_db=0.0))
    mic5 = _segment(n, active_start, mix5)
    ref5 = np.zeros(n, dtype=np.float32)
    write_pair(assets_dir, name, mic5, ref5)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"snr_delta_mean_db_max": -3.0,
         "description": "AI speech plus wind noise in active window with silent head/tail"}))

    # --- TC06: DTD + road noise (5s AEC convergence + 10s double-talk) -------
    # Far-end runs for full 15s; near-end enters at 5s with 12 dB more power
    name = "tc06_dtd_road_noise"
    conv6_n = int(2.0 * SR)
    far6 = _segment(n, active_start, speech_seg(2, -14.0, active_n))
    near6_seg_n = max(0, active_n - conv6_n)
    near6 = _segment(n, active_start + conv6_n, speech_seg(0, -6.0, near6_seg_n))
    road6 = _segment(
        n,
        active_start,
        normalize(_fit_signal(synth_road_noise(rng, duration), active_n), peak_db=-18.0),
    )
    mic6 = add_echo(np.zeros(n, dtype=np.float32), far6)
    mic6 += near6
    mic6 += road6 * 0.5
    mic6 = np.clip(mic6, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic6, far6)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"dtd_frames_min_pct": 20.0,
         "description": "2s echo-only convergence then AI speech overlap with road noise and silent head/tail"}))


    # --- TC07: DTD + wind noise (5s AEC convergence + 10s double-talk) -------
    name = "tc07_dtd_wind_noise"
    conv7_n = int(2.0 * SR)
    far7 = _segment(n, active_start, speech_seg(1, -14.0, active_n))
    near7_seg_n = max(0, active_n - conv7_n)
    near7 = _segment(n, active_start + conv7_n, speech_seg(2, -8.0, near7_seg_n))
    wind7 = _segment(
        n,
        active_start,
        normalize(_fit_signal(synth_wind_noise(rng, duration), active_n), peak_db=-18.0),
    )
    mic7 = add_echo(np.zeros(n, dtype=np.float32), far7)
    mic7 += near7
    mic7 += wind7 * 0.5
    mic7 = np.clip(mic7, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic7, far7)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"dtd_frames_min_pct": 20.0,
         "description": "2s echo-only convergence then AI speech overlap with wind noise and silent head/tail"}))


    # --- TC08: silence (edge case) -------------------------------------------
    name = "tc08_silence"
    mic8 = np.zeros(n, dtype=np.float32)
    ref8 = np.zeros(n, dtype=np.float32)
    write_pair(assets_dir, name, mic8, ref8)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"no_crash": True,
         "description": "Silence input: pipeline must complete without crash or NaN output"}))

    # --- TC09: AEC convergence (echo-only → double-talk mid-file) ------------
    # First half: echo only → AEC converges silently, DTD off
    # Second half: near-end (12 dB louder than ref) added → DTD fires
    # Near-end 16 dB louder than far-end (ratio ~40 >> 4.0 threshold) for
    # reliable DTD in second half regardless of per-frame AM envelope variance
    name = "tc09_aec_convergence"
    half_n = active_n // 2
    far9 = _segment(n, active_start, speech_seg(0, -16.0, active_n))
    near9 = _segment(n, active_start + half_n, speech_seg(1, -2.0, active_n - half_n))
    mic9 = add_echo(np.zeros(n, dtype=np.float32), far9)
    mic9 += near9
    mic9 = np.clip(mic9, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic9, far9)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"erle_mean_db_min": 15.0,
         "dtd_first_half_max_pct": 5.0,
         "dtd_second_half_min_pct": 40.0,
         "description": "AEC convergence then delayed overlap: DTD low in first active half and high in second"}))

    # --- TC10: high-SNR speech (SNR +20 dB) ----------------------------------
    name = "tc10_high_snr_speech"
    speech10 = speech_seg(2, -9.0, active_n)
    road10 = normalize(_fit_signal(synth_road_noise(rng, duration), active_n), peak_db=-22.0)
    mix10 = normalize(mix_at_snr(speech10, road10, snr_db=20.0))
    mic10 = _segment(n, active_start, mix10)
    ref10 = np.zeros(n, dtype=np.float32)
    write_pair(assets_dir, name, mic10, ref10)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"snr_delta_mean_db_max": -1.0,
         "description": "High-SNR AI speech with silent head/tail; confirms NR remains active"}))

    # --- TC11: moderate DTD overlap -----------------------------------------
    name = "tc11_dtd_speech_moderate"
    far11 = _segment(n, active_start, speech_seg(0, -14.0, active_n))
    ovl11_n = int(2.5 * SR)
    ovl11_start = active_start + int(1.0 * SR)
    near11 = _segment(n, ovl11_start, speech_seg(1, -6.0, ovl11_n))
    mic11 = add_echo(np.zeros(n, dtype=np.float32), far11) + near11
    mic11 = np.clip(mic11, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic11, far11)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"dtd_frames_min_pct": 12.0,
         "description": "Moderate DTD overlap (+8 dB near-end) bounded by silent head/tail windows"}))

    # --- TC12: aggressive DTD overlap ---------------------------------------
    name = "tc12_dtd_speech_aggressive"
    far12 = _segment(n, active_start, speech_seg(1, -18.0, active_n))
    ovl12_n = int(3.0 * SR)
    ovl12_start = active_start + int(1.0 * SR)
    near12 = _segment(n, ovl12_start, speech_seg(2, -4.0, ovl12_n))
    mic12 = add_echo(np.zeros(n, dtype=np.float32), far12) + near12
    mic12 = np.clip(mic12, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic12, far12)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"dtd_frames_min_pct": 25.0,
         "description": "Aggressive DTD overlap (+14 dB near-end) with enforced silence windows"}))

    # --- TC13: short-overlap DTD with silence guards ------------------------
    name = "tc13_dtd_silence_guard"
    far13_n = int(2.0 * SR)
    near13_n = int(2.0 * SR)
    far13 = _segment(n, active_start, speech_seg(0, -12.0, far13_n))
    near13 = _segment(n, active_start + far13_n + int(0.5 * SR), speech_seg(2, -6.0, near13_n))
    ref13 = far13
    mic13 = add_echo(np.zeros(n, dtype=np.float32), ref13) + near13
    mic13 = np.clip(mic13, -1.0, 1.0).astype(np.float32)
    write_pair(assets_dir, name, mic13, ref13)
    suite_scenarios.append(write_scenario(scenarios_dir, name,
        {"dtd_frames_min_pct": 15.0,
         "description": "Silence-guarded timeline with a short overlap burst to verify DTD activation remains localized"}))

    # --- Write master suite --------------------------------------------------
    suite = {
        "name": "ecnr_test_suite",
        "description": "AI speech-driven ECNR validation suite with silence windows and DTD stress cases",
        "scenarios": suite_scenarios,
    }
    suite_path = scenarios_dir / "ecnr_test_suite.json"
    with open(suite_path, "w", encoding="utf-8") as f:
        json.dump(suite, f, indent=2)
    print(f"\nSuite -> {suite_path}  ({len(suite_scenarios)} scenarios)")


# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate ECNR test WAV pairs")
    parser.add_argument("--duration", type=float, default=DURATION,
                        help=f"Signal duration in seconds (default: {DURATION})")
    parser.add_argument("--scenarios-dir", default=None,
                        help="Path to scenarios/ directory (default: auto-detect)")
    args = parser.parse_args()

    # Auto-detect: script lives inside scenarios/, repo root is parent
    script_dir = Path(__file__).resolve().parent
    scenarios_dir = Path(args.scenarios_dir) if args.scenarios_dir else script_dir

    print(f"Generating {args.duration}s test WAVs -> {scenarios_dir / 'assets'}")
    generate(args.duration, scenarios_dir)
    print("Done.")


if __name__ == "__main__":
    _main()
