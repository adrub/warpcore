# IBM Racing Simulation Platform

AI-driven racing simulation built on TORCS — Python AI drivers, automated race orchestration, and a Mission Control web interface.

<!-- Record with: peek / kazam on Linux, or ShareX on Windows capturing the WSL window.
     Suggested capture: boot sequence → add a driver → launch race → hyperspace → live telemetry.
     Save the recording as docs/demo.gif then remove this comment. -->
![Mission Control demo](docs/demo.gif)

---

## What is this?

A TORCS-based racing simulation platform where configurable AI drivers compete on track. A Flask web server acts as Mission Control — managing driver configuration, launching races automatically, and displaying live telemetry. Two AI driver types are included out of the box, and external drivers can be dropped in without modifying the platform.

---

## Features

- **Mission Control UI** — IBM terminal-style web interface for configuring and launching races
- **Two AI drivers** — SimpleAI (proportional steering) and PidAI (full PID controller)
- **Automated race launch** — configures TORCS and starts all driver processes in one click
- **Live telemetry** — speed, gear, RPM, lap times, and race position updated every second
- **Race history** — lap-by-lap record with best lap highlighting
- **Hyperspace launch sequence** — cinematic warp effect on race start
- **External driver support** — drop a script into `plugins/` and it appears as a driver type

---

## Quick Start

> **Prerequisite:** TORCS must be installed first — see the [Installation Guide](docs/installation.md).

```bash
# Clone the repo
git clone https://github.com/adrub/warpcore.git
cd warpcore

# Install Python dependency
pip install flask

# Start Mission Control
python3 client.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

From there: add drivers, configure parameters, and click **Launch Race** — TORCS and all driver processes start automatically.

---

## Drivers

| Driver | Description |
|---|---|
| **SimpleAI** | Proportional steering on track position and angle. Multi-tier braking logic. |
| **PidAI** | Full PID steering controller with integral windup clamp. Early braking tier. |

Both drivers support tunable parameters via the UI sliders, saved profiles, and opponent avoidance behaviour.

**External drivers:** participants can bring their own AI by dropping a Python script into `plugins/`. See [docs/external_drivers.md](docs/external_drivers.md) for the interface contract.

---

## Project Structure

```
warpcore/
├── client.py              # Flask server — race orchestration, telemetry, UI backend
├── driver.py              # Base Driver class — TORCS UDP protocol, telemetry
├── simple_ai.py           # SimpleAI driver
├── pid_ai.py              # PidAI driver
├── templates/
│   └── index.html         # Mission Control frontend
├── plugins/               # Drop external driver scripts here
└── docs/
    ├── installation.md    # TORCS setup guide
    └── external_drivers.md # External driver interface spec
```

---

## Installation

Full TORCS setup (WSL2, dependencies, compile, install): [docs/installation.md](docs/installation.md)
