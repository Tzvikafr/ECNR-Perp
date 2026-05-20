#!/usr/bin/env python3
"""Test script to check if audio is being captured and output."""

import numpy as np
import sounddevice as sd
import time

# Test parameters
sr = 16000
frame_size = 320
duration = 5

print("Testing audio capture and playback...")
print(f"Input: Microphone Array (index 1)")
print(f"Output: Headphones (AirPods Pro) (index 4)")
print()

captured_max = 0.0
output_count = 0

def callback(indata, outdata, frames, time_info, status):
    global captured_max, output_count
    if status:
        print(f"Status: {status}")

    # Check input level
    in_level = np.max(np.abs(indata[:, 0]))
    captured_max = max(captured_max, in_level)

    # Pass input directly to output
    outdata[:, 0] = indata[:, 0] * 0.5  # Scale down to 50% to be safe
    output_count += 1

try:
    with sd.Stream(
        samplerate=sr,
        blocksize=frame_size,
        channels=(2, 1),
        dtype='float32',
        device=(1, 4),  # Input device 1, Output device 4
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
    print("⚠️  WARNING: No audio captured from microphone!")
    print("   Check if the microphone is muted or disabled in Windows.")
else:
    print(f"✓ Microphone is capturing audio (peak level: {captured_max:.4f})")
    print(f"✓ Should be hearing audio in headphones")
