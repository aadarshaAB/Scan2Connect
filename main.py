import sys
import cv2
import re
import pywifi
import time
from pywifi import const
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QPushButton, QLabel, QMessageBox, QProgressDialog,
                                QHBoxLayout, QFrame )
from PySide6.QtCore import Qt, QTimer, Slot, QThread, Signal
from PySide6.QtGui import QImage, QPixmap, QIcon
from pyzbar.pyzbar import decode

class WifiConnector(QThread):
    status_updated = Signal(str)
    connection_completed = Signal(bool, str)

    def __init__(self, ssid, password):
        super(). __init__()
        self.ssid = ssid
        self.password = password
        self.wifi = pywifi.PyWiFi()
        self.iface = self.wifi.interfaces()[0]
    
    def run(self):
        try:
            self.iface.disconnect()
            time.sleep(1)

            profile = pywifi.Profile()
            profile.ssid = self.ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)
            profile.cipher = const.CIPHER_TYPE_CCMP
            profile.key = self.password

            self.status_updated.emit("Removing Existing profiles......")
            self.iface.remove_all_network_profiles()

            self.status_updated.emit(f"Adding new network profiles......")
            profile = self.iface.add_network_profile(profile)

            self.status_updated.emit(f"Connecting to {self.ssid}......")
            self.iface.connect(profile)


            for _ in range(10):
                time.sleep(1)
                if self.iface.status() == const.IFACE_CONNECTED:
                    self.connection_completed.emit(True, f"Connected to {self.ssid}")
                    return
                self.status_updated.emit("Connecting......")
            self.connection_completed.emit(False, "Connection Timeout")

        except Exception as exp:
            self.connection_completed.emit(False, f"Connection failed: {str(exp)}")


class WifiQRScanner(QMainWindow):
    def __init__(self):
        super(). __init__()
        self.setWindowTitle("WiFi QR Scanner")
        self.setMinimumSize(800, 600)


            

            



        