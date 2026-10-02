# Changelog

All notable changes to the **VSense-HIL: Virtual Sensor Telemetry Engine** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.4-stage4] - 2026-10-02

### Added
- Multi-modal Virtual Sensor Generator (`simulator/sensor_sim.py`).
- Linux Kernel Character Driver (`driver/vsensor.c`) and Userspace PTY Emulator Fallback (`driver/vsensor_pty_emulator.py`).
- C++ / Python Telemetry Daemon (`daemon/vsensord.py` & `daemon/src/main.cpp`) featuring Validator, Rolling Z-Score Anomaly Engine, and Store-and-Forward SQLite Buffer.
- `vsensorctl` Command-Line Control Utility (`cli/vsensorctl.py`).
- FastAPI Cloud Backend (`cloud-backend/main.py`) with API key auth, rate limiting, and SQLite WAL database.
- Modern Glassmorphism Web Dashboard (`dashboard/index.html`) with real-time Chart.js streaming, state badges, alert logs, and fault injection control panel.
- Orchestrator script (`scripts/run_all.py`) launching full pipeline on `http://localhost:8000`.

## [v0.1-stage1] - 2026-10-02

### Added
- Initial project structure and directory layout (`/driver`, `/simulator`, `/daemon`, `/cli`, `/cloud-backend`, `/dashboard`, `/tests`, `/docs`, `/scripts`, `/deploy`).
- Comprehensive Stage 1 Introduction document (`docs/01-introduction.md`).
- Master Implementation Plan artifact.
- Environment templates (`.env.example`) and `.gitignore`.
- Progress tracking log (`docs/progress-log.md`).
