from driver import Driver, HOST, PORT

GEAR_RATIOS = [3.9, 2.9, 2.3, 1.87, 1.68, 1.54, 1.46]
REDLINE = 18700


def gearbox(rpm, gear, upshift_threshold, downshift_rpm):
    if gear <= 0:
        return 1
    if gear < len(GEAR_RATIOS) and rpm > REDLINE * upshift_threshold:
        return gear + 1
    if gear > 1 and rpm < downshift_rpm:
        rpm_if_down = rpm * (GEAR_RATIOS[gear - 2] / GEAR_RATIOS[gear - 1])
        if rpm_if_down < REDLINE:
            return gear - 1
    return gear


class PidAI(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.integral = 0.0

    def decide(self, sensors):
        speed = sensors.get("speedX", 0)
        track_pos = sensors.get("trackPos", 0)
        rpm = sensors.get("rpm", 0)
        gear = int(sensors.get("gear", 1))
        angle = sensors.get("angle", 0)
        track = sensors.get("track", [100] * 19)
        forward_range = track[9]

        steer_kp         = self.params.get("steer_kp", 0.3)
        steer_ki         = self.params.get("steer_ki", 0.0)
        steer_kd         = self.params.get("steer_kd", 0.5)
        upshift_threshold= self.params.get("upshift_threshold", 0.9)
        downshift_rpm    = self.params.get("downshift_rpm", 8000)

        corner_factor = 1.0 + max(0, (80 - forward_range) / 80)

        self.integral += track_pos
        self.integral = max(-2.0, min(2.0, self.integral))

        steer = (steer_kd * angle - steer_kp * track_pos - steer_ki * self.integral) * corner_factor
        steer = max(-1.0, min(1.0, steer))

        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)
        max_accel = min(1.0, 0.3 + gear * 0.1)

        if forward_range > 100:
            accel = max_accel
        elif forward_range > 50:
            accel = max_accel * 0.85
        else:
            accel = max_accel * 0.5

        brake_emg_speed   = self.params.get("brake_emergency_speed", 65)
        brake_emg_range   = self.params.get("brake_emergency_range", 18)
        brake_emg_force   = self.params.get("brake_emergency_force", 0.5)
        brake_early_speed = self.params.get("brake_early_speed", 130)
        brake_early_range = self.params.get("brake_early_range", 80)
        brake_early_force = self.params.get("brake_early_force", 0.25)
        brake_hard_speed  = self.params.get("brake_hard_speed", 100)
        brake_hard_range  = self.params.get("brake_hard_range", 55)
        brake_hard_force  = self.params.get("brake_hard_force", 0.35)
        brake_soft_speed  = self.params.get("brake_soft_speed", 55)
        brake_soft_range  = self.params.get("brake_soft_range", 25)
        brake_soft_force  = self.params.get("brake_soft_force", 0.2)
        centered_thresh   = self.params.get("centered_threshold", 0.3)

        centered = abs(track_pos) < centered_thresh

        if speed > brake_emg_speed and forward_range < brake_emg_range and centered:
            brake = brake_emg_force
        elif speed > brake_early_speed and forward_range < brake_early_range and centered:
            brake = brake_early_force
        elif speed > brake_hard_speed and forward_range < brake_hard_range and centered:
            brake = brake_hard_force
        elif speed > brake_soft_speed and forward_range < brake_soft_range and centered:
            brake = brake_soft_force
        else:
            brake = 0

        return accel, brake, steer, gear


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--name", default="PidAI")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()
    PidAI(host=args.host, port=args.port, name=args.name, params=json.loads(args.params)).run()
