import socket
import smbus2
import struct
import time

# From
ESP_ADDR = 0x09
bus = smbus2.SMBus(1)

# To
UDP_PORT = 5005
BROADCAST_ADDR = 'ThinkPat.local'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

print(f"Reading IMU data from I2C address {ESP_ADDR}")
print(f"Broadcasting IMU data on UDP port {UDP_PORT}")

while True:
    data = bus.read_i2c_block_data(ESP_ADDR, 0, 12)
    heading, roll, pitch = struct.unpack('<fff', bytes(data))
    line = f"H:{heading:.2f} R:{roll:.2f} P:{pitch:.2f}\n".encode()
    sock.sendto(line, (BROADCAST_ADDR, UDP_PORT))
    
    # print(line.decode("utf-8", errors="replace")) 

    time.sleep(0.1)
