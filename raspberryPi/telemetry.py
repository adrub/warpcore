# telemetry.py


class TelemetryHandler:
    def __init__(self):
        self.latest_telemetry = {}

    def handle_telemetry(self, payload):
        self.latest_telemetry = payload

        car = payload.get("car", "unknown")
        speed = payload.get("speed", 0)
        lap = payload.get("lap", 0)
        position = payload.get("position", 0)

        print(
            f"[TELEMETRY] Car={car}, "
            f"Speed={speed}, "
            f"Lap={lap}, "
            f"Position={position}"
        )