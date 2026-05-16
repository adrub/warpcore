# MQTT Broker Bridge between PC and PI

import json

try:
    import paho.mqtt.client as _paho
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class MQTTBridge:
    # State names must match the Pi's found in raspberryPi/config.py
    RACE_STATE     = "race/state"
    RACE_TELEMETRY = "race/telemetry"
    RACE_CONTROL   = "race/control"
    
    # Initialises MQTT and attempts to connect to broker
    def __init__(self, broker, port, command_callback):
        self._cb = command_callback
        self._client = _paho.Client(_paho.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        try:
            self._client.connect(broker, port, keepalive=60)
            self._client.loop_start()
        except Exception as e:
            print(f"[MQTT] Could not connect to broker: {e}")

    # Publishes current race state to the PI (idle/ready/countdown/racing/finished/error)
    def publish_state(self, state_name: str):
        try:
            self._client.publish(self.RACE_STATE, json.dumps({"state": state_name}))
        except Exception:
            pass
    
    # Sends telemetry data to PI
    def publish_telemetry(self, payload: dict):
        try:
            self._client.publish(self.RACE_TELEMETRY, json.dumps(payload))
        except Exception:
            pass

    # Confirms connection to PI
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"[MQTT] Connected to broker: {reason_code}")
        client.subscribe(self.RACE_CONTROL)


    def _on_message(self, client, userdata, msg):
        try:
            data    = json.loads(msg.payload.decode())
            command = data.get("command")
            if command:
                self._cb(command)
        except Exception:
            pass
