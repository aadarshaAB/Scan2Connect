import cv2
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pyzbar.pyzbar import decode

from scan2connect.qr.parser import parse_wifi_qr
from scan2connect.resources import resource_path
from scan2connect.ui.dialogs import CustomMessageBox
from scan2connect.wifi.connector import WifiConnector


class WifiQRScanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scan2Connect")
        self.setMinimumSize(800, 600)
        icon = QIcon(resource_path("assets/app_icon.ico"))
        self.setWindowIcon(icon)

        self.camera = None
        self.capture_timer = None
        self.is_scanning = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.setup_ui()

    def setup_ui(self):
        camera_frame = QFrame()
        camera_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        camera_layout = QVBoxLayout(camera_frame)

        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        camera_layout.addWidget(self.camera_label)

        button_layout = QHBoxLayout()
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.clicked.connect(self.toggle_scanning)
        button_layout.addWidget(self.scan_button)

        camera_layout.addLayout(button_layout)
        self.layout.addWidget(camera_frame)

        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        status_layout = QVBoxLayout(status_frame)

        self.status_label = QLabel("Scan QR code")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        self.layout.addWidget(status_frame)

        watermark_label = QLabel("© 2024 Aadarsha | https://github.com/aadarshaAB")
        watermark_label.setAlignment(Qt.AlignCenter)
        watermark_label.setStyleSheet("color: #999; padding: 5px;")
        self.layout.addWidget(watermark_label)

    def toggle_scanning(self):
        if not self.is_scanning:
            self.start_camera()
        else:
            self.stop_camera()

    def start_camera(self):
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Cannot access camera")

            self.is_scanning = True
            self.scan_button.setText("Stop Camera")
            self.scan_button.setStyleSheet("background-color: #f44336;")

            self.capture_timer = QTimer()
            self.capture_timer.timeout.connect(self.update_frame)
            self.capture_timer.start(30)

        except Exception as exp:
            QMessageBox.critical(self, "Error", f"Could not start camera: {str(exp)}")

    def stop_camera(self):
        self.is_scanning = False
        if self.capture_timer:
            self.capture_timer.stop()
        if self.camera:
            self.camera.release()

        self.scan_button.setText("Start Camera")
        self.scan_button.setStyleSheet("background-color: #4CAF50;")
        self.camera_label.clear()
        self.status_label.setText("Scan WiFi QR code to connect")

    def connect_to_wifi(self, ssid, password):
        progress = QProgressDialog("Connecting to WiFi...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Connecting")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setAutoClose(True)
        progress.setMinimumDuration(0)

        self.connector = WifiConnector(ssid, password)
        self.connector.status_updated.connect(progress.setLabelText)
        self.connector.connection_completed.connect(self.handle_connection_result)
        self.connector.connection_completed.connect(progress.close)
        self.connector.start()

    def handle_connection_result(self, success, message):
        if success:
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Connected to WiFi")
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText("Connection failed")

    def show_wifi_details_dialog(self, ssid, password):
        dialog = CustomMessageBox(self)
        dialog.setup_ui(ssid, password)
        return dialog.exec_()

    @Slot()
    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            decoded_objects = decode(frame)

            for obj in decoded_objects:
                data = obj.data.decode("utf-8")
                if data.startswith("WIFI:"):
                    ssid, password = parse_wifi_qr(data)
                    if ssid and password:
                        rect_points = obj.rect
                        cv2.rectangle(
                            frame, (rect_points.left, rect_points.top),
                            (rect_points.left + rect_points.width,
                             rect_points.top + rect_points.height),
                            (0, 255, 0), 2
                        )
                        reply = self.show_wifi_details_dialog(ssid, password)
                        if reply == QMessageBox.Yes:
                            self.connect_to_wifi(ssid, password)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line,
                              QImage.Format.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.camera_label.size(), Qt.KeepAspectRatio
            )
            self.camera_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
