import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5.0)

host = "localhost"
port = 3001

init_msg = "SCR(init -90 -75 -60 -45 -30 -20 -15 -10 -5 0 5 10 15 20 30 45 60 75 90)"
print(f"Connecting to TORCS at {host}:{port} ...")
sock.sendto(init_msg.encode(), (host, port))

try:
    data, _ = sock.recvfrom(1024)
    print("TORCS replied:", data.decode())
except socket.timeout:
    print("No reply — is TORCS running with the SCR server plugin?")
    raise SystemExit

print("Connected. Driving forward slowly...")

sock.settimeout(None)

for tick in range(1000):
    data, addr = sock.recvfrom(131072)

    cmd = "(accel 0.3)(brake 0)(steer 0)(gear 1)(clutch 0)(focus 0)(meta 0)"
    sock.sendto(cmd.encode(), (host, port))

    if tick % 50 == 0:
        print(f"Tick {tick}: {data.decode()[:100]}")
