# Storres data and states

import threading

# List of car dicts from the UI - {"name", "type", "params", "simple", "port"}
race_config = []

# subprocess.Popen handles - first is TORCS itself, rest are AI driver processes
procs = []

# Live telemetry indexed by car name - latest packet from each driver
telemetry = {}

# Lap-by-lap record persisted to disk
race_history = []

# Named profiles keyed by driver type then profile name
profiles = {"pid_ai": {}, "simple_ai": {}, "stanley_ai": {}}

# Lock protecting telemetry/race_history reads/writes between the UDP thread and routes
lock = threading.Lock()

# Per-car tick counter used to throttle telemetry forwarding to MQTT (every 5th packet)
tel_ticks = {}

# MQTTBridge instance created at startup, or None if disabled / not configured
mqtt_bridge = None

# True once a car has completed the race distance - drives the "finished" Pi state
finished = False
