#Load and save the JSON files that hold race config, profiles, and lap history

import json
import os

from . import state
from .config import CONFIG_FILE, PROFILES_FILE, HISTORY_FILE, DEFAULT_SIMPLE

# Reads saved car config from disk into state - backfills missing slider values for older saves
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return
    with open(CONFIG_FILE) as f:
        state.race_config = json.load(f)
    # Older saved configs may not have the "simple" slider dict - fill it in so the UI works
    for car in state.race_config:
        if "simple" not in car:
            car["simple"] = dict(DEFAULT_SIMPLE.get(car.get("type", ""), {}))

# Saves current car config and values
def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(state.race_config, f, indent=2)

# Reads saved driver profiles and loads them
def load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            state.profiles = json.load(f)
    state.profiles.setdefault("pid_ai", {})
    state.profiles.setdefault("simple_ai", {})

# Saves driver profiles
def save_profiles():
    with open(PROFILES_FILE, "w") as f:
        json.dump(state.profiles, f, indent=2)

# Loads race history
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            state.race_history = json.load(f)

# Saves race history
def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(state.race_history, f, indent=2)
