"""ECNR PC Real-Time Demo — entry point.

Usage examples:
  python -m ecnr_python.rt_demo --list-devices
  python -m ecnr_python.rt_demo --scenario scenarios/phase1_offline_wav.json
  python -m ecnr_python.rt_demo --config configs/phase1_default.json --duration 60
  python -m ecnr_python.rt_demo --config configs/phase1_default.json --latency-test
"""

import argparse
import time
from pathlib import Path

import numpy as np

from ecnr_python.config.ecnr_config import EcnrConfig, load_config, load_scenario_config
from ecnr_python.engine import EcnrEngine
from ecnr_python.io.rt_audio import RtAudio


def _make_frame_callback(engine: EcnrEngine):
    ref = np.zeros(engine.config.frame_size, dtype="float32")

    def callback(in_frame: np.ndarray, out_frame: np.ndarray) -> None:
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
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return

    cfg = _load_config(args)
    print(
        f"[demo] {cfg.sampling_rate} Hz  "
        f"frame={cfg.frame_size} samples ({cfg.frame_size/cfg.sampling_rate*1000:.1f} ms)  "
        f"mics={cfg.mic_count}  mode={cfg.mode.name}"
    )

    engine = EcnrEngine(cfg)
    rt = RtAudio(
        cfg,
        frame_callback=_make_frame_callback(engine),
        input_device=args.input_device,
        output_device=args.output_device,
    )

    rt.start()
    try:
        if args.latency_test:
            time.sleep(0.5)  # let stream stabilise
            rt.measure_latency()

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
        rtt = rt.round_trip_ms()
        if rtt is not None:
            print(f"[demo] Acoustic round-trip latency: {rtt:.1f} ms")
        print(f"[demo] Done. Total xruns: {rt.xrun_count}")


if __name__ == "__main__":
    main()
