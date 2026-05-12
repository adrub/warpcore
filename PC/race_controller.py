import time


class RaceController:
    def __init__(self, mqtt_client):
        self.mqtt = mqtt_client
        self.state = "idle"

    def set_state(self, state):
        self.state = state
        self.mqtt.publish_state(state)

    def start_race(self):
        print("Starting race sequence...")

        self.set_state("ready")
        time.sleep(1)

        self.set_state("countdown")
        time.sleep(3)

        self.set_state("racing")
        print("TORCS should launch/start race here.")

    def finish_race(self):
        print("Finishing race...")
        self.set_state("finished")

    def reset_race(self):
        print("Resetting race...")
        self.set_state("idle")

    def handle_pi_command(self, command):
        print(f"Command received from Pi: {command}")

        if command == "start":
            self.start_race()
        elif command == "reset":
            self.reset_race()
        elif command == "idle":
            self.set_state("idle")
        else:
            print(f"Unknown command: {command}")

    def send_fake_telemetry(self):
        telemetry = {
            "car": "AI_1",
            "speed": 132.7,
            "lap": 1,
            "position": 1
        }
        self.mqtt.publish_telemetry(telemetry)