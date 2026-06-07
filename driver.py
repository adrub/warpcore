import json
import socket
import threading

HOST = "localhost"
PORT = 3001

INIT_MSG = "SCR(init -90 -75 -60 -45 -30 -20 -15 -10 -5 0 5 10 15 20 30 45 60 75 90)"


def _extract(raw, key):
    idx = raw.find(f"({key} ")
    if idx == -1:
        return None
    start = idx + len(key) + 2
    end = raw.find(")", start)
    return raw[start:end].strip()


def parse_sensors(raw):
    single_keys = [
        "angle", "curLapTime", "damage", "distFromStart", "distRaced",
        "fuel", "gear", "lastLapTime", "pitch", "racePos", "roll", "rpm",
        "speedGlobalX", "speedGlobalY", "speedX", "speedY", "speedZ",
        "trackPos", "x", "y", "yaw", "z"
    ]
    multi_keys = ["focus", "opponents", "track", "wheelSpinVel"]

    sensors = {}
    for key in single_keys:
        val = _extract(raw, key)
        if val is not None:
            try:
                sensors[key] = float(val)
            except ValueError:
                pass   # skip a malformed field; callers use sensors.get(key, default)
    for key in multi_keys:
        val = _extract(raw, key)
        if val is not None:
            try:
                sensors[key] = [float(v) for v in val.split()]
            except ValueError:
                pass   # skip rather than store [] (which would IndexError downstream)
    return sensors


def build_command(accel, brake, steer, gear):
    return f"(accel {accel})(brake {brake})(steer {steer})(gear {gear})(clutch 0)(focus 0)(meta 0)"


def opponent_action(sensors, params, state):
    opp = sensors.get("opponents", [200.0] * 36)

    # Sensor windows are mirrored about dead-ahead (index 18) so avoidance behaves identically
    # whichever side a car is on. The side windows span the whole flank - front quarter through
    # alongside to the rear quarter - so a car gives room to an overtaker beside OR behind it,
    # not just one that's already drawn level at the front.
    fwd_dist   = min(opp[16:21])   # car directly ahead       (-20..+20 deg)
    left_gap   = min(opp[10:18])   # room to the left         (-80..-10 deg) for choosing a side
    right_gap  = min(opp[19:27])   # room to the right        (+10..+80 deg)
    left_side  = min(opp[8:18])    # car along the left flank (-100..-10 deg) incl. rear quarter
    right_side = min(opp[19:29])   # car along the right flank (+10..+100 deg)

    brake_dist      = params.get("opp_brake_dist", 8)
    slow_dist       = params.get("opp_slow_dist", 20)
    clear_dist      = params.get("opp_clear_dist", 30)
    overtake_offset = params.get("opp_overtake_offset", 0.4)
    side_dist       = params.get("opp_side_dist", 10)

    speed = sensors.get("speedX", 0)

    # Longitudinal response to a car directly ahead:
    #  - imminent (< brake_dist): hard brake, no throttle
    #  - closing (< slow_dist): ease the throttle to match its pace AND brake progressively if we
    #    are carrying speed, so a fast car never coasts into the back of a slower one. The brake is
    #    gated above 40 km/h so grid cars at the start ease rather than brake (no stall).
    #  - clear: full throttle
    if fwd_dist < brake_dist:
        extra_brake = 0.6
        throttle_scale = 0.0
    elif fwd_dist < slow_dist:
        frac = (slow_dist - fwd_dist) / max(slow_dist - brake_dist, 1)
        throttle_scale = max(0.7, 1.0 - 0.3 * frac)
        extra_brake = min(0.4, frac * 0.4) if (speed > 40 and fwd_dist < brake_dist * 2) else 0.0
    else:
        extra_brake = 0.0
        throttle_scale = 1.0

    # HIGHEST PRIORITY, active even at a standstill: if a car is alongside, steer away from it.
    # Checked before the overtake logic so two cars can never converge into each other - on the
    # grid at the start or contesting a line mid-race.
    # Boxed in on both flanks: don't steer into either - hold the line and ease back to let it clear.
    if left_side < side_dist and right_side < side_dist:
        return 0.0, max(extra_brake, 0.3), throttle_scale
    if left_side < side_dist and left_side <= right_side:
        return -overtake_offset, extra_brake, throttle_scale     # car on the left -> move right
    if right_side < side_dist and right_side < left_side:
        return overtake_offset, extra_brake, throttle_scale    # car on the right -> move left

    side = state["side"]

    if side is None:
        if fwd_dist < slow_dist:
            # Prefer diving to the INSIDE of the corner (the classic out-braking overtake) when
            # that side is clear of cars; only fall back to the side with more room (the outside)
            # on straights or when the inside is blocked. Inside is the side the track curves
            # toward, from the same sensor imbalance the apex line uses.
            track     = sensors.get("track", [100] * 19)
            imbalance = sum(track[10:19]) / 9 - sum(track[0:9]) / 9   # >0 = curves left
            if abs(imbalance) > 10:  # in a corner
                inside     = "left" if imbalance > 0 else "right"
                inside_gap = left_gap if inside == "left" else right_gap
                side = inside if inside_gap > slow_dist else ("left" if left_gap > right_gap else "right")
            else:
                side = "left" if left_gap > right_gap else "right"
            state["side"] = side
    else:
        alongside = right_side < 15 if side == "left" else left_side < 15
        if fwd_dist > clear_dist and not alongside:
            state["side"] = None
            side = None

    if side == "left":
        target_offset = overtake_offset
    elif side == "right":
        target_offset = -overtake_offset
    else:
        # None = no opponent influence; the caller falls back to the racing line. (A real 0.0
        # returned earlier means "boxed in, hold centre" and must NOT be overridden - hence the
        # None-vs-0.0 distinction. Callers check `if target_offset is None`.)
        target_offset = None

    return target_offset, extra_brake, throttle_scale


class Driver:
    def __init__(self, host=HOST, port=PORT, params=None, name="Driver"):
        self.host = host
        self.port = port
        self.params = params or {}
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5.0)
        self.gear = 1
        self._tel_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._tel_tick = 0
        self._opp_state = {"side": None}
        # Previous throttle output, used to smoothly ramp acceleration between ticks
        self.prev_accel = 0.0

    def connect(self):
        print(f"[{self.name}] Connecting to TORCS at {self.host}:{self.port} ...")
        while True:
            self.sock.sendto(INIT_MSG.encode(), (self.host, self.port))
            try:
                data, _ = self.sock.recvfrom(1024)
                print(f"[{self.name}] TORCS: {data.decode()}")
                self.sock.settimeout(0.5)
                return
            except socket.timeout:
                print(f"[{self.name}] Waiting for TORCS on port {self.port}...")

    def decide(self, sensors):
        raise NotImplementedError("Subclass Driver and implement decide()")

    def _reconnect(self):
        self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5.0)
        self.connect()

    def _listen_for_restart(self):
        while self._running:
            try:
                cmd = input()
                if cmd.strip().lower() == "r":
                    print("Restarting connection...")
                    self._restart = True
            except EOFError:
                break

    def run(self):
        self._running = True
        self._restart = False
        self.connect()
        print(f"[{self.name}] Running on port {self.port}. Type 'r' + Enter to restart. Ctrl+C to stop.")

        listener = threading.Thread(target=self._listen_for_restart, daemon=True)
        listener.start()

        try:
            while True:
                if self._restart:
                    self._restart = False
                    self._reconnect()

                try:
                    data, _ = self.sock.recvfrom(131072)
                except socket.timeout:
                    continue
                sensors = parse_sensors(data.decode())
                accel, brake, steer, self.gear = self.decide(sensors)
                cmd = build_command(accel, brake, steer, self.gear)
                self.sock.sendto(cmd.encode(), (self.host, self.port))
                self._tel_tick += 1
                if self._tel_tick % 5 == 0:
                    tel_port = self.params.get("telemetry_port")
                    if tel_port:
                        tel = {
                            "name": self.name,
                            "speed": sensors.get("speedX", 0),
                            "gear": int(sensors.get("gear", 1)),
                            "rpm": sensors.get("rpm", 0),
                            "lap_time": sensors.get("curLapTime", 0),
                            "last_lap": sensors.get("lastLapTime", 0),
                            "race_pos": int(sensors.get("racePos", 0)),
                            "damage": sensors.get("damage", 0),
                            "dist_raced": sensors.get("distRaced", 0),
                            "x": sensors.get("x", 0),
                            "y": sensors.get("y", 0),
                        }
                        self._tel_sock.sendto(json.dumps(tel).encode(), ("127.0.0.1", int(tel_port)))
        except KeyboardInterrupt:
            print(f"[{self.name}] Stopped.")
        finally:
            self._running = False
            self.sock.close()
            self._tel_sock.close()


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--name", default="Driver")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()
    Driver(host=args.host, port=args.port, name=args.name, params=json.loads(args.params)).run()
