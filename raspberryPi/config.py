# config.py

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

TOPIC_RACE_STATE = "race/state"
TOPIC_RACE_TELEMETRY = "race/telemetry"
TOPIC_RACE_CONTROL = "race/control"
TOPIC_PI_STATUS = "pi/status"

LED_COUNT      = 144
LED_PIN        = 18
LED_FREQ_HZ    = 800_000
LED_DMA        = 10
LED_BRIGHTNESS = 180
LED_INVERT     = False
LED_CHANNEL    = 0

BUTTON_PIN_START = 17
BUTTON_PIN_RESET = 27
BUTTON_DEBOUNCE_MS = 250 

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