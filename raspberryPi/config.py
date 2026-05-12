# config.py

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

TOPIC_RACE_STATE = "race/state"
TOPIC_RACE_TELEMETRY = "race/telemetry"
TOPIC_RACE_CONTROL = "race/control"
TOPIC_PI_STATUS = "pi/status"

DEVICE_STATUS = {
    "device": "raspberry_pi_4",
    "status": "online",
    "role": "warp_core_controller"
}

VALID_RACE_STATES = {
    "idle",
    "ready",
    "countdown",
    "racing",
    "finished",
    "error"
}