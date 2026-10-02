#!/usr/bin/env python3
"""
VSense-HIL Virtual Sensor Signal Generator & Fault Injector
Synthesizes multi-modal sensor signals with noise, drift, and injectable faults.
Output format: 40-byte binary vsensor_sample_t packets streamed over UDP 127.0.0.1:9999 and target file node.
"""

import sys
import os
import time
import struct
import random
import math
import argparse
import signal
import socket

MAGIC_HEADER = 0x56534E53  # 'VSNS'

SENSORS = {
    1: {"name": "Temperature", "type": 1, "baseline": 45.0, "unit": "°C", "min": -20.0, "max": 100.0, "stddev": 0.5},
    2: {"name": "Humidity",    "type": 2, "baseline": 55.0, "unit": "%",  "min": 0.0,   "max": 100.0, "stddev": 1.0},
    3: {"name": "Pressure",    "type": 3, "baseline": 1013.25, "unit": "hPa", "min": 800.0, "max": 1200.0, "stddev": 0.2},
    4: {"name": "Vibration",   "type": 4, "baseline": 2.5,  "unit": "mm/s", "min": 0.0,  "max": 50.0,  "stddev": 0.15},
    5: {"name": "Voltage",     "type": 5, "baseline": 230.0, "unit": "V", "min": 180.0, "max": 280.0, "stddev": 0.8},
    6: {"name": "Current",     "type": 6, "baseline": 12.0, "unit": "A", "min": 0.0,   "max": 50.0,  "stddev": 0.25}
}

STATUS_OK = 0x01
STATUS_NOISE = 0x02
STATUS_SPIKE = 0x04
STATUS_STUCK = 0x08
STATUS_OUT_OF_RANGE = 0x10

sim_global = None

def compute_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
    return crc & 0xFFFF

class SensorSimulator:
    def __init__(self, target_path="vsensor0.fifo", sample_rate_hz=2.0, udp_port=9999):
        self.target_path = target_path
        self.sample_rate_hz = sample_rate_hz
        self.udp_port = udp_port
        self.seq_num = 1
        self.running = True
        self.active_faults = {}
        self.stuck_values = {}
        self.drift_angles = {sid: random.uniform(0, 2*math.pi) for sid in SENSORS}

    def inject_fault(self, sensor_id: int, fault_type: str, duration_sec: float = 5.0, custom_value: float = None):
        self.active_faults[sensor_id] = {
            "type": fault_type,
            "end_time": time.time() + duration_sec,
            "custom_value": custom_value
        }
        print(f"[SIMULATOR] Injected fault '{fault_type}' on Sensor {sensor_id} ({SENSORS[sensor_id]['name']}) for {duration_sec}s")

    def generate_sample(self, sensor_id: int) -> bytes:
        meta = SENSORS[sensor_id]
        now = time.time()
        now_ns = int(now * 1e9)
        status = STATUS_OK

        self.drift_angles[sensor_id] += 0.05
        drift = math.sin(self.drift_angles[sensor_id]) * (meta["baseline"] * 0.02)
        noise = random.gauss(0, meta["stddev"])
        value = meta["baseline"] + drift + noise

        fault = self.active_faults.get(sensor_id)
        if fault and now < fault["end_time"]:
            ftype = fault["type"]
            if ftype == "spike":
                value += meta["baseline"] * 2.5
                status |= STATUS_SPIKE
            elif ftype == "stuck":
                if sensor_id not in self.stuck_values:
                    self.stuck_values[sensor_id] = value
                value = self.stuck_values[sensor_id]
                status |= STATUS_STUCK
            elif ftype == "out_of_range":
                value = meta["max"] * 1.8
                status |= STATUS_OUT_OF_RANGE
            elif ftype == "dropout":
                value = float('nan')
                status |= STATUS_OUT_OF_RANGE
        else:
            if sensor_id in self.stuck_values:
                del self.stuck_values[sensor_id]
            if fault and now >= fault["end_time"]:
                del self.active_faults[sensor_id]

        payload_no_crc = struct.pack(
            "<IIIdQQH",
            MAGIC_HEADER,
            sensor_id,
            meta["type"],
            value if not math.isnan(value) else -9999.0,
            now_ns,
            self.seq_num,
            status
        )
        
        crc16 = compute_crc16(payload_no_crc)
        full_packet = payload_no_crc + struct.pack("<H", crc16)
        self.seq_num += 1
        return full_packet

    def run(self):
        global sim_global
        sim_global = self
        print(f"[SIMULATOR] Starting Virtual Sensor Generator -> UDP 127.0.0.1:{self.udp_port} & {self.target_path}")
        print(f"[SIMULATOR] Sample Rate: {self.sample_rate_hz} Hz across 6 sensors")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        interval = 1.0 / (self.sample_rate_hz * len(SENSORS))

        while self.running:
            for sensor_id in SENSORS:
                packet = self.generate_sample(sensor_id)
                try:
                    sock.sendto(packet, ("127.0.0.1", self.udp_port))
                except Exception:
                    pass

                try:
                    with open(self.target_path, "ab", buffering=0) as f:
                        f.write(packet)
                except Exception:
                    pass

                time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="VSense-HIL Sensor Simulator")
    parser.add_argument("--device", default="vsensor0.fifo", help="Target device path")
    parser.add_argument("--rate", type=float, default=2.0, help="Sample rate in Hz per sensor")
    parser.add_argument("--port", type=int, default=9999, help="UDP port")
    args = parser.parse_args()

    sim = SensorSimulator(target_path=args.device, sample_rate_hz=args.rate, udp_port=args.port)

    def sig_handler(sig, frame):
        print("\n[SIMULATOR] Shutting down...")
        sim.running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    sim.run()

if __name__ == "__main__":
    main()
