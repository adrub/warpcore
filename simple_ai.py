from driver import Driver


class SimpleAI(Driver):
    def decide(self, sensors):
        speed = sensors.get("speedX", 0)
        track_pos = sensors.get("trackPos", 0)
        rpm = sensors.get("rpm", 0)
        gear = int(sensors.get("gear", 1))

        # angle = which way car is pointing relative to track (0 = straight ahead)
        # trackPos = where car is on track (-1 left edge, 0 center, +1 right edge)
        # angle aligns the nose, trackPos corrects position — both needed to avoid oscillation
        angle = sensors.get("angle", 0)
        steer = max(-1.0, min(1.0, angle * 0.5 - track_pos * 0.3))

        if rpm > 8000 and gear < 6:
            gear += 1
        elif rpm < 2500 and gear > 1:
            gear -= 1

        track = sensors.get("track", [100] * 19)
        forward_range = min(track[7:12])

        if forward_range > 150:
            target = 200
        elif forward_range > 80:
            target = 140
        elif forward_range > 40:
            target = 90
        else:
            target = 60

        if speed > target + 5:
            accel = 0
            brake = min(1.0, (speed - target) / 20)
        elif speed < target - 10:
            accel = 1.0
            brake = 0
        else:
            accel = 0.3
            brake = 0

        return accel, brake, steer, gear


if __name__ == "__main__":
    SimpleAI().run()
