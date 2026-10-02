# Stage 4 – Prototype & End-to-End Implementation Report

**Project Title:** VSense-HIL: Virtual Sensor Telemetry Engine  
**Stage:** 4 (Implementation & Prototype)  
**Status:** Complete & Verified Live  
**Target Pipeline:** Virtual Device → Linux → Device Interface/Driver → C++ System Programming → Data Processing → Cloud → Database → Dashboard  

---

## 1. Prototype Overview & Localhost Deployment

The complete **VSense-HIL** telemetry engine is fully implemented, containerized, and running live on **localhost:8000**.

* **Dashboard Web UI:** [`http://localhost:8000`](http://localhost:8000)
* **OpenAPI Specs / Swagger Docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **Telemetry Query Endpoint:** [`http://localhost:8000/api/v1/telemetry/latest`](http://localhost:8000/api/v1/telemetry/latest)
* **Health & Diagnostics Endpoint:** [`http://localhost:8000/api/v1/health`](http://localhost:8000/api/v1/health)
* **Fault Injection API:** [`http://localhost:8000/api/v1/faults/inject`](http://localhost:8000/api/v1/faults/inject)

---

## 2. Implemented Modules Summary

### 2.1 Virtual Sensor Simulator (`simulator/sensor_sim.py`)
* Synthesizes 6 multi-modal sensor signals: Temperature, Humidity, Pressure, Vibration, Voltage, Current.
* Generates 40-byte binary `vsensor_sample_t` packets containing CRC16 checksums, sequence numbers, and UTC nanosecond timestamps.
* Supports live fault injection: `spike`, `stuck`, `dropout`, and `out_of_range`.

### 2.2 Linux Device Driver & Userspace Fallback (`driver/`)
* **Kernel Driver (`driver/vsensor.c`):** C Linux character device driver `/dev/vsensor0` featuring `hrtimer` interrupts, spinlock-protected ring buffer, wait queues, `/proc/vsensor` stats, and `ioctl` calls.
* **Userspace Fallback (`driver/vsensor_pty_emulator.py`):** PTY/FIFO fallback node (`vsensor0.fifo`) enabling zero-permission, cross-platform containerized execution.

### 2.3 C++ / Python Telemetry Daemon (`daemon/`)
* **Validator (`daemon/include/Validator.hpp`):** Verifies 0x56534E53 magic header, NaN/Inf checks, sequence monotonicity, and CRC16 validity.
* **Anomaly Engine (`daemon/include/AnomalyDetector.hpp`):** Maintains rolling Z-score & moving averages. Controls device state machine (`NORMAL` → `WARNING` → `CRITICAL` → `RECOVERY`).
* **Store-and-Forward Client (`daemon/include/StoreAndForward.hpp` & `CloudClient.hpp`):** Buffers telemetry locally during network outages and handles batched HTTP ingestion.

### 2.4 Cloud Backend & Database (`cloud-backend/main.py`)
* FastAPI application backed by SQLite database with WAL journal mode.
* Features API key authorization (`X-API-Key`), rate limiting, in-memory real-time telemetry caching, alert logging, and static dashboard serving.

### 2.5 Web Dashboard UI (`dashboard/index.html`)
* Modern dark-mode glassmorphism interface.
* Real-time Chart.js time-series plots, live gauge cards for all 6 sensors, state machine status badges, live alerts table, and interactive fault injection panel.

---

## 3. Verification & Live Execution Metrics

```text
[HTTP POST /api/v1/telemetry] Ingested 1,870+ records with 200 OK
[Anomaly Engine] 408+ System Alerts Logged
[CLI Fault Injection] Injected spike fault on Sensor #4 for 5.0 seconds -> Verified State Transition to WARNING/CRITICAL
```

---

*All hardware simulated for educational and system validation purposes.*
