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
