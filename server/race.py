# Race start / stop logic + MQTT connection for PI commands 

import json
import os
import shutil
import subprocess
import sys
import threading
import time

from . import state
from .config import DRIVER_FILES, TELEMETRY_PORT, RACE_LAPS
from .torcs_control import assign_ports, patch_quickrace_xml, autostart_torcs, quit_torcs, patch_car_colors
from .plugins import discover_plugins

# Sends race state updates to the PI so it can trigger LED effects at the right time
def publish_race_states():
    if not state.mqtt_bridge:
        return
    state.mqtt_bridge.publish_state("ready")
    time.sleep(1)
    state.mqtt_bridge.publish_state("countdown")
    time.sleep(3)
    state.mqtt_bridge.publish_state("racing")

# Watches lap counts; once a car completes the race distance, tell the Pi the race is finished.
# Reuses the per-car `laps` counter the telemetry server maintains. Exits when do_stop() clears procs.
def race_monitor():
    while state.procs:
        time.sleep(1.0)
        with state.lock:
            laps = [c.get("laps", 0) for c in state.telemetry.values()]
        if laps and max(laps) >= RACE_LAPS:
            if state.mqtt_bridge:
                state.mqtt_bridge.publish_state("finished")
            state.finished = True
            print(f"[race] finished - a car reached {RACE_LAPS} lap(s)")
            return

# Launches TORCS and spawns a subprocess for each AI driver in the race config then starts.
# The grid is the configured cars plus any auto-detected plugins from the plugins/ folder.
def do_launch():
    if state.procs:
        return False, "Race already running."
    assign_ports()
    # Plugins are numbered onto the grid after the configured cars
    plugins = discover_plugins(len(state.race_config))
    grid = list(state.race_config) + plugins
    if not grid:
        return False, "No cars configured - add at least one driver."
    if not shutil.which("torcs"):
        return False, "TORCS not found on PATH - is it installed?"
    try:
        patch_quickrace_xml(len(grid))
        patch_car_colors(grid)
    except Exception as e:
        return False, f"Failed to configure the race: {e}"
    try:
        # First entry in procs is always TORCS itself
        state.procs.append(subprocess.Popen(["torcs"]))
    except Exception as e:
        return False, f"Could not launch TORCS: {e}"
    threading.Thread(target=autostart_torcs, daemon=True).start()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Plugin files in plugins/ import the framework (driver, driver_utils) - put the project root
    # on PYTHONPATH so those imports resolve when the plugin is launched from its own folder.
    env = dict(os.environ)
    env["PYTHONPATH"] = base_dir + os.pathsep + env.get("PYTHONPATH", "")

    n_cars = len(grid)
    failures = []
    for i, car in enumerate(grid):
        # Remote (Pi-hosted) drivers run on the Pi - we only reserve their grid slot, port and
        # colour here; the Pi connects to TORCS over the network itself.
        if car.get("type") == "remote":
            continue
        # Drivers learn where to send telemetry via this --params extra field
        params = dict(car.get("params", {}))
        params["telemetry_port"] = TELEMETRY_PORT
        # Spread each car's preferred line across the track width (evenly by field size) so they
        # don't all stack on the identical apex line - reduces same-line collisions in traffic.
        params["lane_bias"] = (-0.5 + 1.0 * i / (n_cars - 1)) if n_cars > 1 else 0.0
        # Plugins and configured cars are the same kind of thing - a driver file with its own
        # __main__/run_driver entry point. They differ only in where the file lives: a plugin
        # carries its own path in car["file"], a configured car looks its file up in DRIVER_FILES.
        rel = car["file"] if car.get("type") == "plugin" else DRIVER_FILES[car["type"]]
        cmd = [
            sys.executable, "-u",
            os.path.join(base_dir, rel),
            "--port", str(car["port"]),
            "--name", car["name"],
            "--params", json.dumps(params),
        ]
        try:
            state.procs.append(subprocess.Popen(cmd, env=env))
        except Exception as e:
            failures.append(f"{car['name']}: {e}")

    state.finished = False
    threading.Thread(target=publish_race_states, daemon=True).start()
    threading.Thread(target=race_monitor, daemon=True).start()
    if failures:
        return True, "Race started, but some drivers failed to launch: " + "; ".join(failures)
    return True, "Race started."

#Exits TORCS and kills all driver subprocesses, clears telemetry, and notifies the Pi we are now in IDLE state
def do_stop():
    quit_torcs()
    for p in state.procs:
        try:
            p.kill()
        except Exception:
            pass
    state.procs.clear()
    state.finished = False
    with state.lock:
        state.telemetry.clear()
    if state.mqtt_bridge:
        state.mqtt_bridge.publish_state("idle")

# Routes button commands received from the PI over MQTT to launch or stop the race
def handle_pi_command(command: str):
    print(f"[MQTT] Pi command: {command}")
    if command == "start":
        do_launch()
    elif command in ("reset", "idle"):
        do_stop()
