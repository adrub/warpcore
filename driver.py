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


class Driver:
    def __init__(self, host=HOST, port=PORT, params=None, name="Driver"):
        self.host = host
        self.port = port
        self.params = params or {}
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5.0)
        self.gear = 1

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
        except KeyboardInterrupt:
            print(f"[{self.name}] Stopped.")
        finally:
            self._running = False
            self.sock.close()


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--name", default="Driver")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()
    Driver(host=args.host, port=args.port, name=args.name, params=json.loads(args.params)).run()
