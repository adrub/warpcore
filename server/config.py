# Constants and server configs

import os

# File paths and ports
CONFIG_FILE    = os.path.join(os.path.dirname(__file__), "race_config.json")
PROFILES_FILE  = os.path.join(os.path.dirname(__file__), "profiles.json")
HISTORY_FILE   = os.path.join(os.path.dirname(__file__), "race_history.json")
QUICKRACE_XML  = os.path.expanduser("~/.torcs/config/raceman/quickrace.xml")
TELEMETRY_PORT = 9999
MAX_CARS       = 10

# MQTT config
MQTT_BROKER = "localhost" # <--- change to IP of PI
MQTT_PORT   = 1883

# Driver Information - maps driver type to file and displays name
DRIVER_FILES   = {"simple_ai": "simple_ai.py", "pid_ai": "pid_ai.py"}
DRIVER_DISPLAY = {"simple_ai": "SimpleAI",     "pid_ai": "PidAI"}

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
        "centered_threshold": 0.5,
        "opp_brake_dist": 8,
        "opp_slow_dist": 20,
        "opp_overtake_offset": 0.4,
        "opp_clear_dist": 30,
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
    {"key": "opp_aggressiveness", "label": "Aggressiveness",   "min": 0.0, "max": 1.0, "step": 0.05},
    {"key": "opp_detection",      "label": "Detection Range",  "min": 0.0, "max": 1.0, "step": 0.05},
]

SIMPLE_PARAMS = {
    "pid_ai": {
        "PID Control": [
            {"key": "steer_kp", "label": "Proportional (Kp)", "min": 0.0, "max": 2.0,  "step": 0.05,  "direct": True},
            {"key": "steer_ki", "label": "Integral (Ki)",     "min": 0.0, "max": 0.2,  "step": 0.005, "direct": True},
            {"key": "steer_kd", "label": "Derivative (Kd)",   "min": 0.0, "max": 2.0,  "step": 0.05,  "direct": True},
        ],
        "Braking":              _BRAKING_SLIDERS,
        "Acceleration":         _ACCEL_SLIDERS,
        "Opponent Behaviour":   _OPP_SLIDERS,
    },
    "simple_ai": {
        "Steering": [
            {"key": "steering_responsiveness", "label": "Responsiveness", "min": 0.0, "max": 1.0, "step": 0.05},
        ],
        "Braking":            _BRAKING_SLIDERS,
        "Acceleration":       _ACCEL_SLIDERS,
        "Opponent Behaviour": _OPP_SLIDERS,
    },
}

# Default slider values for each driver
DEFAULT_SIMPLE = {
    "pid_ai": {
        "steer_kp": 0.3, "steer_ki": 0.0, "steer_kd": 0.5,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_aggressiveness": 0.5, "opp_detection": 0.6,
    },
    "simple_ai": {
        "steering_responsiveness": 0.5,
        "brake_force": 0.6, "brake_distance": 0.7,
        "shift_aggression": 0.5, "straight_speed": 0.8, "corner_caution": 0.5,
        "opp_aggressiveness": 0.5, "opp_detection": 0.6,
    },
}
