# Example external driver plugin.

# Test it standalone:
#   python plugins/example_ai.py --port 3001 --name Example

from driver import Driver
from driver_utils import run_driver, gearbox


class ExampleAI(Driver):

    def decide(self, sensors):
        angle     = sensors.get("angle", 0.0)
        track_pos = sensors.get("trackPos", 0.0)
        speed     = sensors.get("speedX", 0.0)
        track     = sensors.get("track", [200.0] * 19)
        rpm       = sensors.get("rpm", 0.0)
        gear      = int(sensors.get("gear", 1))

        steer = angle * 0.8 - track_pos * 0.5
        steer = max(-1.0, min(1.0, steer))
        front = track[9]
        target_speed = 200
        if   front < 50:  target_speed = 80
        elif front < 100: target_speed = 120
        elif front < 150: target_speed = 160

        accel, brake = 0.0, 0.0
        if speed < target_speed:
            accel = 1.0
        else:
            brake = min(1.0, (speed - target_speed) / 50.0)

        gear = gearbox(rpm, gear, upshift_threshold=0.85, downshift_rpm=8000)

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(ExampleAI, default_name="ExampleAI")
