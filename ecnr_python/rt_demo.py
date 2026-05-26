"""ECNR PC Real-Time Demo — entry point.

Usage examples:
  python -m ecnr_python.rt_demo --list-devices
  python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json
  python -m ecnr_python.rt_demo --config configs/phase1_default.json --duration 60
  python -m ecnr_python.rt_demo --config configs/phase1_default.json --latency-test
  python -m ecnr_python.rt_demo --gui                        # live visualisation
  python -m ecnr_python.rt_demo --gui --record-path out.wav  # record output
"""

import argparse
import time
from pathlib import Path

import numpy as np

from ecnr_python.config.ecnr_config import EcnrConfig, load_config, load_scenario_config
from ecnr_python.engine import EcnrEngine
from ecnr_python.io.reference import ReferenceSource
from ecnr_python.io.rt_audio import RtAudio


def _make_frame_callback(engine: EcnrEngine, ref_source: ReferenceSource):
    def callback(in_frame: np.ndarray, out_frame: np.ndarray) -> None:
        ref = ref_source.read_frame()
        out = engine.process_frame(in_frame, ref)
        out_frame[:, 0] = out

    return callback


def _load_config(args) -> EcnrConfig:
    if args.scenario:
        cfg = load_scenario_config(args.scenario)
        print(f"[demo] Config loaded from scenario: {args.scenario}")
        return cfg
    if args.config:
        cfg = load_config(args.config)
        print(f"[demo] Config loaded from: {args.config}")
        return cfg
    # Default: try Phase 1 scenario relative to repo root
    default = Path(__file__).parent.parent / "scenarios" / "phase1_offline_wav.json"
    if default.exists():
        cfg = load_scenario_config(str(default))
        print(f"[demo] Config loaded from default scenario: {default}")
        return cfg
    print("[demo] No config specified — using defaults")
    return EcnrConfig()


def _parse_device(d):
    try:
        return int(d)
    except (TypeError, ValueError):
        return d


def main():
    parser = argparse.ArgumentParser(description="ECNR PC Real-Time Demo")
    parser.add_argument("--config", default=None, help="Path to ecnr config JSON")
    parser.add_argument("--scenario", default=None, help="Path to Phase 1 scenario JSON")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Run duration in seconds (default: 60)")
    parser.add_argument("--latency-test", action="store_true",
                        help="Inject acoustic click for round-trip latency measurement")
    parser.add_argument("--input-device", default=None,
                        help="sounddevice input device index or name substring")
    parser.add_argument("--output-device", default=None,
                        help="sounddevice output device index or name substring")
    parser.add_argument("--list-devices", action="store_true",
                        help="Print available audio devices and exit")
    parser.add_argument("--gui", action="store_true",
                        help="Open live spectrogram + metrics visualisation window")
    parser.add_argument("--record-path", default="ecnr_capture.wav",
                        help="Output WAV path for GUI recording (default: ecnr_capture.wav)")
    parser.add_argument("--profile", action="store_true",
                        help="Enable per-module CPU profiling; report on exit")
    parser.add_argument("--stability-run", action="store_true",
                        help="Offline looped-WAV stability run (no audio device needed)")
    parser.add_argument("--loops", type=int, default=90,
                        help="Loop count for --stability-run (default: 90 ≈ 30 min)")
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return

    # Offline stability run — no audio device required
    if args.stability_run:
        from ecnr_python.offline_runner import run_scenario_offline
        scenario = args.scenario or str(
            Path(__file__).parent.parent / "scenarios" / "phase1_offline_wav.json"
        )
        print(f"[demo] Stability run: {args.loops} loops of {scenario}")
        summary = run_scenario_offline(
            scenario, loop_count=args.loops, enable_profile=args.profile
        )
        xrun_eq = 0  # offline has no xruns
        audio_min = summary["elapsed_s"] / 60
        print(f"[demo] Stability: {audio_min:.1f} min processed  xruns=0  "
              f"rt_factor={summary['rt_factor']:.0f}×")
        return

    cfg = _load_config(args)
    print(
        f"[demo] {cfg.sampling_rate} Hz  "
        f"frame={cfg.frame_size} samples ({cfg.frame_size/cfg.sampling_rate*1000:.1f} ms)  "
        f"mics={cfg.mic_count}  mode={cfg.mode.name}"
    )

    engine = EcnrEngine(cfg)
    if args.profile:
        engine.set_profile(True)

    ref_source = ReferenceSource(cfg.reference, cfg.frame_size, cfg.sampling_rate)

    viz = None
    if args.gui:
        from ecnr_python.gui.rt_viz import RtViz
        viz = RtViz(cfg, record_path=args.record_path,
                    bypass_callback=engine.set_bypass)
        engine.set_viz(viz)

    rt = RtAudio(
        cfg,
        frame_callback=_make_frame_callback(engine, ref_source),
        input_device=_parse_device(args.input_device),
        output_device=_parse_device(args.output_device),
    )

    rt.start()
    try:
        if args.latency_test:
            time.sleep(0.5)
            rt.measure_latency()

        if viz is not None:
            # Qt event loop takes over the main thread; duration enforced by Qt timer
            viz.run(args.duration)
        else:
            # Headless loop with periodic status print
            start = time.perf_counter()
            interval = 5.0
            next_report = start + interval
            while True:
                elapsed = time.perf_counter() - start
                if elapsed >= args.duration:
                    break
                now = time.perf_counter()
                if now >= next_report:
                    print(f"[demo] {elapsed:.0f}/{args.duration:.0f}s  xruns={rt.xrun_count}")
                    next_report += interval
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[demo] Interrupted")
    finally:
        rt.stop()
        ref_source.close()
        rtt = rt.round_trip_ms()
        if rtt is not None:
            print(f"[demo] Acoustic round-trip latency: {rtt:.1f} ms")
        print(f"[demo] Done. Total xruns: {rt.xrun_count}")
        if args.profile:
            from ecnr_python.offline_runner import _print_profile
            _print_profile(engine.profile_report(), cfg.frame_size, cfg.sampling_rate)


if __name__ == "__main__":
    main()
