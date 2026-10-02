#!/usr/bin/env python3
"""
VSense-HIL CLI Tool: vsensorctl
Utility to inspect daemon status, query telemetry, and dynamically inject sensor faults.
"""

import sys
import argparse
import requests
import json

DEFAULT_BACKEND = "http://localhost:8000"
API_KEY = "vsense_secret_api_key_12345"

def get_headers():
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

def status_cmd(args):
    url = f"{args.url}/api/v1/health"
    try:
        r = requests.get(url, headers=get_headers(), timeout=3.0)
        print("================ VSENSE-HIL SYSTEM HEALTH ================")
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"[ERROR] Failed to connect to VSense-HIL Cloud Backend at {url}: {e}")

def dump_cmd(args):
    url = f"{args.url}/api/v1/telemetry/latest"
    try:
        r = requests.get(url, headers=get_headers(), timeout=3.0)
        print("================ LATEST SENSOR READINGS ================")
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"[ERROR] Failed to query latest readings: {e}")

def inject_cmd(args):
    url = f"{args.url}/api/v1/faults/inject"
    payload = {
        "sensor_id": args.sensor_id,
        "fault_type": args.type,
        "duration_sec": args.duration
    }
    try:
        r = requests.post(url, json=payload, headers=get_headers(), timeout=3.0)
        print(f"[SUCCESS] Injected fault '{args.type}' on Sensor #{args.sensor_id} for {args.duration} seconds.")
        print("Response:", r.json())
    except Exception as e:
        print(f"[ERROR] Fault injection failed: {e}")

def main():
    parser = argparse.ArgumentParser(prog="vsensorctl", description="VSense-HIL Control Utility")
    parser.add_argument("--url", default=DEFAULT_BACKEND, help="Cloud Backend URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Show system health and daemon status")

    # dump
    subparsers.add_parser("dump", help="Dump latest telemetry records")

    # inject-fault
    inject_p = subparsers.add_parser("inject-fault", help="Inject fault into sensor")
    inject_p.add_argument("--sensor-id", type=int, required=True, choices=[1,2,3,4,5,6], help="Sensor ID (1..6)")
    inject_p.add_argument("--type", required=True, choices=["spike", "stuck", "dropout", "out_of_range"], help="Fault type")
    inject_p.add_argument("--duration", type=float, default=5.0, help="Duration in seconds")

    args = parser.parse_args()

    if args.command == "status":
        status_cmd(args)
    elif args.command == "dump":
        dump_cmd(args)
    elif args.command == "inject-fault":
        inject_cmd(args)

if __name__ == "__main__":
    main()
