from driver import Driver

GEAR_RATIOS = [3.9, 2.9, 2.3, 1.87, 1.68, 1.54, 1.46]
REDLINE = 18700
UPSHIFT_THRESHOLD = 0.9   
DOWNSHIFT_RPM = 8000       

def gearbox(rpm, gear):
    if gear <= 0:
        return 1

    # Upshift: current RPM is near redline
    if gear < len(GEAR_RATIOS) and rpm > REDLINE * UPSHIFT_THRESHOLD:
        return gear + 1

    # Downshift: current RPM is too low
    if gear > 1 and rpm < DOWNSHIFT_RPM:
        rpm_if_down = rpm * (GEAR_RATIOS[gear - 2] / GEAR_RATIOS[gear - 1])
        if rpm_if_down < REDLINE:
            return gear - 1

    return gear


class SimpleAI(Driver):
    def decide(self, sensors):
        speed = sensors.get("speedX", 0)
        track_pos = sensors.get("trackPos", 0)
        rpm = sensors.get("rpm", 0)
        gear = int(sensors.get("gear", 1))

        angle = sensors.get("angle", 0)
        track = sensors.get("track", [100] * 19)
        forward_range = track[9]

        # Corner Handling
        corner_factor = 1.0 + max(0, (80 - forward_range) / 80)
        steer = max(-1.0, min(1.0, angle * 0.5 * corner_factor - track_pos * 0.3 * corner_factor))

        # Gear Shifts
        gear = gearbox(rpm, gear)

        # Avoid Spin Out
        max_accel = min(1.0, 0.3 + gear * 0.1)

        if forward_range > 100:
            accel = max_accel
        elif forward_range > 50:
            accel = max_accel * 0.7
        else:
            accel = max_accel * 0.35

        if speed > 120 and forward_range < 55:
            brake = 0.5
        elif speed > 80 and forward_range < 35:
            brake = 0.3
        else:
            brake = 0

        return accel, brake, steer, gear


if __name__ == "__main__":
    SimpleAI().run()
