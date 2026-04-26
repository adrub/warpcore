from driver import Driver


class SimpleAI(Driver):
    def decide(self, sensors):
        speed = sensors.get("speedX", 0)
        track_pos = sensors.get("trackPos", 0)
        rpm = sensors.get("rpm", 0)
        gear = int(sensors.get("gear", 1))

        angle = sensors.get("angle", 0)
        track = sensors.get("track", [100] * 19)
        forward_range = track[9]

        # Tighter corner (small forward_range) = boost steering gains
        corner_factor = 1.0 + max(0, (80 - forward_range) / 80)
        steer = max(-1.0, min(1.0, angle * 0.5 * corner_factor - track_pos * 0.3 * corner_factor))

        # Gear shifting
        if rpm > 8000 and gear < 6:
            gear += 1
        elif rpm < 2500 and gear > 1:
            gear -= 1

        if forward_range > 100:
            accel = 1.0
        elif forward_range > 50:
            accel = 0.5
        else:
            accel = 0.0

        # Graduated braking: start earlier and brake harder as corner tightens
        if speed > 80 and forward_range < 80:
            brake = 0.8
        elif speed > 50 and forward_range < 50:
            brake = 0.6
        else:
            brake = 0

        return accel, brake, steer, gear


if __name__ == "__main__":
    SimpleAI().run()
