# IoT-Embedded-Virtual-Sensor-Telemetry-System

[![Stage 1](https://img.shields.io/badge/Stage-1%20Completed-brightgreen)](#current-status)
[![OS](https://img.shields.io/badge/OS-Linux%20Ubuntu%2022.04%2F24.04-blue)](#technologies)
[![C++](https://img.shields.io/badge/C%2B%2B-17-orange)](#technologies)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)

> **Project Type:** Individual Project  
> **Domain:** IoT, Embedded Systems & Virtual Sensors
> **localhost:** https://cdn.corenexis.com/f/lwuHvpXaBpt.png

---

## 📌 Overview

**IoT-Embedded-Virtual-Sensor-Telemetry-System** is a software-based IoT and embedded project that simulates sensor hardware and builds a complete telemetry pipeline using **C++17, Linux, virtual sensors, and cloud services**.

### 🔄 System Flow

```text
Virtual Sensor
      ↓
Linux Driver / PTY
      ↓
C++17 Telemetry Daemon
      ↓
Anomaly Detection
      ↓
Store-and-Forward Client
      ↓
FastAPI Backend
      ↓
PostgreSQL / SQLite
      ↓
Live Web Dashboard

IoT-Embedded-Virtual-Sensor-Telemetry-System/
│
├── driver/
│   ├── vsensor.ko
│   └── pty-emulator/
│
├── simulator/
│   └── virtual-sensor-generator/
│
├── daemon/
│   └── vsensord/
│
├── cli/
│   └── vsensorctl/
│
├── cloud-backend/
│   └── FastAPI/
│
├── dashboard/
│   └── web-ui/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── system/
│
├── docs/
│   ├── 01-introduction.md
│   ├── architecture.md
│   └── progress-log.md
│
└── README.md


**Important:** The links like `docs/01-introduction.md` will work on GitHub **only if those files actually exist in your repository**.
