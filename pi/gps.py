import gpsd
import socket
import json
import time

gpsd.connect()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

UDP_PORT = 5006  # different port from IMU
BROADCAST_ADDR = 'ThinkPat.local'

while True:
    try:
        packet = gpsd.get_current()
        data = json.dumps({"lat": packet.lat, "lon": packet.lon, "alt": packet.alt})
        sock.sendto(data.encode(), (BROADCAST_ADDR, UDP_PORT))
    except gpsd.NoFixError:
        pass
    time.sleep(0.5)