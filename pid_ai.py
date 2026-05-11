from driver import Driver, HOST, PORT, opponent_action

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
        self._prev_opp_side = None
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
        downshift_rpm    = self.params.get("downshift_rpm", 9500)

        corner_factor = 1.0 + max(0, (80 - forward_range) / 80)

        target_offset, extra_brake = opponent_action(sensors, self.params, self._opp_state)

        if self._opp_state["side"] != self._prev_opp_side:
            self.integral = 0.0
            self._prev_opp_side = self._opp_state["side"]

        error = track_pos - target_offset
        self.integral += error
        self.integral = max(-2.0, min(2.0, self.integral))

        steer = (steer_kd * angle - steer_kp * error - steer_ki * self.integral) * corner_factor
        steer = max(-1.0, min(1.0, steer))

        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)
        max_accel = min(1.0, 0.3 + gear * 0.1)

        straight_throttle      = self.params.get("straight_throttle", 1.0)
        medium_corner_throttle = self.params.get("medium_corner_throttle", 0.85)
        tight_corner_throttle  = self.params.get("tight_corner_throttle", 0.5)

        if forward_range > 100:
            accel = max_accel * straight_throttle
        elif forward_range > 50:
            accel = max_accel * medium_corner_throttle
        else:
            accel = max_accel * tight_corner_throttle

        brake_emg_speed   = self.params.get("brake_emergency_speed", 50)
        brake_emg_range   = self.params.get("brake_emergency_range", 28)
        brake_emg_force   = self.params.get("brake_emergency_force", 0.85)
        brake_early_speed = self.params.get("brake_early_speed", 100)
        brake_early_range = self.params.get("brake_early_range", 110)
        brake_early_force = self.params.get("brake_early_force", 0.45)
        brake_hard_speed  = self.params.get("brake_hard_speed", 75)
        brake_hard_range  = self.params.get("brake_hard_range", 75)
        brake_hard_force  = self.params.get("brake_hard_force", 0.65)
        brake_soft_speed  = self.params.get("brake_soft_speed", 45)
        brake_soft_range  = self.params.get("brake_soft_range", 35)
        brake_soft_force  = self.params.get("brake_soft_force", 0.3)
        centered_thresh   = self.params.get("centered_threshold", 0.5)

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

        brake = max(brake, extra_brake)

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
