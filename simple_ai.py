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

        # Avoiding other cars or overtaking requires offset to go around them 
        target_offset, extra_brake, throttle_scale = opponent_action(sensors, self.params, self._opp_state)
        # Follow racing line with no opponents
        apex_aggr = self.params.get("apex_aggressiveness", 0.6)
        lane_bias = self.params.get("lane_bias", 0.0) * min(1.0, sensors.get("distRaced", 0) / 200.0)
        if target_offset is None:
            target_offset = racing_line_offset(sensors, apex_aggr, lane_bias)
        steer = (angle * angle_gain * corner_factor
                 - (track_pos - target_offset) * position_gain * corner_factor)
        # Dampen steering as speed rises to stop high-speed darting 
        speed_ms = speed / 3.6
        if speed_ms > 15.0:
            steer /= (1.0 + (speed_ms - 15.0) * 0.02)
        steer = max(-1.0, min(1.0, steer))

        # Gear shifting logic
        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)

        # Acceleration depending on space available and corner severity.
        straight_throttle      = self.params.get("straight_throttle", 1.0)
        medium_corner_throttle = self.params.get("medium_corner_throttle", 0.85)
        tight_corner_throttle  = self.params.get("tight_corner_throttle", 0.5)

        # Corner detection based on current speed and infront space
        target_accel = corner_throttle(sensors, straight_throttle, medium_corner_throttle, tight_corner_throttle)
        target_accel *= gear_accel_limit(gear)
        accel = ramp_throttle(self.prev_accel, target_accel)
        self.prev_accel = accel

        # Launch control 
        accel, gear = launch_control(sensors, accel, gear)

        # Ease off if closing on a car ahead 
        accel *= throttle_scale

        # Traction control 
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
        if brake > 0.05:
            accel = 0.0

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(SimpleAI, default_name="SimpleAI")
