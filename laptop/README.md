#### Disclaimer: Claude models were used to help generate the source code.

`quad_monitor.py` contains a PyQt GUI app that integrates the three UDP streams for video, GPS, and IMU data. 

I used Leaflet to set up a map viewer to add context to the GPS coordinates coming in. One interesting challenge was needing all of the layers and tiles to be available offline since the laptop was only connected to the pi's WAP during flights. 

The tiles are not included here, but `tiles.py` shows how to grab what you need. 

### Notes
* The `gps/gps_ws_client.html` and `imu/*` files are not used for the final version but were used for intermittent versions leading up to the final project.
