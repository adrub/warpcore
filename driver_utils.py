# Driver Utils - shared code for all TORCS AI Drivers

from driver import HOST, PORT

# Gear ratios - these are the thresholds for shifting gears
GEAR_RATIOS = [3.9, 2.9, 2.3, 1.87, 1.68, 1.54, 1.46]
REDLINE = 18700

# Gear shifting logic
def gearbox(rpm, gear, upshift_threshold, downshift_rpm):
    if gear <= 0:
        return 1
    # Upshift when RPM exceeds threshold for current gear, but only if not already in top gear
    if gear < len(GEAR_RATIOS) and rpm > REDLINE * upshift_threshold:
        return gear + 1
    # Downshift if RPM drops below threshold for current gear, but only if not already in first gear
    if gear > 1 and rpm < downshift_rpm:
        rpm_if_down = rpm * (GEAR_RATIOS[gear - 2] / GEAR_RATIOS[gear - 1])
        if rpm_if_down < REDLINE:
            return gear - 1
    return gear

_WHEEL_RADIUS = 0.33  # approximate TORCS car wheel radius in metres

# Pulses brake pressure when wheel lockup is detected to restore traction
def abs_brake(brake, sensors):
    speed = sensors.get("speedX", 0)
    if brake == 0 or speed < 10:
        return brake
    wheel_spin = sensors.get("wheelSpinVel", [])
    if not wheel_spin:
        return brake
    expected_spin = (speed / 3.6) / _WHEEL_RADIUS
    # Monitor slowest wheel
    min_spin = min(wheel_spin)
    if min_spin < 0.3 * expected_spin:
        return brake * 0.5
    return brake

# Prevent spinouts but cutting throttle
def traction_control(accel, sensors, tc_slip):
    wheel_spin = sensors.get("wheelSpinVel", [])
    speed = sensors.get("speedX", 0)
    if not wheel_spin or accel == 0:
        return accel
    calc_speed = max(5.0, speed)
    expected_spin = (calc_speed / 3.6) / _WHEEL_RADIUS
    avg_spin = sum(wheel_spin) / len(wheel_spin)
    slip = avg_spin / expected_spin
    if slip > tc_slip:
        return max(0.0, accel - (slip - tc_slip) * 0.4)
    return accel

# Computes the target racing-line offset for the current corner
def racing_line_offset(sensors, aggressiveness, bias=0.0):
    track = sensors.get("track", [100] * 19)
    left_avg  = sum(track[0:9])  / 9
    right_avg = sum(track[10:19]) / 9
    imbalance = right_avg - left_avg              
    sharpness = min(1.0, abs(imbalance) / 50.0)   
    inside_sign = 1.0 if imbalance > 0 else -1.0  
    line = inside_sign * (2.0 * aggressiveness - 1.0)
    room = max(0.0, min(1.0, (max(track[8:11]) - 15.0) / 35.0))
    return max(-0.7, min(0.7, line * sharpness * 0.7 + bias * room))

# Full throttle on race start
def launch_control(sensors, accel, gear):
    is_race_start = sensors.get("lastLapTime", 0) <= 0 and sensors.get("distRaced", 0) < 100.0
    if is_race_start and sensors.get("curLapTime", 999) < 2.0 and sensors.get("speedX", 0) < 40:
        return 1.0, 1
    return accel, gear


# Speed around corners
def corner_throttle(sensors, straight_t, medium_t, tight_t):
    track = sensors.get("track", [100] * 19)
    speed = sensors.get("speedX", 0)
    forward = max(track[6:13])
    flat_out_dist = max(70.0, speed * 0.9)
    medium_dist   = max(35.0, speed * 0.45)
    if forward >= flat_out_dist:
        return straight_t
    if forward >= medium_dist:
        return medium_t
    return tight_t


# Limits max throttle in low gears to stop wheelspin
def gear_accel_limit(gear):
    if gear <= 1:
        return 0.6
    if gear == 2:
        return 0.8
    return 1.0


# Smoothly ramps the throttle toward its target
def ramp_throttle(prev, target, rise=0.08, fall=0.20):
    if target > prev:
        return min(target, prev + rise)
    return max(target, prev - fall)

# Parses --host/--port/--name/--params, instantiates the driver, and runs it within TORCS
def run_driver(driver_class, default_name=None):
    import argparse
    import json

    p = argparse.ArgumentParser()
    p.add_argument("--port",   type=int, default=PORT)
    p.add_argument("--host",   default=HOST)
    p.add_argument("--name",   default=default_name or driver_class.__name__)
    p.add_argument("--params", default="{}")
    args = p.parse_args()
    driver_class(
        host=args.host, port=args.port,
        name=args.name, params=json.loads(args.params),
    ).run()
