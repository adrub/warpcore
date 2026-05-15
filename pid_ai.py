# PidAI - A PID-based driver with opponent awareness 

from driver import Driver, opponent_action
from driver_utils import gearbox, run_driver


class PidAI(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Integral term for the PID steering controller 
        self.integral = 0.0
        # Tracks which side of the car a passing opponent is on so we can reset the integral
        self._prev_opp_side = None

    #Takes in current sensor data from packet
    def decide(self, sensors):
        speed = sensors.get("speedX", 0)
        track_pos = sensors.get("trackPos", 0)
        rpm = sensors.get("rpm", 0)
        gear = int(sensors.get("gear", 1))
        angle = sensors.get("angle", 0)
        track = sensors.get("track", [100] * 19)
        forward_range = track[9]

        # PID params and gear shifting thresholds
        steer_kp          = self.params.get("steer_kp", 0.3)
        steer_ki          = self.params.get("steer_ki", 0.0)
        steer_kd          = self.params.get("steer_kd", 0.5)
        upshift_threshold = self.params.get("upshift_threshold", 0.9)
        downshift_rpm     = self.params.get("downshift_rpm", 9500)

        # Corner handling
        corner_factor = 1.0 + max(0, (80 - forward_range) / 80)

        # Opponent handling
        target_offset, extra_brake = opponent_action(sensors, self.params, self._opp_state)

        # Reset integral if another car overtakes
        if self._opp_state["side"] != self._prev_opp_side:
            self.integral = 0.0
            self._prev_opp_side = self._opp_state["side"]

        # Error between desired position (middle of track) and current position + offset
        error = track_pos - target_offset
        self.integral += error
        
        # Clamp integral to prevent runnaway
        self.integral = max(-2.0, min(2.0, self.integral))

        # Steering calculation 
        steer = (steer_kd * angle - steer_kp * error - steer_ki * self.integral) * corner_factor
        steer = max(-1.0, min(1.0, steer))

        # Gear shifting logic
        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)
        max_accel = min(1.0, 0.3 + gear * 0.1)

        # Acceleration params 
        straight_throttle      = self.params.get("straight_throttle", 1.0)
        medium_corner_throttle = self.params.get("medium_corner_throttle", 0.85)
        tight_corner_throttle  = self.params.get("tight_corner_throttle", 0.5)

        # Acceleration logic
        if forward_range > 100:
            accel = max_accel * straight_throttle
        elif forward_range > 50:
            accel = max_accel * medium_corner_throttle
        else:
            accel = max_accel * tight_corner_throttle

        # Braking params
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

        # Braking Logic
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
    run_driver(PidAI, default_name="PidAI")
