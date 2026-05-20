#!/usr/bin/env python3
import sys
import sounddevice as sd
import numpy as np
import time

print("TEST: Checking sounddevice and devices", flush=True)

print("Available devices:", flush=True)
try:
    devices = sd.query_devices()
    print(f"Found {len(devices)} devices", flush=True)
    for i, dev in enumerate(devices):
        if 'AirPods' in dev['name'] or 'Microphone Array' in dev['name']:
            print(f"  Device {i}: {dev['name']}", flush=True)
except Exception as e:
    print(f"Error querying devices: {e}", flush=True)
    sys.exit(1)

def audio_callback(indata, outdata, frames, time_info, status):
    if status:
        print(f"Status: {status}", flush=True)
    # Pass input to output (mic → headphones)
    outdata[:, 0] = indata[:, 0] * 0.5

print("\nTesting stream creation...", flush=True)
try:
    stream = sd.Stream(
        samplerate=16000,
        blocksize=320,
        channels=(2, 1),
        dtype='float32',
        device=(1, 4),
        callback=audio_callback,
        latency='low'
    )
    print("Stream created successfully", flush=True)
    stream.start()
    print("Stream started - playing passthrough for 3 seconds", flush=True)
    print("Speak into the microphone...", flush=True)

    for i in range(3):
        time.sleep(1)
        print(f"  {i+1}s elapsed", flush=True)

    stream.stop()
    stream.close()
    print("Stream stopped", flush=True)
    print("DONE", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
    import traceback
    traceback.print_exc(flush=True)
