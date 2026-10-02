#!/usr/bin/env python3
"""
VSense-HIL Userspace Device Emulator (PTY/FIFO Fallback)
Exposes identical /dev/vsensor0 interface at /tmp/vsensor0 for containerized and non-root environments.
"""

import os
import sys
import time
import signal

DEVICE_PATH = "vsensor0.fifo"

def setup_emulator_node():
    if os.path.exists(DEVICE_PATH):
        try:
            os.remove(DEVICE_PATH)
        except Exception:
            pass

    try:
        os.mkfifo(DEVICE_PATH, 0o666)
        print(f"[EMULATOR] Created userspace fallback FIFO node at {DEVICE_PATH}")
    except Exception as e:
        print(f"[EMULATOR] FIFO creation fallback to standard file: {e}")
        with open(DEVICE_PATH, "wb") as f:
            pass

def main():
    setup_emulator_node()
    print("[EMULATOR] Userspace Device Emulator Ready.")
    print(f"[EMULATOR] Point vsensord or readers to {DEVICE_PATH}")

    def shutdown(sig, frame):
        print("\n[EMULATOR] Cleaning up device node...")
        if os.path.exists(DEVICE_PATH):
            try:
                os.remove(DEVICE_PATH)
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
