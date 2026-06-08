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
    offset_inc      = params.get("opp_offset_inc", 0.04)   # how fast to slide sideways per tick

    speed = sensors.get("speedX", 0)

    # Closing speed on the car ahead (m/s): SCR gives no opponent speed, but differencing the
    # front-gap distance between ticks tells us whether we're actually catching it. Smoothed, and
    # frames where the reading jumps (a car entering/leaving the front window) are ignored.
    DT = 0.02
    prev_fwd = state.get("fwd_prev", fwd_dist)
    if fwd_dist < 190 and prev_fwd < 190 and abs(fwd_dist - prev_fwd) < 30:
        closing = 0.6 * state.get("closing", 0.0) + 0.4 * (prev_fwd - fwd_dist) / DT
    else:
        closing = 0.5 * state.get("closing", 0.0)
    state["fwd_prev"], state["closing"] = fwd_dist, closing

    # Longitudinal response to a car directly ahead:
    #  - imminent (< brake_dist): hard brake, no throttle
    #  - closing (< slow_dist): ease the throttle to match its pace AND brake progressively if we
    #    are carrying speed, so a fast car never coasts into the back of a slower one.
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

    # Closing-aware braking: if we're catching the car ahead fast, shed speed EARLIER than the
    # fixed distance tiers above (a rough "can't stop in time" guard). Scales with closing speed.
    close_speed = params.get("opp_close_speed", 5.0)   # closing m/s above which to start braking
    if closing > close_speed and fwd_dist < slow_dist + closing * 1.5:
        extra_brake = max(extra_brake, min(0.6, (closing - close_speed) / 15.0))
        throttle_scale = min(throttle_scale, 0.6)

    # Decide the DESIRED lateral offset, and whether to SNAP to it (safety) or EASE into it (a pass).
    #   desired = None  -> no opponent influence; ease back to centre then hand off to the racing line
    snap, desired = False, None

    # HIGHEST PRIORITY: a car alongside -> move away NOW (snapped, even at a standstill), so two
    # cars never converge. Boxed in on both flanks -> hold centre and ease off to let it clear.
    if left_side < side_dist and right_side < side_dist:
        desired, snap, extra_brake = 0.0, True, max(extra_brake, 0.3)
    elif left_side < side_dist and left_side <= right_side:
        desired, snap = -overtake_offset, True                       # car on the left -> move right
    elif right_side < side_dist and right_side < left_side:
        desired, snap = overtake_offset, True                        # car on the right -> move left
    else:
        # Nobody alongside: commit to a side to pass a car ahead, release the commitment when clear.
        side = state.get("side")
        if side is None:
            if fwd_dist < slow_dist:
                # Prefer diving to the INSIDE of the corner (classic out-braking pass) when that
                # side is clear; otherwise take the side with more room.
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
            desired = overtake_offset
        elif side == "right":
            desired = -overtake_offset
        # else desired stays None -> clear road

    # Apply the offset: snap for safety, otherwise slide toward `desired` (or back to centre) a
    # step per tick so passes look deliberate instead of darting.
    cur  = state.get("offset", 0.0)
    goal = 0.0 if desired is None else desired
    if snap:
        cur = goal
    elif cur < goal:
        cur = min(goal, cur + offset_inc)
    elif cur > goal:
        cur = max(goal, cur - offset_inc)
    state["offset"] = cur

    # Hand back to the racing line only once there's no opponent influence AND we've eased to
    # centre, so a pass finishes smoothly instead of snapping to the apex mid-move. A returned 0.0
    # (boxed in) is held and NOT overridden; None means "use the racing line". Callers check None.
    if desired is None and abs(cur) < offset_inc:
        state["offset"] = 0.0
        return None, extra_brake, throttle_scale
    return cur, extra_brake, throttle_scale


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
