import json
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883

TOPIC_RACE_STATE = "race/state"
TOPIC_RACE_TELEMETRY = "race/telemetry"
TOPIC_PI_STATUS = "pi/status"


def handle_race_state(payload):
    """
    Expected payload examples:
    {"state": "idle"}
    {"state": "ready"}
    {"state": "countdown"}
    {"state": "racing"}
    {"state": "finished"}
    {"state": "error"}
    """
    state = payload.get("state", "unknown")
    print(f"[RACE STATE] {state}")

    if state == "idle":
        print("LED effect: slow pulse")
    elif state == "ready":
        print("LED effect: steady blue/white glow")
    elif state == "countdown":
        print("LED effect: countdown flash")
    elif state == "racing":
        print("LED effect: fast warp animation")
    elif state == "finished":
        print("LED effect: celebration flash")
    elif state == "error":
        print("LED effect: warning/error flash")
    else:
        print("LED effect: unknown/default")


def handle_telemetry(payload):
    """
    Expected payload example:
    {
        "car": "AI_1",
        "speed": 120.5,
        "lap": 2,
        "position": 1
    }
    """
    car = payload.get("car", "unknown")
    speed = payload.get("speed", 0)
    lap = payload.get("lap", 0)
    position = payload.get("position", 0)

    print(f"[TELEMETRY] Car={car}, Speed={speed}, Lap={lap}, Position={position}")


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Connected to MQTT broker with code: {reason_code}")

    client.subscribe(TOPIC_RACE_STATE)
    client.subscribe(TOPIC_RACE_TELEMETRY)

    status_msg = {
        "device": "raspberry_pi_4",
        "status": "online",
        "role": "warp_core_controller"
    }

    client.publish(TOPIC_PI_STATUS, json.dumps(status_msg))


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON on topic {msg.topic}: {msg.payload}")
        return

    if msg.topic == TOPIC_RACE_STATE:
        handle_race_state(payload)

    elif msg.topic == TOPIC_RACE_TELEMETRY:
        handle_telemetry(payload)

    else:
        print(f"[UNKNOWN TOPIC] {msg.topic}: {payload}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT broker...")
    client.connect(BROKER, PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping MQTT receiver...")
        client.disconnect()


if __name__ == "__main__":
    main()
