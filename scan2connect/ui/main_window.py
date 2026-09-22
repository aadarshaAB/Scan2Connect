import logging
import time

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
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

from scan2connect.camera.worker import CameraWorker, detect_qr_codes_in_image
from scan2connect.logging_setup import log_dir
from scan2connect.qr.parser import parse_wifi_qr
from scan2connect.resources import resource_path
from scan2connect.ui.dialogs import CustomMessageBox
from scan2connect.ui.widgets import CameraView
from scan2connect.wifi import wlanapi
from scan2connect.wifi.connector import WifiConnector

log = logging.getLogger(__name__)

SETTINGS_ADAPTER_GUID_KEY = "wifi/adapter_guid"
DEBOUNCE_SECONDS = 10
HIGHLIGHT_DISPLAY_MS = 1500


class WifiQRScanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scan2Connect")
        self.setMinimumSize(800, 600)
        icon = QIcon(resource_path("assets/app_icon.ico"))
        self.setWindowIcon(icon)

        self.camera_worker = None
        self.is_scanning = False
        self._dialog_open = False
        self._ignored_payload = None
        self._ignored_until = 0.0
        self.setAcceptDrops(True)

        self._highlight_timer = QTimer(self)
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.timeout.connect(self._clear_highlight)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.setup_ui()
        self.setup_menu()

    def setup_ui(self):
        camera_frame = QFrame()
        camera_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        camera_layout = QVBoxLayout(camera_frame)

        self.camera_label = CameraView()
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

    def setup_menu(self):
        help_menu = self.menuBar().addMenu("&Help")
        open_log_folder_action = help_menu.addAction("Open log folder")
        open_log_folder_action.triggered.connect(self.open_log_folder)

    def open_log_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir())))

    def toggle_scanning(self):
        if not self.is_scanning:
            self.start_camera()
        else:
            self.stop_camera()

    def start_camera(self):
        self.is_scanning = True
        self.scan_button.setText("Stop Camera")
        self.scan_button.setStyleSheet("background-color: #f44336;")

        self.camera_worker = CameraWorker(0)
        self.camera_worker.frame_ready.connect(self.display_frame)
        self.camera_worker.qr_found.connect(self.on_qr_found)
        self.camera_worker.camera_error.connect(self.on_camera_error)
        self.camera_worker.start()

    def stop_camera(self):
        self.is_scanning = False
        if self.camera_worker:
            self.camera_worker.frame_ready.disconnect(self.display_frame)
            self.camera_worker.qr_found.disconnect(self.on_qr_found)
            self.camera_worker.camera_error.disconnect(self.on_camera_error)
            self.camera_worker.stop()
            self.camera_worker = None

        self._highlight_timer.stop()
        self.scan_button.setText("Start Camera")
        self.scan_button.setStyleSheet("background-color: #4CAF50;")
        self.camera_label.clear()
        self.status_label.setText("Scan WiFi QR code to connect")

    def on_camera_error(self, error_message):
        self.is_scanning = False
        self.scan_button.setText("Start Camera")
        self.scan_button.setStyleSheet("background-color: #4CAF50;")
        QMessageBox.critical(self, "Camera Error", error_message)

    def connect_to_wifi(self, creds):
        try:
            interfaces = wlanapi.list_interfaces()
        except wlanapi.WlanApiError as exp:
            self._dialog_open = False
            QMessageBox.critical(self, "Error", f"Could not query WiFi adapters: {exp}")
            return

        if not interfaces:
            self._dialog_open = False
            QMessageBox.critical(self, "Error", "No WiFi adapter found or WiFi is off")
            return

        interface_guid = self.resolve_adapter(interfaces)
        if interface_guid is None:
            self._dialog_open = False
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
        self._dialog_open = False

    def show_wifi_details_dialog(self, creds):
        dialog = CustomMessageBox(self)
        dialog.setup_ui(creds.ssid, creds.password or "")
        return dialog.exec_()

    @Slot("QImage")
    def display_frame(self, qt_image):
        pixmap = QPixmap.fromImage(qt_image)
        self.camera_label.set_frame(pixmap, (qt_image.width(), qt_image.height()))

    @Slot(str, object)
    def on_qr_found(self, data, corners):
        self.camera_label.set_highlight(corners)
        self._highlight_timer.start(HIGHLIGHT_DISPLAY_MS)

        if self._dialog_open or not data.startswith("WIFI:"):
            return

        if data == self._ignored_payload and time.monotonic() < self._ignored_until:
            return

        creds = parse_wifi_qr(data)
        if creds:
            self.handle_wifi_qr_found(creds, data)

    def _clear_highlight(self):
        self.camera_label.clear_highlight()

    def handle_wifi_qr_found(self, creds, payload=None):
        log.info(
            "WiFi QR found: ssid=%r security=%s hidden=%s",
            creds.ssid,
            creds.security,
            creds.hidden,
        )
        self._dialog_open = True
        reply = self.show_wifi_details_dialog(creds)

        if reply == QMessageBox.Yes:
            self.connect_to_wifi(creds)
        else:
            self._dialog_open = False
            if payload is not None:
                self._ignored_payload = payload
                self._ignored_until = time.monotonic() + DEBOUNCE_SECONDS

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
