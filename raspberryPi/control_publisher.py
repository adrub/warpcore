# control_publisher.py


class ControlPublisher:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client

    def send_command(self, command):
        valid_commands = {"start", "reset", "idle"}

        if command not in valid_commands:
            print(f"[CONTROL] Invalid command: {command}")
            return

        self.mqtt_client.publish_control(command)