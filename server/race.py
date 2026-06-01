# Race start / stop logic + MQTT connection for PI commands 

import json
import os
import subprocess
import sys
import threading
import time

from . import state
from .config import DRIVER_FILES, TELEMETRY_PORT
from .torcs_control import assign_ports, patch_quickrace_xml, autostart_torcs, quit_torcs, patch_car_colors

# Sends race state updates to the PI so it can trigger LED effects at the right time
def publish_race_states():
    if not state.mqtt_bridge:
        return
    state.mqtt_bridge.publish_state("ready")
    time.sleep(1)
    state.mqtt_bridge.publish_state("countdown")
    time.sleep(3)
    state.mqtt_bridge.publish_state("racing")

# Launches TORCS and spawns a subprocess for each AI driver in the race config then starts
def do_launch():
    if state.procs or not state.race_config:
        return False
    assign_ports()
    patch_quickrace_xml(len(state.race_config))
    patch_car_colors(state.race_config)

    # First entry in procs is always TORCS itself
    state.procs.append(subprocess.Popen(["torcs"]))
    threading.Thread(target=autostart_torcs, daemon=True).start()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    n_cars = len(state.race_config)
    for i, car in enumerate(state.race_config):
        # Drivers learn where to send telemetry via this --params extra field
        params = dict(car["params"])
        params["telemetry_port"] = TELEMETRY_PORT
        # Spread each car's preferred line across the track width (evenly by field size) so they
        # don't all stack on the identical apex line - reduces same-line collisions in traffic.
        params["lane_bias"] = (-0.5 + 1.0 * i / (n_cars - 1)) if n_cars > 1 else 0.0
        cmd = [
            sys.executable, "-u",
            os.path.join(base_dir, DRIVER_FILES[car["type"]]),
            "--port", str(car["port"]),
            "--name", car["name"],
            "--params", json.dumps(params),
        ]
        state.procs.append(subprocess.Popen(cmd))

    threading.Thread(target=publish_race_states, daemon=True).start()
    return True

#Exits TORCS and kills all driver subprocesses, clears telemetry, and notifies the Pi we are now in IDLE state
def do_stop():
    quit_torcs()
    for p in state.procs:
        try:
            p.kill()
        except Exception:
            pass
    state.procs.clear()
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
