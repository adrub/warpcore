import subprocess
import sys
import json
import signal

CARS = [
    {
        "name": "SimpleAI",
        "driver": "simple_ai.py",
        "port": 3001,
        "params": {
            "angle_gain": 0.5,
            "position_gain": 0.3,
            "upshift_threshold": 0.9,
            "downshift_rpm": 8000,
            "brake_emergency_speed": 50,
            "brake_emergency_range": 18,
            "brake_hard_speed": 120,
            "brake_hard_range": 55,
            "brake_soft_speed": 80,
            "brake_soft_range": 35,
        },
    },
    {
        "name": "PidAI",
        "driver": "pid_ai.py",
        "port": 3002,
        "params": {
            "steer_kp": 0.6,
            "steer_ki": 0.02,
            "steer_kd": 0.5,
            "speed_kp": 0.02,
            "speed_straight": 999,
            "speed_corner": 80,
            "speed_sharp": 45,
            "upshift_threshold": 0.9,
            "downshift_rpm": 8000,
        },
    },
]


def main():
    procs = []
    for car in CARS:
        cmd = [
            sys.executable, "-u", car["driver"],
            "--port", str(car["port"]),
            "--name", car["name"],
            "--params", json.dumps(car["params"]),
        ]
        print(f"Launching {car['name']} on port {car['port']}")
        procs.append(subprocess.Popen(cmd))

    def shutdown(sig, frame):
        print("\nShutting down all drivers...")
        for p in procs:
            p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("All drivers launched. Ctrl+C to stop.")
    for p in procs:
        p.wait()


if __name__ == "__main__":
    main()
