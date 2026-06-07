# PidAI - A PID-based driver with opponent awareness 

from driver import Driver, opponent_action
from driver_utils import (
    gearbox, run_driver, abs_brake, launch_control, traction_control, racing_line_offset,
    corner_throttle, gear_accel_limit, ramp_throttle,
)


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
        target_offset, extra_brake, throttle_scale = opponent_action(sensors, self.params, self._opp_state)
        # When no opponent is nearby, follow the racing line (inside/outside set by aggressiveness).
        # Ramp the lane bias in over the first 200m so cars hold their grid line at the start
        # instead of darting sideways across the track toward their assigned lane.
        apex_aggr = self.params.get("apex_aggressiveness", 0.6)
        lane_bias = self.params.get("lane_bias", 0.0) * min(1.0, sensors.get("distRaced", 0) / 200.0)
        if target_offset is None:
            target_offset = racing_line_offset(sensors, apex_aggr, lane_bias)

        # Reset integral if another car overtakes
        if self._opp_state["side"] != self._prev_opp_side:
            self.integral = 0.0
            self._prev_opp_side = self._opp_state["side"]

        # Error between desired position (middle of track) and current position + offset
        error = track_pos - target_offset
        self.integral += error

        # Clamp integral to prevent runaway
        self.integral = max(-2.0, min(2.0, self.integral))

        # Steering calculation
        steer = (steer_kd * angle - steer_kp * error - steer_ki * self.integral) * corner_factor
        # Dampen steering as speed rises to stop high-speed darting (no effect below ~54 km/h)
        speed_ms = speed / 3.6
        if speed_ms > 15.0:
            steer /= (1.0 + (speed_ms - 15.0) * 0.02)
        steer = max(-1.0, min(1.0, steer))

        # Gear shifting logic
        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)

        # Acceleration params
        straight_throttle      = self.params.get("straight_throttle", 1.0)
        medium_corner_throttle = self.params.get("medium_corner_throttle", 0.85)
        tight_corner_throttle  = self.params.get("tight_corner_throttle", 0.5)

        # Speed-relative corner detection picks the throttle target; gear limit guards low-gear
        # wheelspin; ramp smooths the change so throttle eases on rather than snapping.
        target_accel = corner_throttle(sensors, straight_throttle, medium_corner_throttle, tight_corner_throttle)
        target_accel *= gear_accel_limit(gear)
        accel = ramp_throttle(self.prev_accel, target_accel)
        self.prev_accel = accel

        # Launch control - full throttle in gear 1 for first 2 seconds
        accel, gear = launch_control(sensors, accel, gear)

        # Ease off if closing on a car ahead (also moderates the launch so we don't ram the grid)
        accel *= throttle_scale

        # Traction control - cuts throttle when wheels spin faster than ground speed allows
        accel = traction_control(accel, sensors, self.params.get("tc_slip", 1.4))

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

        # Braking Logic - brakes for the corner regardless of track position
        if speed > brake_emg_speed and forward_range < brake_emg_range:
            brake = brake_emg_force
        elif speed > brake_early_speed and forward_range < brake_early_range:
            brake = brake_early_force
        elif speed > brake_hard_speed and forward_range < brake_hard_range:
            brake = brake_hard_force
        elif speed > brake_soft_speed and forward_range < brake_soft_range:
            brake = brake_soft_force
        else:
            brake = 0

        brake = max(brake, extra_brake)

        # ABS - pulse brake pressure on wheel lockup
        brake = abs_brake(brake, sensors)

        # Don't accelerate and brake on the same tick (ignore a negligible brake)
        if brake > 0.05:
            accel = 0.0

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(PidAI, default_name="PidAI")
