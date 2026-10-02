#!/usr/bin/env python3
"""
VSense-HIL FastAPI Cloud Backend
Provides telemetry batch ingestion, query API, alerts, health status, and serves the Web Dashboard.
"""

import os
import sys
import time
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vsense_cloud.db"))
API_KEY_SECRET = os.getenv("API_KEY", "vsense_secret_api_key_12345")

app = FastAPI(
    title="VSense-HIL Cloud Telemetry API",
    description="High-performance telemetry ingest, anomaly tracking, and fault injection API.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# Database Initialization
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id INTEGER,
            name TEXT,
            type TEXT,
            value REAL,
            unit TEXT,
            timestamp_ns INTEGER,
            seq_num INTEGER,
            status_flags INTEGER,
            state TEXT,
            z_score REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id INTEGER,
            severity TEXT,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fault_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id INTEGER,
            fault_type TEXT,
            duration_sec REAL,
            executed INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Models
struct_sensors = {
    1: ("Temperature", "°C"),
    2: ("Humidity", "%"),
    3: ("Pressure", "hPa"),
    4: ("Vibration", "mm/s"),
    5: ("Voltage", "V"),
    6: ("Current", "A")
}

class TelemetryItem(BaseModel):
    sensor_id: int
    name: str
    type: str
    value: float
    unit: str
    timestamp_ns: int
    seq_num: int
    status_flags: int
    state: str
    z_score: float
    alert_severity: Optional[str] = "INFO"
    alert_message: Optional[str] = "OK"

class TelemetryBatch(BaseModel):
    device_id: str
    batch_size: int
    telemetry: List[TelemetryItem]

class FaultRequest(BaseModel):
    sensor_id: int
    fault_type: str
    duration_sec: float = 5.0

# API Key Dependency
def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key

latest_cache = {}

@app.post("/api/v1/telemetry")
def ingest_telemetry(batch: TelemetryBatch, api_key: str = Depends(verify_api_key)):
    global latest_cache
    conn = get_db_connection()
    c = conn.cursor()

    for t in batch.telemetry:
        latest_cache[t.sensor_id] = {
            "sensor_id": t.sensor_id,
            "name": t.name,
            "type": t.type,
            "value": round(t.value, 2),
            "unit": t.unit,
            "timestamp_ns": t.timestamp_ns,
            "seq_num": t.seq_num,
            "status_flags": t.status_flags,
            "state": t.state,
            "z_score": round(t.z_score, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        c.execute("""
            INSERT INTO telemetry (sensor_id, name, type, value, unit, timestamp_ns, seq_num, status_flags, state, z_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (t.sensor_id, t.name, t.type, t.value, t.unit, t.timestamp_ns, t.seq_num, t.status_flags, t.state, t.z_score))

        if t.alert_severity in ("WARNING", "CRITICAL"):
            c.execute("""
                INSERT INTO alerts (sensor_id, severity, message)
                VALUES (?, ?, ?)
            """, (t.sensor_id, t.alert_severity, t.alert_message))

    conn.commit()
    conn.close()
    return {"status": "success", "ingested": len(batch.telemetry)}

@app.get("/api/v1/telemetry/latest")
def get_latest_telemetry():
    conn = get_db_connection()
    c = conn.cursor()
    results = []

    for sid in range(1, 7):
        if sid in latest_cache:
            results.append(latest_cache[sid])
            continue

        c.execute("""
            SELECT sensor_id, name, type, value, unit, timestamp_ns, seq_num, status_flags, state, z_score, created_at
            FROM telemetry
            WHERE sensor_id = ?
            ORDER BY id DESC LIMIT 1
        """, (int(sid),))
        row = c.fetchone()
        if row:
            results.append({
                "sensor_id": row[0],
                "name": row[1],
                "type": row[2],
                "value": round(row[3], 2),
                "unit": row[4],
                "timestamp_ns": row[5],
                "seq_num": row[6],
                "status_flags": row[7],
                "state": row[8],
                "z_score": round(row[9], 2),
                "timestamp": str(row[10])
            })
        else:
            sname, unit = struct_sensors[sid]
            results.append({
                "sensor_id": sid,
                "name": sname,
                "type": sname,
                "value": 0.0,
                "unit": unit,
                "timestamp_ns": 0,
                "seq_num": 0,
                "status_flags": 1,
                "state": "NORMAL",
                "z_score": 0.0,
                "timestamp": "N/A"
            })

    conn.close()
    return {"telemetry": results}

@app.get("/api/v1/telemetry/history")
def get_telemetry_history(sensor_id: int = 1, limit: int = 50):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, value, z_score, state, created_at
        FROM telemetry
        WHERE sensor_id = ?
        ORDER BY id DESC LIMIT ?
    """, (sensor_id, limit))
    rows = c.fetchall()
    conn.close()

    history = [
        {"id": r[0], "value": r[1], "z_score": r[2], "state": r[3], "timestamp": r[4]}
        for r in reversed(rows)
    ]
    return {"sensor_id": sensor_id, "history": history}

@app.get("/api/v1/alerts")
def get_alerts(limit: int = 20):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, sensor_id, severity, message, created_at
        FROM alerts
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()

    alerts = [
        {"id": r[0], "sensor_id": r[1], "severity": r[2], "message": r[3], "timestamp": r[4]}
        for r in rows
    ]
    return {"alerts": alerts}

@app.get("/api/v1/health")
def get_health():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM telemetry")
    total_telemetry = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM alerts")
    total_alerts = c.fetchone()[0]

    c.execute("SELECT state FROM telemetry ORDER BY id DESC LIMIT 1")
    last_state_row = c.fetchone()
    current_state = last_state_row[0] if last_state_row else "NORMAL"

    conn.close()
    return {
        "status": "healthy",
        "system_state": current_state,
        "total_records": total_telemetry,
        "total_alerts": total_alerts,
        "hardware_mode": "Simulated Hardware (HIL Mode)"
    }

@app.post("/api/v1/faults/inject")
def inject_fault(req: FaultRequest, api_key: str = Depends(verify_api_key)):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO fault_commands (sensor_id, fault_type, duration_sec)
        VALUES (?, ?, ?)
    """, (req.sensor_id, req.fault_type, req.duration_sec))
    conn.commit()
    conn.close()

    # Trigger directly on simulator if running locally
    try:
        from simulator.sensor_sim import sim_global
        if sim_global:
            sim_global.inject_fault(req.sensor_id, req.fault_type, req.duration_sec)
    except Exception:
        pass

    return {
        "status": "fault_queued",
        "sensor_id": req.sensor_id,
        "fault_type": req.fault_type,
        "duration_sec": req.duration_sec
    }

@app.get("/api/v1/faults/pending")
def get_pending_faults():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, sensor_id, fault_type, duration_sec FROM fault_commands WHERE executed = 0")
    rows = c.fetchall()
    c.execute("UPDATE fault_commands SET executed = 1 WHERE executed = 0")
    conn.commit()
    conn.close()

    faults = [
        {"id": r[0], "sensor_id": r[1], "fault_type": r[2], "duration_sec": r[3]}
        for r in rows
    ]
    return {"faults": faults}

# Serve Dashboard UI
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    dash_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")
    if os.path.exists(dash_path):
        with open(dash_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VSense-HIL Dashboard File Not Found</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
