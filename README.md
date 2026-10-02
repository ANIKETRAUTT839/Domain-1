# VSense-HIL: Virtual Sensor Telemetry Engine

[![Stage 1 Completed](https://img.shields.io/badge/Stage-1%20Completed-brightgreen)](#)
[![Target OS](https://img.shields.io/badge/Target%20OS-Linux%20Ubuntu%2022.04%2F24.04-blue)](#)
[![C++ Standard](https://img.shields.io/badge/C%2B%2B-17-orange)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](#)

> **Simulated Hardware Notice:** All sensor hardware in VSense-HIL is synthesized and simulated in software for Hardware-in-the-Loop (HIL) telemetry testing and academic evaluation.

---

## Overview
**VSense-HIL** is an end-to-end, high-performance Hardware-in-the-Loop (HIL) Telemetry Engine. It demonstrates the complete embedded telemetry pipeline:

```text
Virtual Sensor Generator ➔ Linux Kernel / PTY Driver ➔ C++17 vsensord Daemon ➔ Anomaly Engine ➔ Store-and-Forward Cloud Client ➔ FastAPI Backend ➔ PostgreSQL/SQLite DB ➔ Live Web Dashboard
```

---

## Directory Structure
* [`/driver`](file:///c:/Users/win11/Desktop/Domain%201/driver): Linux kernel character driver `vsensor.ko` and userspace PTY emulator fallback.
* [`/simulator`](file:///c:/Users/win11/Desktop/Domain%201/simulator): Multi-modal virtual sensor signal generator (baseline, drift, noise, fault injection).
* [`/daemon`](file:///c:/Users/win11/Desktop/Domain%201/daemon): `vsensord` C++17 telemetry service with non-blocking epoll reader, thread-safe bounded queue, and anomaly detection.
* [`/cli`](file:///c:/Users/win11/Desktop/Domain%201/cli): `vsensorctl` Unix domain socket command-line tool.
* [`/cloud-backend`](file:///c:/Users/win11/Desktop/Domain%201/cloud-backend): FastAPI REST API backend with API key auth, rate limiting, and database models.
* [`/dashboard`](file:///c:/Users/win11/Desktop/Domain%201/dashboard): Web dashboard UI with live charts and real-time status badges.
* [`/tests`](file:///c:/Users/win11/Desktop/Domain%201/tests): Unit, integration, and system test suites (GoogleTest, pytest, fault scripts).
* [`/docs`](file:///c:/Users/win11/Desktop/Domain%201/docs): Stage documentation, architectural diagrams, PRD, and test reports.

---

## Current Status
- **Stage 1 (Project Introduction):** Completed & Tagged `v0.1-stage1`. See [docs/01-introduction.md](file:///c:/Users/win11/Desktop/Domain%201/docs/01-introduction.md) and [docs/progress-log.md](file:///c:/Users/win11/Desktop/Domain%201/docs/progress-log.md).
