import time

from PySide6.QtCore import QThread, Signal

from scan2connect.wifi import wlanapi
from scan2connect.wifi.profile import build_profile_xml

CONNECT_TIMEOUT_SECONDS = 15
POLL_INTERVAL_SECONDS = 1
MAX_ATTEMPTS = 3

_AUTH_FAILURE_STATES = {
    wlanapi.WLAN_INTERFACE_STATE_AUTHENTICATING,
}


class WifiConnector(QThread):
    status_updated = Signal(str)
    connection_completed = Signal(bool, str)

    def __init__(self, credentials, interface_guid=None):
        super().__init__()
        self.credentials = credentials
        self.ssid = credentials.ssid
        self.interface_guid = interface_guid
        self._cancelled = False

    def cancel(self):
        """Request cancellation. Checked once per poll iteration (~1s granularity)."""
        self._cancelled = True

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

                if wlanapi.current_connection(interface_guid) == self.ssid:
                    self.connection_completed.emit(True, f"Already connected to {self.ssid}")
                    return

                if self._cancelled:
                    self.connection_completed.emit(False, "Cancelled")
                    return

                profile_xml = build_profile_xml(self.credentials)

                self.status_updated.emit("Adding network profile...")
                wlanapi.set_profile(handle, interface_guid, profile_xml, all_user=False)

                for attempt in range(1, MAX_ATTEMPTS + 1):
                    if self._cancelled:
                        self._cleanup(handle, interface_guid)
                        self.connection_completed.emit(False, "Cancelled")
                        return

                    if attempt > 1:
                        self.status_updated.emit(
                            f"Retrying connection ({attempt}/{MAX_ATTEMPTS})..."
                        )
                    else:
                        self.status_updated.emit(f"Connecting to {self.ssid}...")

                    wlanapi.connect(handle, interface_guid, self.ssid)

                    outcome = self._await_connection(handle, interface_guid)

                    if outcome == "connected":
                        self.connection_completed.emit(True, f"Connected to {self.ssid}")
                        return
                    if outcome == "cancelled":
                        self._cleanup(handle, interface_guid)
                        self.connection_completed.emit(False, "Cancelled")
                        return
                    if outcome == "wrong_password":
                        self._cleanup(handle, interface_guid)
                        self.connection_completed.emit(False, "Wrong password")
                        return
                    # outcome == "timeout": fall through and retry

                self._cleanup(handle, interface_guid)
                self.connection_completed.emit(False, "Connection Timeout")

        except wlanapi.WlanApiError as exp:
            self.connection_completed.emit(False, f"Connection failed: {exp}")
        except Exception as exp:
            self.connection_completed.emit(False, f"Connection failed: {str(exp)}")

    def _await_connection(self, handle, interface_guid):
        """Poll until connected, a wrong-password auth failure is detected,
        cancellation is requested, or CONNECT_TIMEOUT_SECONDS elapses."""
        saw_authenticating = False

        for _ in range(CONNECT_TIMEOUT_SECONDS):
            if self._cancelled:
                return "cancelled"

            time.sleep(POLL_INTERVAL_SECONDS)

            if wlanapi.current_connection(interface_guid) == self.ssid:
                return "connected"

            state = wlanapi.interface_state(handle, interface_guid)
            if state in _AUTH_FAILURE_STATES:
                saw_authenticating = True
            elif saw_authenticating and state == wlanapi.WLAN_INTERFACE_STATE_DISCONNECTED:
                return "wrong_password"

            self.status_updated.emit("Connecting...")

        return "timeout"

    def _cleanup(self, handle, interface_guid):
        """Best-effort: disconnect and remove the profile we added on failure."""
        try:
            wlanapi.disconnect(handle, interface_guid)
        except wlanapi.WlanApiError:
            pass
        try:
            wlanapi.delete_profile(handle, interface_guid, self.ssid)
        except wlanapi.WlanApiError:
            pass
