# Constants and server configs

import os

# File paths and ports
CONFIG_FILE    = os.path.join(os.path.dirname(__file__), "race_config.json")
PROFILES_FILE  = os.path.join(os.path.dirname(__file__), "profiles.json")
HISTORY_FILE   = os.path.join(os.path.dirname(__file__), "race_history.json")
QUICKRACE_XML  = os.path.expanduser("~/.torcs/config/raceman/quickrace.xml")
TELEMETRY_PORT = 9999
MAX_CARS       = 10
RACE_LAPS      = 1     # race length; the finish monitor watches for a car reaching this lap count

# MQTT config
MQTT_BROKER = "172.20.10.4" # <--- change to IP of PI
MQTT_PORT   = 1883

# Driver Information - maps driver type to file and displays name
DRIVER_FILES   = {"simple_ai": "simple_ai.py", "pid_ai": "pid_ai.py", "stanley_ai": "stanley_ai.py"}
DRIVER_DISPLAY = {"simple_ai": "SimpleAI",     "pid_ai": "PidAI",    "stanley_ai": "StanleyAI",
                  "remote": "Remote (Pi)"}   # a driver hosted on the Pi - reserved, not launched locally

# Advanced parameters for each driver type
DRIVER_PARAMS = {
    "simple_ai": {
        "angle_gain": 0.5,
        "position_gain": 0.3,
        "upshift_threshold": 0.9,
        "downshift_rpm": 8000,
        "straight_throttle": 1.0,
        "medium_corner_throttle": 0.85,
        "tight_corner_throttle": 0.5,
        "brake_emergency_speed": 50,
        "brake_emergency_range": 18,
        "brake_emergency_force": 0.85,
        "brake_hard_speed": 120,
        "brake_hard_range": 55,
        "brake_hard_force": 0.65,
        "brake_soft_speed": 80,
        "brake_soft_range": 35,
        "brake_soft_force": 0.4,
        "opp_brake_dist": 8,
        "opp_slow_dist": 20,
        "opp_overtake_offset": 0.4,
        "opp_clear_dist": 30,
        "opp_side_dist": 10,
        "opp_offset_inc": 0.04,
        "opp_close_speed": 5.0,
    },
    "pid_ai": {
        "steer_kp": 0.3,
        "steer_ki": 0.0,
        "steer_kd": 0.5,
        "upshift_threshold": 0.9,
        "downshift_rpm": 9500,
        "straight_throttle": 1.0,
        "medium_corner_throttle": 0.85,
        "tight_corner_throttle": 0.5,
        "brake_emergency_speed": 50,
        "brake_emergency_range": 28,
        "brake_emergency_force": 0.85,
        "brake_early_speed": 100,
        "brake_early_range": 110,
        "brake_early_force": 0.45,
        "brake_hard_speed": 75,
        "brake_hard_range": 75,
        "brake_hard_force": 0.65,
        "brake_soft_speed": 45,
        "brake_soft_range": 35,
        "brake_soft_force": 0.3,
        "opp_brake_dist": 8,
        "opp_slow_dist": 20,
        "opp_overtake_offset": 0.4,
        "opp_clear_dist": 30,
        "opp_side_dist": 10,
        "opp_offset_inc": 0.04,
        "opp_close_speed": 5.0,
    },
    "stanley_ai": {
        "stanley_k": 1.0,
        "stanley_ks": 1.0,
        "upshift_threshold": 0.9,
        "downshift_rpm": 9000,
        "straight_throttle": 1.0,
        "medium_corner_throttle": 0.85,
        "tight_corner_throttle": 0.5,
        "brake_emergency_speed": 50,
        "brake_emergency_range": 28,
        "brake_emergency_force": 0.85,
        "brake_early_speed": 100,
        "brake_early_range": 110,
        "brake_early_force": 0.45,
        "brake_hard_speed": 75,
        "brake_hard_range": 75,
        "brake_hard_force": 0.65,
        "brake_soft_speed": 45,
        "brake_soft_range": 35,
        "brake_soft_force": 0.3,
        "opp_brake_dist": 8,
        "opp_slow_dist": 20,
        "opp_overtake_offset": 0.4,
        "opp_clear_dist": 30,
        "opp_side_dist": 10,
        "opp_offset_inc": 0.04,
        "opp_close_speed": 5.0,
    },
}

# Simple slider parameters for each driver type
_BRAKING_SLIDERS = [
    {"key": "brake_force",    "label": "Brake Force",    "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "brake_distance", "label": "Brake Distance", "min": 0.0, "max": 1.0, "step": 0.05},
]
_ACCEL_SLIDERS = [
    {"key": "shift_aggression", "label": "Shift Aggression", "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "straight_speed",   "label": "Straight Speed",   "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "corner_caution",   "label": "Corner Caution",   "min": 0.0, "max": 1.0, "step": 0.05},
]
_OPP_SLIDERS = [
    {"key": "opp_commitment",     "label": "Overtake Commitment", "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "opp_aggressiveness", "label": "Brake Closeness",     "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "opp_detection",      "label": "Awareness Range",     "min": 0.0, "max": 1.0, "step": 0.05},
]
_DYNAMICS_SLIDERS = [
    {"key": "apex_aggressiveness", "label": "Racing Line (0 outside → 1 inside)", "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "tc_slip",             "label": "Traction Control",    "min": 0.0, "max": 1.0, "step": 0.05},
]

SIMPLE_PARAMS = {
    "stanley_ai": {
        "Stanley Steering": [
            {"key": "stanley_k",  "label": "Cross-Track Gain", "min": 0.1, "max": 5.0,  "step": 0.1, "direct": True},
            {"key": "stanley_ks", "label": "Speed Softening",  "min": 0.1, "max": 10.0, "step": 0.1, "direct": True},
        ],
        "Braking":            _BRAKING_SLIDERS,
        "Acceleration":       _ACCEL_SLIDERS,
        "Opponent Behaviour": _OPP_SLIDERS,
        "Dynamics":           _DYNAMICS_SLIDERS,
    },
    "pid_ai": {
        "PID Control": [
            {"key": "steer_kp", "label": "Proportional (Kp)", "min": 0.0, "max": 2.0,  "step": 0.05,  "direct": True},
            {"key": "steer_ki", "label": "Integral (Ki)",     "min": 0.0, "max": 0.2,  "step": 0.005, "direct": True},
            {"key": "steer_kd", "label": "Derivative (Kd)",   "min": 0.0, "max": 2.0,  "step": 0.05,  "direct": True},
        ],
        "Braking":              _BRAKING_SLIDERS,
        "Acceleration":         _ACCEL_SLIDERS,
        "Opponent Behaviour":   _OPP_SLIDERS,
        "Dynamics":             _DYNAMICS_SLIDERS,
    },
    "simple_ai": {
        "Steering": [
            {"key": "steering_responsiveness", "label": "Responsiveness", "min": 0.0, "max": 1.0, "step": 0.05},
        ],
        "Braking":            _BRAKING_SLIDERS,
        "Acceleration":       _ACCEL_SLIDERS,
        "Opponent Behaviour": _OPP_SLIDERS,
        "Dynamics":           _DYNAMICS_SLIDERS,
    },
}

# Default slider values for each driver
DEFAULT_SIMPLE = {
    "stanley_ai": {
        "stanley_k": 1.0, "stanley_ks": 1.0,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_commitment": 0.5, "opp_aggressiveness": 0.5, "opp_detection": 0.6,
        "apex_aggressiveness": 0.6, "tc_slip": 0.4,
    },
    "pid_ai": {
        "steer_kp": 0.3, "steer_ki": 0.0, "steer_kd": 0.5,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_commitment": 0.5, "opp_aggressiveness": 0.5, "opp_detection": 0.6,
        "apex_aggressiveness": 0.6, "tc_slip": 0.4,
    },
    "simple_ai": {
        "steering_responsiveness": 0.5,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_commitment": 0.5, "opp_aggressiveness": 0.5, "opp_detection": 0.6,
        "apex_aggressiveness": 0.6, "tc_slip": 0.4,
    },
}
