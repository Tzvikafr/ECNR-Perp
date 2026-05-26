"""Offline WAV scenario runner — Sprint 6.

Processes a Phase 1 scenario entirely in NumPy without an audio device.
Used for:
  - Regression testing against MATLAB baseline CSVs  (task 6.3)
  - CPU profiling per DSP module                      (task 6.2)
  - Stability/loop validation without hardware        (task 6.1)

Usage (direct):
  python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json
  python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --profile
  python -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --loops 90
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

# Ensure Unicode output works on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from ecnr_python.config.ecnr_config import load_config
from ecnr_python.engine import EcnrEngine
from ecnr_python.metrics.metrics import Metrics


def run_scenario_offline(
    scenario_path: str,
    repo_root: Optional[str] = None,
    loop_count: int = 1,
    enable_profile: bool = False,
    quiet: bool = False,
) -> dict:
    """Process a Phase 1 scenario WAV file offline.

    Returns a summary dict with keys:
      frames, erle_mean_db, snr_in_mean_db, snr_out_mean_db,
      snr_delta_mean_db, dtd_frames, rt_factor, elapsed_s,
      and optionally 'profile' when enable_profile=True.
    """
    scenario_path = Path(scenario_path)
    root = Path(repo_root) if repo_root else scenario_path.parent.parent

    with open(scenario_path) as f:
        scenario = json.load(f)

    config_path = root / scenario["config"]
    mic_wav     = root / scenario["mic_wav"]
    ref_wav     = root / scenario["ref_wav"]
    out_wav     = root / scenario.get("output_wav",
                                      "scenarios/results/py_offline_output.wav")
    metrics_csv = root / scenario.get("metrics_csv",
                                      "metrics_baselines/py_offline_current.csv")

    cfg = load_config(str(config_path))

    if not quiet:
        print(f"[offline] Scenario : {scenario.get('name', scenario_path.stem)}")
        print(f"[offline] mic_wav  : {mic_wav}")
        print(f"[offline] ref_wav  : {ref_wav}")

    # ---- Load WAVs ----
    mic_data, mic_sr = sf.read(str(mic_wav), dtype="float32", always_2d=True)
    ref_data, ref_sr = sf.read(str(ref_wav), dtype="float32", always_2d=True)

    if mic_sr != cfg.sampling_rate:
        raise ValueError(f"mic WAV sr={mic_sr} != config sr={cfg.sampling_rate}")
    if ref_sr != cfg.sampling_rate:
        raise ValueError(f"ref WAV sr={ref_sr} != config sr={cfg.sampling_rate}")

    # Ensure mic has exactly mic_count channels
    if mic_data.shape[1] < cfg.mic_count:
        mic_data = np.tile(mic_data[:, :1], (1, cfg.mic_count))
    mic_data = mic_data[:, :cfg.mic_count]
    ref_mono = ref_data[:, 0]

    # Optional loop for stability test
    if loop_count > 1:
        mic_data = np.tile(mic_data, (loop_count, 1))
        ref_mono = np.tile(ref_mono, loop_count)

    frame_size = cfg.frame_size
    n_frames   = len(mic_data) // frame_size

    # ---- Engine + metrics ----
    engine = EcnrEngine(cfg)
    if enable_profile:
        engine.set_profile(True)
    metrics = Metrics(cfg)

    out_frames: list = []
    t_start = time.perf_counter()

    for fi in range(n_frames):
        s = fi * frame_size
        e = s + frame_size

        out = engine.process_frame(mic_data[s:e, :], ref_mono[s:e])
        out_frames.append(out)

        erle_inst = engine.aec.erle_inst_db    if engine.aec else math.nan
        erle_win  = engine.aec.erle_window_db  if engine.aec else math.nan
        snr_in    = engine.nr.snr_in_db        if engine.nr  else math.nan
        snr_out   = engine.nr.snr_out_db       if engine.nr  else math.nan
        dtd       = engine.aec.dtd_active      if engine.aec else False

        metrics.update(fi + 1, erle_inst, erle_win, snr_in, snr_out, dtd)

    elapsed   = time.perf_counter() - t_start
    audio_dur = n_frames * frame_size / cfg.sampling_rate
    rt_factor = audio_dur / elapsed

    if not quiet:
        print(f"[offline] {n_frames} frames  {elapsed:.2f}s  "
              f"{rt_factor:.0f}× real-time")

    # ---- Write outputs ----
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), np.concatenate(out_frames), cfg.sampling_rate)
    if not quiet:
        print(f"[offline] Output WAV → {out_wav}")

    metrics.export_csv(str(metrics_csv))

    summary = metrics.summary()
    summary["rt_factor"]  = rt_factor
    summary["elapsed_s"]  = elapsed

    if enable_profile:
        prof = engine.profile_report()
        summary["profile"] = prof
        if not quiet:
            _print_profile(prof, frame_size, cfg.sampling_rate)

    if not quiet:
        print(f"[offline] {metrics.report()}")

    return summary


def _print_profile(prof: dict, frame_size: int, sr: int) -> None:
    budget_us = frame_size / sr * 1e6
    print(f"\n[profile] Frame budget: {budget_us:.0f} µs  "
          f"({frame_size} samples @ {sr} Hz)")
    print(f"{'Module':<10}  {'Mean µs':>9}  {'p99 µs':>8}  {'Frames':>7}  {'%Budget':>8}")
    print("-" * 52)
    total_mean = 0.0
    for name, v in prof.items():
        pct = v["mean_us"] / budget_us * 100
        flag = "  ⚠ >30%" if pct > 30.0 else ""
        print(f"{name:<10}  {v['mean_us']:>9.1f}  {v['p99_us']:>8.1f}  "
              f"{v['n']:>7d}  {pct:>7.1f}%{flag}")
        total_mean += v["mean_us"]
    print(f"{'TOTAL':<10}  {total_mean:>9.1f}  {'':>8}  {'':>7}  "
          f"{total_mean / budget_us * 100:>7.1f}%")
    print()


# ------------------------------------------------------------------ #
# CLI entry point                                                      #
# ------------------------------------------------------------------ #

def _main() -> None:
    parser = argparse.ArgumentParser(description="ECNR offline scenario runner")
    parser.add_argument("scenario", help="Path to Phase 1 scenario JSON")
    parser.add_argument("--repo-root", default=None,
                        help="Repo root directory (default: scenario/../..)")
    parser.add_argument("--loops", type=int, default=1,
                        help="Loop WAV input N times (default: 1)")
    parser.add_argument("--profile", action="store_true",
                        help="Enable per-module CPU profiling")
    args = parser.parse_args()

    summary = run_scenario_offline(
        args.scenario,
        repo_root=args.repo_root,
        loop_count=args.loops,
        enable_profile=args.profile,
    )
    sys.exit(0)


if __name__ == "__main__":
    _main()
