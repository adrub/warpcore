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
            sensors[key] = float(val)
    for key in multi_keys:
        val = _extract(raw, key)
        if val is not None:
            sensors[key] = [float(v) for v in val.split()]
    return sensors


def build_command(accel, brake, steer, gear):
    return f"(accel {accel})(brake {brake})(steer {steer})(gear {gear})(clutch 0)(focus 0)(meta 0)"


def opponent_action(sensors, params, state):
    opp = sensors.get("opponents", [200.0] * 36)

    fwd_dist   = min(opp[16:21])
    left_gap   = min(opp[9:17])
    right_gap  = min(opp[19:27])
    left_side  = min(opp[13:17])
    right_side = min(opp[19:23])

    brake_dist      = params.get("opp_brake_dist", 8)
    slow_dist       = params.get("opp_slow_dist", 20)
    clear_dist      = params.get("opp_clear_dist", 30)
    overtake_offset = params.get("opp_overtake_offset", 0.4)

    if fwd_dist < brake_dist:
        extra_brake = 0.6
    elif fwd_dist < slow_dist:
        extra_brake = 0.3 * (1 - (fwd_dist - brake_dist) / (slow_dist - brake_dist))
    else:
        extra_brake = 0

    side = state["side"]

    if side is None:
        if fwd_dist < slow_dist:
            side = "left" if left_gap > right_gap else "right"
            state["side"] = side
    else:
        alongside = right_side < 15 if side == "left" else left_side < 15
        if fwd_dist > clear_dist and not alongside:
            state["side"] = None
            side = None

    if side == "left":
        target_offset = -overtake_offset
    elif side == "right":
        target_offset = overtake_offset
    else:
        target_offset = 0.0

    return target_offset, extra_brake


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
