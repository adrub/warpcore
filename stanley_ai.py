# StanleyAI - Stanley path-tracking controller with opponent awareness

import math
from driver import Driver, opponent_action
from driver_utils import (
    gearbox, run_driver, abs_brake, launch_control, traction_control, racing_line_offset,
    corner_throttle, gear_accel_limit, ramp_throttle,
)


class StanleyAI(Driver):

    # Takes in current sensor data from packet
    def decide(self, sensors):
        speed      = sensors.get("speedX", 0)
        track_pos  = sensors.get("trackPos", 0)
        rpm        = sensors.get("rpm", 0)
        gear       = int(sensors.get("gear", 1))
        angle      = sensors.get("angle", 0)
        track      = sensors.get("track", [100] * 19)

        # Stanley params and gear shifting thresholds
        # stanley_k: cross-track gain (now a physical gain since the error is in metres)
        # stanley_ks: softening constant in m/s, added to speed to avoid blow-up when slow
        stanley_k         = self.params.get("stanley_k", 1.0)
        stanley_ks        = self.params.get("stanley_ks", 1.0)
        upshift_threshold = self.params.get("upshift_threshold", 0.85)
        downshift_rpm     = self.params.get("downshift_rpm", 8000)

        # Opponent handling
        target_offset, extra_brake, throttle_scale = opponent_action(sensors, self.params, self._opp_state)
        # When no opponent is nearby, follow the racing line (inside/outside set by aggressiveness).
        # Ramp the lane bias in over the first 200m so cars hold their grid line at the start
        # instead of darting sideways across the track toward their assigned lane.
        apex_aggr = self.params.get("apex_aggressiveness", 0.6)
        lane_bias = self.params.get("lane_bias", 0.0) * min(1.0, sensors.get("distRaced", 0) / 200.0)
        if target_offset == 0:
            target_offset = racing_line_offset(sensors, apex_aggr, lane_bias)

        # Convert the normalised cross-track error to real metres so the Stanley gain is
        # physically meaningful. Track width is estimated from the perpendicular (-90/+90
        # degree) sensor beams, clamped to a sane range in case a beam reads out of range.
        width = min(25.0, max(5.0, track[0] + track[18]))
        cross_track_error = (track_pos - target_offset) * (width / 2.0)
        speed_ms = speed / 3.6

        # Stanley control law: heading error + speed-scaled cross-track correction.
        # At speed the cross-track term shrinks so heading dominates; when slow it grows.
        steer = angle - math.atan(stanley_k * cross_track_error / (stanley_ks + speed_ms))
        steer = max(-1.0, min(1.0, steer))

        # Gear shifting logic
        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)

        # Acceleration params
        straight_throttle      = self.params.get("straight_throttle", 1.0)
        medium_corner_throttle = self.params.get("medium_corner_throttle", 0.85)
        tight_corner_throttle  = self.params.get("tight_corner_throttle", 0.6)

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
        brake_emg_speed  = self.params.get("brake_emergency_speed", 50)
        brake_emg_range  = self.params.get("brake_emergency_range", 25)
        brake_emg_force  = self.params.get("brake_emergency_force", 0.6)
        brake_hard_speed = self.params.get("brake_hard_speed", 100)
        brake_hard_range = self.params.get("brake_hard_range", 70)
        brake_hard_force = self.params.get("brake_hard_force", 0.35)
        brake_soft_speed = self.params.get("brake_soft_speed", 70)
        brake_soft_range = self.params.get("brake_soft_range", 50)
        brake_soft_force = self.params.get("brake_soft_force", 0.2)

        # Use the widest opening in the central sensor cone, not just the dead-ahead beam,
        # so a road that curves away through a corner isn't mistaken for a wall (which would
        # otherwise emergency-brake the whole way round and cap corner speed).
        brake_lookahead = max(track[8:11])

        # Braking logic - lift throttle first, only brake if still too fast
        if speed > brake_emg_speed and brake_lookahead < brake_emg_range:
            accel = 0.0
            brake = brake_emg_force
        elif speed > brake_hard_speed and brake_lookahead < brake_hard_range:
            accel = 0.0
            brake = brake_hard_force
        elif speed > brake_soft_speed and brake_lookahead < brake_soft_range:
            accel = accel * 0.3   # lift throttle rather than hard brake
            brake = brake_soft_force
        else:
            brake = 0

        brake = max(brake, extra_brake)

        # Cut throttle when braking for a car ahead so we don't drive into it
        if extra_brake > 0:
            accel = 0.0

        # ABS - pulse brake pressure on wheel lockup
        brake = abs_brake(brake, sensors)

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(StanleyAI, default_name="StanleyAI")
