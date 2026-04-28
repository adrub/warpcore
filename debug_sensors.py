import socket
import re

from driver import HOST, PORT, INIT_MSG

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5.0)

sock.sendto(INIT_MSG.encode(), (HOST, PORT))
data, _ = sock.recvfrom(1024)
print("Connected:", data.decode())
sock.settimeout(None)

print("Printing one tick of sensor data...\n")
data, _ = sock.recvfrom(131072)
raw = data.decode()

print("RAW STRING:")
print(raw)
print()

print("PARSED KEYS:")
for match in re.finditer(r"\((\S+)\s+([^)]+)\)", raw):
    key = match.group(1)
    values = match.group(2).split()
    if len(values) == 1:
        print(f"  {key} = {values[0]}")
    else:
        print(f"  {key} = [{', '.join(values[:5])}{'...' if len(values) > 5 else ''}]  ({len(values)} values)")

sock.close()
