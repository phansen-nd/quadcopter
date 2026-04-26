import socket
import re
import sys
import json
import threading
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QGridLayout, QSplitter, QSizePolicy
)
from PyQt6.QtCore import QTimer, Qt, QObject, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QPixmap, QShortcut, QKeySequence
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import tempfile, os, time, struct

IMU_UDP_PORT = 5005
GPS_UDP_PORT = 5006
VIDEO_UDP_PORT = 5007

TILE_PATH = "/home/pat/Projects/jhu/embedded/quadcopter/gps/tiles"

STYLE = """
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
}
QFrame#card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}
QLabel#axis_label {
    color: #8b949e;
    font-size: 18px;
    letter-spacing: 2px;
}
QLabel#axis_value {
    color: #58a6ff;
    font-size: 42px;
    font-family: monospace;
}
QLabel#calib_label {
    color: #8b949e;
    font-size: 16px;
    letter-spacing: 1px;
}
QLabel#calib_value {
    font-size: 20px;
    font-family: monospace;
}
QLabel#title {
    color: #8b949e;
    font-size: 20px;
    letter-spacing: 3px;
}
QSplitter::handle {
    background-color: #30363d;
    width: 2px;
}
"""

CALIB_COLORS = ["#f85149", "#e3b341", "#e3b341", "#3fb950"]


def calib_color(val):
    try:
        return CALIB_COLORS[int(val)]
    except Exception:
        return "#8b949e"


LEAFLET_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body, #map { width: 100%; height: 100%; background: #0d1117; }
  .leaflet-tile { filter: brightness(0.85) saturate(0.9); }
</style>
<link rel="stylesheet" href="file:///home/pat/Projects/jhu/embedded/quadcopter/gps/leaflet.css"/>
<script src="file:///home/pat/Projects/jhu/embedded/quadcopter/gps/leaflet.js"></script>
</head>
<body>
<div id="map"></div>
<script>
  const initLatlng = [37.867, -122.302];
  const map = L.map("map", { zoomControl: true }).setView(initLatlng, 18);

  L.tileLayer('file://TILE_PATH_PLACEHOLDER/{z}/{x}/{y}.png', {
    maxZoom: 19,
    minZoom: 13,
    errorTileUrl: ''
  }).addTo(map);

  const marker = L.circleMarker(initLatlng, {
    radius: 8,
    fillColor: "#D30000",
    color: "#ffffff",
    weight: 2,
    opacity: 1,
    fillOpacity: 0.9
  }).addTo(map);

  // Accuracy ring
  const ring = L.circle(initLatlng, {
    radius: 8,
    color: "#D30000",
    fillColor: "#D30000",
    fillOpacity: 0.1,
    weight: 1
  }).addTo(map);

  const pathLine = L.polyline([], {
    color: '#D30000',
    weight: 2,
    opacity: 0.5
  }).addTo(map);

  const altDisplay = L.control({position: 'bottomleft'});
  altDisplay.onAdd = function() {
    const div = L.DomUtil.create('div');
    div.style.cssText = 'background:#0d1117cc; color:#58a6ff; padding:6px 10px; font-family:monospace; font-size:14px; border-radius:6px; border:1px solid #30363d;';
    div.id = 'alt-display';
    div.innerHTML = 'ALT: --';
    return div;
  };
  altDisplay.addTo(map);

  let hasfix = false;

  function updatePosition(lat, lon, alt) {
    const latlng = [lat, lon];
    marker.setLatLng(latlng);
    ring.setLatLng(latlng);
    pathLine.addLatLng(latlng);
    if (!hasfix) {
      map.setView(latlng, 15);
      hasfix = true;
    } else {
      map.panTo(latlng);
    }
    if (alt !== undefined) {
      document.getElementById('alt-display').innerHTML = `ALT: ${alt.toFixed(1)}m`;
    }
  }
</script>
</body>
</html>
""".replace("TILE_PATH_PLACEHOLDER", TILE_PATH)


class GpsSignal(QObject):
    position_updated = pyqtSignal(float, float, float)

class VideoSignal(QObject):
    frame_ready = pyqtSignal(bytes)

class QuadcopterMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quadcopter Monitor")
        self.setMinimumSize(980, 480)
        self.setStyleSheet(STYLE)

        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── Left panel: IMU ──────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(420)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(12)

        title = QLabel("IMU FEED FROM QUADCOPTER")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        # RPY cards
        rpy_row = QHBoxLayout()
        rpy_row.setSpacing(10)
        self.rpy_values = {}
        for axis, label in [("H", "HEADING"), ("R", "ROLL"), ("P", "PITCH")]:
            card, val_label = self._make_rpy_card(label)
            self.rpy_values[axis] = val_label
            rpy_row.addWidget(card)
        left_layout.addLayout(rpy_row)
        
        # Status bar
        self.imu_status = QLabel("Waiting for IMU...")
        self.imu_status.setObjectName("calib_label")
        self.imu_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.imu_status)

        self.gps_status = QLabel("Waiting for GPS...")
        self.gps_status.setObjectName("calib_label")
        self.gps_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.gps_status)

        left_layout.addStretch()

        # ── Right panel: Map ─────────────────────────────────────────
        self.map_view = QWebEngineView()
        self.map_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.map_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True  # needed for unpkg leaflet
        )
        # Write HTML to a temp file so WebEngine has a file:// base URL
        self._html_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False
        )
        self._html_file.write(LEAFLET_HTML)
        self._html_file.close()

        self.map_view.setUrl(
            QUrl.fromLocalFile(self._html_file.name)
        )

        splitter.addWidget(left)
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

        # ── IMU UDP socket ───────────────────────────────────────────
        self.imu_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.imu_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.imu_sock.bind(('', IMU_UDP_PORT))
        self.imu_sock.setblocking(False)

        self.imu_timer = QTimer()
        self.imu_timer.timeout.connect(self.poll_imu)
        self.imu_timer.start(16)

        # ── GPS UDP listener thread ──────────────────────────────────
        self.gps_signal = GpsSignal()
        self.gps_signal.position_updated.connect(self.update_map)

        gps_thread = threading.Thread(target=self._gps_listener, daemon=True)
        gps_thread.start()

        # ── Video ─────────────────────────────────────────────────────
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000000; border-radius: 8px;")
        self.video_label.setMinimumHeight(800)
        left_layout.addWidget(self.video_label)

        self.video_signal = VideoSignal()
        self.video_signal.frame_ready.connect(self.update_video)

        video_thread = threading.Thread(target=self._video_listener, daemon=True)
        video_thread.start()

    # ── IMU ──────────────────────────────────────────────────────────

    def _make_rpy_card(self, label_text):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setObjectName("axis_label")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val = QLabel("---.–°")
        val.setObjectName("axis_value")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        layout.addWidget(val)
        return card, val

    def poll_imu(self):
        try:
            while True:
                data, _ = self.imu_sock.recvfrom(1024)
                self.parse_imu(data.decode("utf-8", errors="replace").strip())
        except BlockingIOError:
            pass

    def parse_imu(self, line):
        if m := re.search(r'H:([-\d.]+)', line):
            self.rpy_values["H"].setText(f"{float(m.group(1)):>7.1f}°")
            self.imu_status.setText("● IMU live")
        if m := re.search(r'R:([-\d.]+)', line):
            self.rpy_values["R"].setText(f"{float(m.group(1)):>7.1f}°")
        if m := re.search(r'P:([-\d.]+)', line):
            self.rpy_values["P"].setText(f"{float(m.group(1)):>7.1f}°")

    # ── GPS ──────────────────────────────────────────────────────────

    def _gps_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', GPS_UDP_PORT))
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                packet = json.loads(data.decode())
                if 'lat' in packet and 'lon' in packet:
                    self.gps_signal.position_updated.emit(packet['lat'], packet['lon'], packet['alt'])
            except Exception:
                pass

    def update_map(self, lat, lon, alt):
        self.gps_status.setText(f"● GPS  {lat:.5f}, {lon:.5f}, ALT: {alt:.1f}m")
        self.map_view.page().runJavaScript(f"updatePosition({lat}, {lon}, {alt});")

    # ── Video ──────────────────────────────────────────────────────────
    def _video_listener(self):
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to all interfaces on the port the Pi is sending to
        sock.bind(('', VIDEO_UDP_PORT))
        
        # Increase the OS-level receive buffer (64KB) to prevent dropped packets
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

        while True:
            try:
                # Max size for a UDP datagram is 65507 bytes
                data, _ = sock.recvfrom(65507)
                if data:
                    self.video_signal.frame_ready.emit(data)
            except Exception as e:
                print(f"UDP Video error: {e}")
                time.sleep(0.1)

    def update_video(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # Using FastTransformation reduces CPU lag during WAP streaming
            scaled = pixmap.scaled(
                self.video_label.width(),
                self.video_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.video_label.setPixmap(scaled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QuadcopterMonitor()
    win.show()
    sys.exit(app.exec())
