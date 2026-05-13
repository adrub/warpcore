# pi_control_publisher.py

import json
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883

TOPIC_CONTROL = "race/control"
TOPIC_PI_STATUS = "pi/status"


def publish_control(client, command):
    message = {
        "source": "raspberry_pi",
        "command": command,
        "timestamp": time.time()
    }

    client.publish(TOPIC_CONTROL, json.dumps(message))
    print(f"Published control command: {message}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    client.publish(TOPIC_PI_STATUS, json.dumps({
        "device": "raspberry_pi_4",
        "status": "control_publisher_online"
    }))

    print("Type a command: start, reset, idle, quit")

    try:
        while True:
            command = input("> ").strip().lower()

            if command == "quit":
                break

            if command in ["start", "reset", "idle"]:
                publish_control(client, command)
            else:
                print("Unknown command. Use: start, reset, idle, quit")

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
