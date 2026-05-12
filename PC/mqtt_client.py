import json
import paho.mqtt.client as mqtt


class WarpCoreMQTTClient:
    def __init__(self, broker_ip="172.20.10.4", port=1883):
        self.broker_ip = broker_ip
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.command_callback = None

    def set_command_callback(self, callback):
        self.command_callback = callback

    def connect(self):
        print(f"Connecting to MQTT broker at {self.broker_ip}:{self.port}")
        self.client.connect(self.broker_ip, self.port, keepalive=60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"Connected to MQTT broker: {reason_code}")
        client.subscribe("race/control")
        client.subscribe("pi/status")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"Invalid JSON on {msg.topic}")
            return

        print(f"Received {msg.topic}: {payload}")

        if msg.topic == "race/control":
            command = payload.get("command")
            if self.command_callback:
                self.command_callback(command)

    def publish_state(self, state):
        message = {"state": state}
        self.client.publish("race/state", json.dumps(message))
        print(f"Published race/state: {message}")

    def publish_telemetry(self, telemetry):
        self.client.publish("race/telemetry", json.dumps(telemetry))
        print(f"Published race/telemetry: {telemetry}")