# Auto-discovery of external driver plugins dropped into the plugins/ folder.

import os

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")

# Colours assigned to plugin cars by grid slot
_PALETTE = ['#ff0000', '#0000ff', '#00cc00', '#ffcc00', '#cc00cc',
            '#00cccc', '#ff6600', '#ffffff', '#ff69b4', '#888888']


# A plugin is detected by two things only: its filename ends in "_ai.py" (the convention that
# marks the top-level, runnable driver file) and its text contains "def decide". The decide check
# is a plain text read - no import, no code execution at scan time - so a helper file or a stray
# .py never becomes a phantom grid slot that never connects and stalls the race.
def _looks_like_driver(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except OSError:
        return False
    return "def decide" in src


# Scans plugins/ and returns a "car" dict for each driver file found, with a port and colour
# assigned by grid slot. `start_index` is the number of configured cars, so plugins are numbered
# after them. Only files named "<name>_ai.py" that define a decide() are picked up; files starting
# with "_" (e.g. __init__.py) and helper files alongside the driver are ignored.
def discover_plugins(start_index=0):
    cars = []
    if not os.path.isdir(PLUGINS_DIR):
        return cars
    files = sorted(f for f in os.listdir(PLUGINS_DIR)
                   if f.endswith("_ai.py") and not f.startswith("_")
                   and _looks_like_driver(os.path.join(PLUGINS_DIR, f)))
    for j, fname in enumerate(files):
        slot = start_index + j
        cars.append({
            "name":  fname[:-3],
            "type":  "plugin",
            "file":  os.path.join("plugins", fname),
            "port":  3001 + slot,
            "color": _PALETTE[slot % len(_PALETTE)],
        })
    return cars
