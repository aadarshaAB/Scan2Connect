import cv2
from PySide6.QtCore import QSettings, Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scan2connect.camera.worker import detect_qr_codes, detect_qr_codes_in_image, open_camera
from scan2connect.qr.parser import parse_wifi_qr
from scan2connect.resources import resource_path
from scan2connect.ui.dialogs import CustomMessageBox
from scan2connect.wifi import wlanapi
from scan2connect.wifi.connector import WifiConnector

SETTINGS_ADAPTER_GUID_KEY = "wifi/adapter_guid"


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
        self.setAcceptDrops(True)

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

        self.open_image_button = QPushButton("Open image…")
        self.open_image_button.clicked.connect(self.open_image_dialog)
        button_layout.addWidget(self.open_image_button)

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
        self.camera, error_message = open_camera(0)
        if error_message is not None:
            QMessageBox.critical(self, "Camera Error", error_message)
            return

        self.is_scanning = True
        self.scan_button.setText("Stop Camera")
        self.scan_button.setStyleSheet("background-color: #f44336;")

        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.update_frame)
        self.capture_timer.start(30)

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

    def connect_to_wifi(self, creds):
        try:
            interfaces = wlanapi.list_interfaces()
        except wlanapi.WlanApiError as exp:
            QMessageBox.critical(self, "Error", f"Could not query WiFi adapters: {exp}")
            return

        if not interfaces:
            QMessageBox.critical(self, "Error", "No WiFi adapter found or WiFi is off")
            return

        interface_guid = self.resolve_adapter(interfaces)
        if interface_guid is None:
            return

        progress = QProgressDialog("Connecting to WiFi...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Connecting")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setAutoClose(True)
        progress.setMinimumDuration(0)

        self.connector = WifiConnector(creds, interface_guid)
        self.connector.status_updated.connect(progress.setLabelText)
        self.connector.connection_completed.connect(self.handle_connection_result)
        self.connector.connection_completed.connect(progress.close)
        self.connector.start()

    def resolve_adapter(self, interfaces):
        """Return the interface GUID to connect through, prompting if there are several."""
        if len(interfaces) == 1:
            return interfaces[0]["guid"]

        settings = QSettings()
        remembered_guid = settings.value(SETTINGS_ADAPTER_GUID_KEY)
        if remembered_guid in {iface["guid"] for iface in interfaces}:
            return remembered_guid

        descriptions = [iface["description"] for iface in interfaces]
        choice, ok = QInputDialog.getItem(
            self, "Select WiFi Adapter", "Multiple adapters found:", descriptions, 0, False
        )
        if not ok:
            return None

        chosen = interfaces[descriptions.index(choice)]
        settings.setValue(SETTINGS_ADAPTER_GUID_KEY, chosen["guid"])
        return chosen["guid"]

    def handle_connection_result(self, success, message):
        if success:
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Connected to WiFi")
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText("Connection failed")

    def show_wifi_details_dialog(self, creds):
        dialog = CustomMessageBox(self)
        dialog.setup_ui(creds.ssid, creds.password or "")
        return dialog.exec_()

    @Slot()
    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            for data, corners in detect_qr_codes(frame):
                if data.startswith("WIFI:"):
                    creds = parse_wifi_qr(data)
                    if creds:
                        cv2.polylines(
                            frame, [corners.astype(int)], True, (0, 255, 0), 2
                        )
                        self.handle_wifi_qr_found(creds)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line,
                              QImage.Format.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.camera_label.size(), Qt.KeepAspectRatio
            )
            self.camera_label.setPixmap(scaled_pixmap)

    def handle_wifi_qr_found(self, creds):
        reply = self.show_wifi_details_dialog(creds)
        if reply == QMessageBox.Yes:
            self.connect_to_wifi(creds)

    def open_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open QR Code Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)",
        )
        if path:
            self.scan_image_file(path)

    def scan_image_file(self, path):
        for data, _corners in detect_qr_codes_in_image(path):
            if data.startswith("WIFI:"):
                creds = parse_wifi_qr(data)
                if creds:
                    self.handle_wifi_qr_found(creds)
                    return

        QMessageBox.warning(
            self, "No WiFi QR Code Found", "No WiFi QR code was found in this image."
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.scan_image_file(urls[0].toLocalFile())

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
