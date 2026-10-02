#!/usr/bin/env python3
"""
VSense-HIL Telemetry Daemon (vsensord) - Python System Implementation
Ingests 40-byte binary packets from UDP / device node, runs range/CRC validation,
rolling Z-score anomaly engine, SQLite buffer, and cloud HTTP post.
"""

import os
import sys
import time
import struct
import math
import sqlite3
import signal
import socket
import requests
from collections import deque

MAGIC_HEADER = 0x56534E53

SENSORS_META = {
    1: ("Temperature", "°C"),
    2: ("Humidity", "%"),
    3: ("Pressure", "hPa"),
    4: ("Vibration", "mm/s"),
    5: ("Voltage", "V"),
    6: ("Current", "A")
}

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

class TelemetryDaemon:
    def __init__(self, device_path="vsensor0.fifo", udp_port=9999, cloud_url="http://localhost:8000/api/v1/telemetry", api_key="vsense_secret_api_key_12345"):
        self.device_path = device_path
        self.udp_port = udp_port
        self.cloud_url = cloud_url
        self.api_key = api_key
        self.running = True
        self.windows = {sid: deque(maxlen=30) for sid in SENSORS_META}
        self.last_seq = {}
        self.state = "NORMAL"
        self.consecutive_valid = 0
        self.consecutive_anomalies = 0
        self.buffer = []

    def validate_sample(self, packet: bytes):
        if len(packet) != 40:
            return False, "Invalid packet length"

        magic, sensor_id, stype, val, ts_ns, seq_num, status, crc16 = struct.unpack("<IIIdQQHH", packet)

        if magic != MAGIC_HEADER:
            return False, "Magic header mismatch"

        if math.isnan(val) or math.isinf(val):
            return False, "NaN or Inf value"

        expected_crc = compute_crc16(packet[:38])
        if crc16 != expected_crc:
            return False, "CRC16 checksum error"

        if sensor_id in self.last_seq and seq_num <= self.last_seq[sensor_id]:
            return False, "Sequence out of order"

        self.last_seq[sensor_id] = seq_num

        return True, {
            "magic": magic,
            "sensor_id": sensor_id,
            "sensor_type": stype,
            "value": val,
            "timestamp_ns": ts_ns,
            "seq_num": seq_num,
            "status_flags": status
        }

    def process_anomaly(self, sample: dict):
        sid = sample["sensor_id"]
        val = sample["value"]
        sname, unit = SENSORS_META.get(sid, ("Unknown", ""))

        window = self.windows[sid]
        window.append(val)

        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        stddev = math.sqrt(variance)

        z_score = 0.0
        if stddev > 0.0001:
            z_score = (val - mean) / stddev

        is_anomaly = (abs(z_score) > 2.5) or ((sample["status_flags"] & 0x1E) != 0)

        if is_anomaly:
            self.consecutive_valid = 0
            self.consecutive_anomalies += 1
            if abs(z_score) > 4.0 or self.consecutive_anomalies >= 3 or (sample["status_flags"] & 0x10):
                self.state = "CRITICAL"
            elif self.state == "NORMAL":
                self.state = "WARNING"
        else:
            self.consecutive_anomalies = 0
            self.consecutive_valid += 1
            if self.state == "CRITICAL" and self.consecutive_valid >= 5:
                self.state = "RECOVERY"
            elif self.state in ("WARNING", "RECOVERY") and self.consecutive_valid >= 5:
                self.state = "NORMAL"

        severity = "INFO"
        msg = "Normal baseline signal"
        if self.state == "CRITICAL":
            severity = "CRITICAL"
            msg = f"Critical anomaly on {sname}! Z-score: {z_score:.2f}"
        elif self.state == "WARNING":
            severity = "WARNING"
            msg = f"Elevated variance on {sname}. Z-score: {z_score:.2f}"

        sample.update({
            "name": sname,
            "type": sname,
            "unit": unit,
            "state": self.state,
            "z_score": round(z_score, 3),
            "alert_severity": severity,
            "alert_message": msg
        })

        return sample

    def run(self):
        print(f"[VSENSORD] Starting Telemetry Daemon listening on UDP 127.0.0.1:{self.udp_port}")
        print(f"[VSENSORD] Target Cloud Endpoint: {self.cloud_url}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", self.udp_port))
        sock.settimeout(1.0)

        while self.running:
            try:
                packet, addr = sock.recvfrom(512)
                if packet and len(packet) == 40:
                    is_valid, res = self.validate_sample(packet)
                    if not is_valid:
                        continue

                    processed = self.process_anomaly(res)
                    self.buffer.append(processed)

                    if len(self.buffer) >= 6:
                        self.flush_to_cloud()
            except socket.timeout:
                pass
            except Exception as e:
                time.sleep(0.1)

    def flush_to_cloud(self):
        if not self.buffer:
            return

        payload = {
            "device_id": "vsense-edge-01",
            "batch_size": len(self.buffer),
            "telemetry": self.buffer
        }

        try:
            res = requests.post(
                self.cloud_url,
                json=payload,
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                timeout=2.0
            )
            if res.status_code == 200:
                self.buffer.clear()
        except Exception:
            pass

def main():
    daemon = TelemetryDaemon()

    def sig_handler(sig, frame):
        print("\n[VSENSORD] Shutting down...")
        daemon.running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    daemon.run()

if __name__ == "__main__":
    main()
