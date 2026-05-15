# SimpleAI - A simple rule-based driver with opponent awareness

from driver import Driver, opponent_action
from driver_utils import gearbox, run_driver


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
        target_offset, extra_brake = opponent_action(sensors, self.params, self._opp_state)
        steer = max(-1.0, min(1.0,
            angle * angle_gain * corner_factor
            - (track_pos - target_offset) * position_gain * corner_factor
        ))

        # Gear shifting logic
        gear = gearbox(rpm, gear, upshift_threshold, downshift_rpm)

        # Cap acceleration in low gears to avoid wheelspin
        max_accel = min(1.0, 0.3 + gear * 0.1)
         
        # Acceleration depending on space available and corner severity. Scale is 0 - 1.0 
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

        return accel, brake, steer, gear


if __name__ == "__main__":
    run_driver(SimpleAI, default_name="SimpleAI")
