### Files
* `pi-ap.nmconnection` is a file used to set the pi up as a WAP.
* `imu_udp.py` reads from the pi's serial input and re-broadcasts data over UDP (used for Project 8)
* `imu_i2c.py` reads from the I2C connection with the ESP-32 S3 and also re-broadcasts over UDP
* `gps.py` reads GPS data with the `gpsd` package and broadcasts over UDP
* vid_commands.txt` contains the primary `rpivid` command for sending video data over UDP as well as a couple others to free up bandwidth to smoothen the video stream
