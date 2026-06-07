# Example external driver plugin.
#
# Drop a file named "<something>_ai.py" into plugins/ that defines a Driver subclass with a
# decide() method, and the platform auto-detects it, assigns a port and colour, and races it.
# A plugin is just a normal driver that happens to live in plugins/ - there is nothing else to
# learn: same Driver base class, same decide() signature, same run_driver() entry point as the
# built-in drivers.
#
# decide(self, sensors) is called ~50 times a second. `sensors` is the full reading dict from
# TORCS (all 22 single values + 4 arrays - angle, speedX, track, opponents, wheelSpinVel, focus,
# ...). Use sensors.get(key, default) since a given key may be absent on a tick. Return the
# controls as a tuple in this order: (accel, brake, steer, gear).
#
# Test it standalone (TORCS must be running with a free slot):
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

        # Steering: hold the centre line (positive steer = left).
        steer = angle * 0.8 - track_pos * 0.5
        steer = max(-1.0, min(1.0, steer))

        # Speed: ease off as a corner approaches. track[9] is the dead-ahead beam.
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

        # Gear shifting via the framework helper (you manage your own gears).
        gear = gearbox(rpm, gear, upshift_threshold=0.85, downshift_rpm=8000)

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(ExampleAI, default_name="ExampleAI")
