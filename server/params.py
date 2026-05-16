# Converts params into a simple scale from 0 - 1.0 in the UI

# Linear interpolation of params helper function
def linear_interpolate(a, b, t):
    return a + (b - a) * t

# Expands simple params into full physics params values
def expand_simple_params(driver_type, simple):
    bf = simple.get("brake_force",    0.6)
    bd = simple.get("brake_distance", 0.7)
    sa = simple.get("shift_aggression", 0.5)
    ss = simple.get("straight_speed",   0.8)
    cc = simple.get("corner_caution",   0.5)
    oa = simple.get("opp_aggressiveness", 0.5)
    od = simple.get("opp_detection",      0.6)

    raw = {
        # Braking forces - how hard each tier presses the pedal
        "brake_emergency_force": linear_interpolate(0.3,  1.0,  bf),
        "brake_hard_force":      linear_interpolate(0.15, 0.8,  bf),
        "brake_early_force":     linear_interpolate(0.1,  0.6,  bf),
        "brake_soft_force":      linear_interpolate(0.05, 0.35, bf),
        # Braking speeds - the speed (km/h) below which each tier applies
        "brake_emergency_speed": linear_interpolate(30,  70,  bf),
        "brake_hard_speed":      linear_interpolate(40,  100, bf),
        "brake_early_speed":     linear_interpolate(60,  140, bf),
        "brake_soft_speed":      linear_interpolate(30,  65,  bf),
        # Braking ranges - the look-ahead distance (m) that triggers each tier
        "brake_emergency_range": linear_interpolate(15,  40,  bd),
        "brake_early_range":     linear_interpolate(50,  150, bd),
        "brake_hard_range":      linear_interpolate(35,  100, bd),
        "brake_soft_range":      linear_interpolate(15,  55,  bd),
        # Acceleration / gearbox
        "upshift_threshold":       linear_interpolate(0.75, 0.95,  sa),
        "downshift_rpm":           linear_interpolate(7000, 12000, sa),
        "straight_throttle":       linear_interpolate(0.5,  1.0,   ss),
        "medium_corner_throttle":  linear_interpolate(0.95, 0.5,   cc),  # higher cc = lower throttle in corners
        "tight_corner_throttle":   linear_interpolate(0.8,  0.2,   cc),
        # Opponent avoidance
        "opp_overtake_offset": linear_interpolate(0.2, 0.7,  oa),
        "opp_brake_dist":      linear_interpolate(15,  4,    oa),       # more aggressive = brake closer
        "opp_slow_dist":       linear_interpolate(10,  35,   od),
        "opp_clear_dist":      linear_interpolate(15,  50,   od),
    }

    if driver_type == "pid_ai":
        # PID drivers expose their gains directly
        raw["steer_kp"] = simple.get("steer_kp", 0.3)
        raw["steer_ki"] = simple.get("steer_ki", 0.0)
        raw["steer_kd"] = simple.get("steer_kd", 0.5)
        raw["centered_threshold"] = 0.5
    elif driver_type == "simple_ai":
        sr = simple.get("steering_responsiveness", 0.5)
        raw["angle_gain"]    = linear_interpolate(0.2, 1.0, sr)
        raw["position_gain"] = linear_interpolate(0.1, 0.6, sr)

    return raw
