# mqtt_client.py

import json
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER,
    MQTT_PORT,
    TOPIC_RACE_STATE,
    TOPIC_RACE_TELEMETRY,
    TOPIC_RACE_CONTROL,
    TOPIC_PI_STATUS,
    DEVICE_STATUS,
)


class PiMQTTClient:
    def __init__(self, state_machine, telemetry_handler):
        self.state_machine = state_machine
        self.telemetry_handler = telemetry_handler

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def connect(self):
        print(f"[MQTT] Connecting to broker {MQTT_BROKER}:{MQTT_PORT}")
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.client.loop_start()

    def disconnect(self):
        print("[MQTT] Disconnecting")
        self.client.loop_stop()
        self.client.disconnect()

    def publish_control(self, command):
        message = {
            "source": "raspberry_pi",
            "command": command
        }
        self.client.publish(TOPIC_RACE_CONTROL, json.dumps(message))
        print(f"[MQTT] Published control: {message}")

    def publish_status(self):
        self.client.publish(TOPIC_PI_STATUS, json.dumps(DEVICE_STATUS))
        print(f"[MQTT] Published status: {DEVICE_STATUS}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"[MQTT] Connected with code: {reason_code}")

        client.subscribe(TOPIC_RACE_STATE)
        client.subscribe(TOPIC_RACE_TELEMETRY)

        self.publish_status()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"[MQTT] Invalid JSON on topic {msg.topic}: {msg.payload}")
            return

        if msg.topic == TOPIC_RACE_STATE:
            state = payload.get("state", "unknown")
            self.state_machine.set_state(state)

        elif msg.topic == TOPIC_RACE_TELEMETRY:
            self.telemetry_handler.handle_telemetry(payload)

        else:
            print(f"[MQTT] Unknown topic {msg.topic}: {payload}")