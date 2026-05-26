#!/usr/bin/env python3
"""Test script to check if audio is being captured and output."""

import argparse
import sys

import numpy as np
import sounddevice as sd
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="Audio capture/playback level test")
parser.add_argument("--device-in", type=int, default=1, help="Input device index (default: 1)")
parser.add_argument("--device-out", type=int, default=4, help="Output device index (default: 4)")
args = parser.parse_args()

# Test parameters
sr = 16000
frame_size = 320
duration = 5

print("Testing audio capture and playback...")
print(f"Input device index : {args.device_in}")
print(f"Output device index: {args.device_out}")
print()

captured_max = 0.0
output_count = 0

def callback(indata, outdata, frames, time_info, status):
    global captured_max, output_count
    if status:
        print(f"Status: {status}")

    in_level = np.max(np.abs(indata[:, 0]))
    captured_max = max(captured_max, in_level)

    outdata[:, 0] = indata[:, 0] * 0.5
    output_count += 1

try:
    with sd.Stream(
        samplerate=sr,
        blocksize=frame_size,
        channels=(2, 1),
        dtype='float32',
        device=(args.device_in, args.device_out),
        callback=callback,
        latency='low'
    ) as stream:
        print(f"Stream started. Input latency: {stream.latency[0]*1000:.1f}ms, Output: {stream.latency[1]*1000:.1f}ms")
        time.sleep(duration)
        print(f"Stream stopped.")

except Exception as e:
    print(f"Error: {e}")

print()
print(f"Results after {duration}s:")
print(f"  Max input level captured: {captured_max:.4f}")
print(f"  Output frames processed: {output_count}")
print()
if captured_max < 0.001:
    print("[!] WARNING: No audio captured from microphone!")
    print("    Check if the microphone is muted or disabled in Windows.")
    print("    Use --device-in and --device-out to select different devices.")
    print("    Run: python -c \"import sounddevice as sd; print(sd.query_devices())\"")
else:
    print(f"[OK] Microphone is capturing audio (peak level: {captured_max:.4f})")
    print(f"[OK] Should be hearing audio in headphones")
