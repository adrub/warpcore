# SimpleAI - A simple rule-based driver with opponent awareness

from driver import Driver, opponent_action
from driver_utils import (
    gearbox, run_driver, abs_brake, launch_control, traction_control, racing_line_offset,
    corner_throttle, gear_accel_limit, ramp_throttle,
)


class SimpleAI(Driver):

    #Takes in current sensor data from packet
    def decide(self, sensors):
        speed = sensors.get("speedX", 0)
        track_pos = sensors.get("trackPos", 0)
        rpm = sensors.get("rpm", 0)
        gear = int(sensors.get("gear", 1))
        angle = sensors.get("angle", 0)
        track = sensors.get("track", [100] * 19)
        forward_range = track[9]  # This sensor is straight ahead

        # Steering and gear shift parameters
        angle_gain        = self.params.get("angle_gain", 0.5)
        position_gain     = self.params.get("position_gain", 0.3)
        upshift_threshold = self.params.get("upshift_threshold", 0.9)
        downshift_rpm     = self.params.get("downshift_rpm", 8000)

        # Brake tier thresholds and aggressiveness - emergency is very aggro, soft least
        brake_emg_speed  = self.params.get("brake_emergency_speed", 50)
        brake_emg_range  = self.params.get("brake_emergency_range", 18)
        brake_emg_force  = self.params.get("brake_emergency_force", 0.85)
        brake_hard_speed = self.params.get("brake_hard_speed", 120)
        brake_hard_range = self.params.get("brake_hard_range", 55)
        brake_hard_force = self.params.get("brake_hard_force", 0.65)
        brake_soft_speed = self.params.get("brake_soft_speed", 80)
        brake_soft_range = self.params.get("brake_soft_range", 35)
        brake_soft_force = self.params.get("brake_soft_force", 0.4)

        # As car approaches corner increases steering and braking aggressiveness
        corner_factor = 1.0 + max(0, (80 - forward_range) / 80)

        # Avoiding other cars or overtaking requires offset to go around them - handled here
        target_offset, extra_brake, throttle_scale = opponent_action(sensors, self.params, self._opp_state)
        # When no opponent is nearby, follow the racing line (inside/outside set by aggressiveness).
        # Ramp the lane bias in over the first 200m so cars hold their grid line at the start
        # instead of darting sideways across the track toward their assigned lane.
        apex_aggr = self.params.get("apex_aggressiveness", 0.6)
        lane_bias = self.params.get("lane_bias", 0.0) * min(1.0, sensors.get("distRaced", 0) / 200.0)
        if target_offset == 0:
            target_offset = racing_line_offset(sensors, apex_aggr, lane_bias)
        steer = max(-1.0, min(1.0,
            angle * angle_gain * corner_factor
            - (track_pos - target_offset) * position_gain * corner_factor
        ))

        # Gear shifting logic
        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)

        # Acceleration depending on space available and corner severity. Scale is 0 - 1.0
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

        # Braking logic
        if speed > brake_emg_speed and forward_range < brake_emg_range:
            brake = brake_emg_force
        elif speed > brake_hard_speed and forward_range < brake_hard_range:
            brake = brake_hard_force
        elif speed > brake_soft_speed and forward_range < brake_soft_range:
            brake = brake_soft_force
        else:
            brake = 0

        # Extra braking - for scenarios where another car is close
        brake = max(brake, extra_brake)

        # ABS - pulse brake pressure on wheel lockup
        brake = abs_brake(brake, sensors)

        # Don't accelerate and brake on the same tick
        if brake > 0:
            accel = 0.0

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(SimpleAI, default_name="SimpleAI")
