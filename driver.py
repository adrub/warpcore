import socket
import re

HOST = "localhost"
PORT = 3001

INIT_MSG = "SCR(init -90 -75 -60 -45 -30 -20 -15 -10 -5 0 5 10 15 20 30 45 60 75 90)"


def parse_sensors(raw):
    sensors = {}
    for match in re.finditer(r"\((\S+)\s+([^)]+)\)", raw):
        key = match.group(1)
        values = match.group(2).split()
        sensors[key] = float(values[0]) if len(values) == 1 else [float(v) for v in values]
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
