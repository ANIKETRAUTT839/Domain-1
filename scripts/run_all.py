#!/usr/bin/env python3
"""
VSense-HIL Full Pipeline Orchestrator & Localhost Server Launcher
Launches Cloud Backend (FastAPI), Sensor Simulator, and Telemetry Daemon background services.
"""

import sys
import os
import time
import subprocess
import signal

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, root_dir)

    print("==========================================================")
    print("  VSense-HIL: Virtual Sensor Telemetry Engine")
    print("  Launching End-to-End Pipeline on Localhost")
    print("==========================================================")

    # 1. Launch FastAPI Cloud Backend
    print("[1/3] Starting FastAPI Cloud Backend on http://localhost:8000 ...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "cloud-backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
    backend_proc = subprocess.Popen(backend_cmd, cwd=root_dir)
    time.sleep(2.0)

    # 2. Launch Sensor Simulator
    print("[2/3] Starting Sensor Simulator (Writing to vsensor0.fifo) ...")
    sim_cmd = [sys.executable, "simulator/sensor_sim.py", "--device", "vsensor0.fifo", "--rate", "2.0"]
    sim_proc = subprocess.Popen(sim_cmd, cwd=root_dir)
    time.sleep(1.0)

    # 3. Launch Telemetry Daemon
    print("[3/3] Starting Telemetry Daemon (vsensord) ...")
    daemon_cmd = [sys.executable, "daemon/vsensord.py"]
    daemon_proc = subprocess.Popen(daemon_cmd, cwd=root_dir)

    print("\n==========================================================")
    print("  SUCCESS! VSense-HIL Pipeline is Live on Localhost:")
    print("  Dashboard UI:   http://localhost:8000")
    print("  API Docs:       http://localhost:8000/docs")
    print("  Telemetry API:  http://localhost:8000/api/v1/telemetry/latest")
    print("  Health API:     http://localhost:8000/api/v1/health")
    print("==========================================================")
    print("Press Ctrl+C to terminate all services.\n")

    def shutdown(sig, frame):
        print("\n[ORCHESTRATOR] Shutting down services...")
        for proc in [daemon_proc, sim_proc, backend_proc]:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        print("[ORCHESTRATOR] All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
