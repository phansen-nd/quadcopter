import serial
import re
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QGridLayout
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor

SERIAL_PORT = '/dev/rfcomm0'
BAUD_RATE = 115200

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
"""

CALIB_COLORS = ["#f85149", "#e3b341", "#e3b341", "#3fb950"]  # 0=red,1-2=yellow,3=green


def calib_color(val):
    try:
        return CALIB_COLORS[int(val)]
    except Exception:
        return "#8b949e"


class IMUDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMU Monitor")
        self.setMinimumSize(520, 340)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("IMU FEED FROM QUADCOPTER")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # RPY row
        rpy_row = QHBoxLayout()
        rpy_row.setSpacing(10)
        self.rpy_values = {}
        for axis, label in [("H", "HEADING"), ("R", "ROLL"), ("P", "PITCH")]:
            card, val_label = self._make_rpy_card(label)
            self.rpy_values[axis] = val_label
            rpy_row.addWidget(card)
        root.addLayout(rpy_row)

        # Calibration card
        calib_card = QFrame()
        calib_card.setObjectName("card")
        calib_layout = QGridLayout(calib_card)
        calib_layout.setContentsMargins(16, 12, 16, 12)
        calib_layout.setSpacing(8)

        self.calib_labels = {}
        for col, key in enumerate(["SYS", "GYRO", "ACCEL", "MAG"]):
            lbl = QLabel(key)
            lbl.setObjectName("calib_label")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val = QLabel("–")
            val.setObjectName("calib_value")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            calib_layout.addWidget(lbl, 0, col)
            calib_layout.addWidget(val, 1, col)
            self.calib_labels[key] = val

        root.addWidget(calib_card)

        # Status bar
        self.status = QLabel("Waiting for data...")
        self.status.setObjectName("calib_label")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.status)

        # BT serial port
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
            self.status.setText("● Connected to RFCOMM")
        except Exception as e:
            self.status.setText(f"Error: {str(e)}")
            self.ser = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(10)

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

    def poll(self):
        if not self.ser: return
        
        try:
            # Read all available lines in the buffer
            while self.ser.in_waiting > 0:
                line = self.ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    self.parse(line)
        except Exception as e:
            self.status.setText(f"Read Error: {e}")

    def parse(self, line):
        # IMU data: H:1.23 R:-4.56 P:0.78
        if m := re.search(r'H:([-\d.]+)', line):
            self.rpy_values["H"].setText(f"{float(m.group(1)):>7.1f}°")
            self.status.setText("● live")
        if m := re.search(r'R:([-\d.]+)', line):
            self.rpy_values["R"].setText(f"{float(m.group(1)):>7.1f}°")
        if m := re.search(r'P:([-\d.]+)', line):
            self.rpy_values["P"].setText(f"{float(m.group(1)):>7.1f}°")

        # Calibration: Calib SYS:3 GYRO:3 ACCEL:1 MAG:3
        for key in ["SYS", "GYRO", "ACCEL", "MAG"]:
            if m := re.search(rf'{key}:(\d)', line):
                v = m.group(1)
                self.calib_labels[key].setText(v)
                self.calib_labels[key].setStyleSheet(
                    f"color: {calib_color(v)}; font-size: 13px; font-family: monospace;"
                )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = IMUDisplay()
    win.show()
    sys.exit(app.exec())