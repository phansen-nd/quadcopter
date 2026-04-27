import socket
import serial

SERIAL_PORT = '/dev/ttyUSB0'
BAUD = 115200
UDP_PORT = 5005
BROADCAST_ADDR = 'ThinkPat.local'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.01)
buf = b""

print(f"Broadcasting IMU data on UDP port {UDP_PORT}")

while True:
    buf += ser.read(ser.in_waiting or 1)
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        line = line.strip()
        if line:
            sock.sendto(line, (BROADCAST_ADDR, UDP_PORT))
            print(line.decode("utf-8", errors="replace"))  # optional, remove if too noisy
