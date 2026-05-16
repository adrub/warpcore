# Listens for UDP telemetry packets from AI drivers, tracks laps, and forwards data to the PI

import datetime
import json
import socket

from . import state
from .config import TELEMETRY_PORT
from .history import save_history

# Opens a UDP socket and processes incoming telemetry packets in an infinite loop
def telemetry_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Opens socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allows port to be reused
    sock.bind(("127.0.0.1", TELEMETRY_PORT)) # Sets to receive packets from any local driver
    while True:
        try:
            data, _ = sock.recvfrom(4096) 
            entry = json.loads(data.decode()) # Parses incoming packet as JSON
            name = entry["name"] 
            with state.lock:
                prev      = state.telemetry.get(name, {})
                prev_last = prev.get("last_lap", 0)
                new_last  = entry.get("last_lap", 0)

                # Preserve cumulative counters that don't come in every packet
                entry["laps"]     = prev.get("laps", 0)
                entry["best_lap"] = prev.get("best_lap", 0)

                # New lap detected: last_lap changed from previous packet to a non-zero value
                if new_last > 0 and new_last != prev_last:
                    entry["laps"] = prev.get("laps", 0) + 1
                    if entry["best_lap"] == 0 or new_last < entry["best_lap"]:
                        entry["best_lap"] = new_last
                    state.race_history.append({
                        "name": name,
                        "lap": entry["laps"],
                        "lap_time": round(new_last, 3),
                        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                    })
                    save_history()

                state.telemetry[name] = entry

                # Send MQTT eveery 5th packet
                state.tel_ticks[name] = state.tel_ticks.get(name, 0) + 1
                if state.mqtt_bridge and state.tel_ticks[name] % 5 == 0:
                    state.mqtt_bridge.publish_telemetry({
                        "car":      name,
                        "speed":    round(entry.get("speed", 0), 1),
                        "lap":      entry.get("laps", 0),
                        "position": entry.get("race_pos", 0),
                    })
        except Exception:
            # Malformed packets or transient socket errors - keep listening
            pass
