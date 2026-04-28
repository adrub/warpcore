import socket

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
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5.0)
        self.gear = 1

    def connect(self):
        print(f"Connecting to TORCS at {self.host}:{self.port} ...")
        self.sock.sendto(INIT_MSG.encode(), (self.host, self.port))
        data, _ = self.sock.recvfrom(1024)
        print("TORCS:", data.decode())
        self.sock.settimeout(None)

    def decide(self, sensors):
        raise NotImplementedError("Subclass Driver and implement decide()")

    def run(self):
        self.connect()
        print("Running. Ctrl+C to stop.")
        try:
            while True:
                data, _ = self.sock.recvfrom(131072)
                sensors = parse_sensors(data.decode())
                accel, brake, steer, self.gear = self.decide(sensors)
                cmd = build_command(accel, brake, steer, self.gear)
                self.sock.sendto(cmd.encode(), (self.host, self.port))
        except KeyboardInterrupt:
            print("Stopped.")
        finally:
            self.sock.close()
