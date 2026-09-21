import time

from PySide6.QtCore import QThread, Signal

from scan2connect.wifi import wlanapi
from scan2connect.wifi.profile import build_profile_xml

CONNECT_TIMEOUT_SECONDS = 15
POLL_INTERVAL_SECONDS = 1


class WifiConnector(QThread):
    status_updated = Signal(str)
    connection_completed = Signal(bool, str)

    def __init__(self, credentials, interface_guid=None):
        super().__init__()
        self.credentials = credentials
        self.ssid = credentials.ssid
        self.interface_guid = interface_guid

    def run(self):
        try:
            with wlanapi.WlanHandle() as handle:
                interface_guid = self.interface_guid
                if interface_guid is None:
                    interfaces = wlanapi.enum_interfaces(handle)
                    if not interfaces:
                        self.connection_completed.emit(
                            False, "No WiFi adapter found or WiFi is off"
                        )
                        return
                    interface_guid = interfaces[0]["guid"]

                profile_xml = build_profile_xml(self.credentials)

                self.status_updated.emit("Adding network profile...")
                wlanapi.set_profile(handle, interface_guid, profile_xml, all_user=False)

                self.status_updated.emit(f"Connecting to {self.ssid}...")
                wlanapi.connect(handle, interface_guid, self.ssid)

                for _ in range(CONNECT_TIMEOUT_SECONDS):
                    time.sleep(POLL_INTERVAL_SECONDS)
                    if wlanapi.current_connection(interface_guid) == self.ssid:
                        self.connection_completed.emit(True, f"Connected to {self.ssid}")
                        return
                    self.status_updated.emit("Connecting...")

                self.connection_completed.emit(False, "Connection Timeout")

        except wlanapi.WlanApiError as exp:
            self.connection_completed.emit(False, f"Connection failed: {exp}")
        except Exception as exp:
            self.connection_completed.emit(False, f"Connection failed: {str(exp)}")
