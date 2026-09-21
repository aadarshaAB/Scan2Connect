"""ctypes bindings for the Windows Native WiFi API (wlanapi.dll).

Reference: https://learn.microsoft.com/en-us/windows/win32/nativewifi/wlan-2

Only what Scan2Connect needs is bound: opening/closing a client handle,
enumerating interfaces, querying the current connection, and
get/set/delete/connect/disconnect on profiles. Not wired into the app yet
(see E-09); this module is a standalone foundation with its own
`list_interfaces()` / `current_connection()` helpers.
"""

import ctypes
from ctypes import POINTER, Structure, byref, c_ulong, c_void_p, c_wchar, c_wchar_p
from ctypes.wintypes import BOOL, DWORD, HANDLE

wlanapi = ctypes.windll.wlanapi

WLAN_MAX_NAME_LENGTH = 256
GUID_SIZE = 16

ERROR_SUCCESS = 0


class GUID(Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __str__(self):
        d4 = "".join(f"{b:02x}" for b in self.Data4)
        return f"{{{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-{d4[:4]}-{d4[4:]}}}"


class WLAN_INTERFACE_INFO(Structure):
    _fields_ = [
        ("InterfaceGuid", GUID),
        ("strInterfaceDescription", c_wchar * WLAN_MAX_NAME_LENGTH),
        ("isState", c_ulong),
    ]


class WLAN_INTERFACE_INFO_LIST(Structure):
    _fields_ = [
        ("dwNumberOfItems", DWORD),
        ("dwIndex", DWORD),
        ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
    ]


class DOT11_SSID(Structure):
    _fields_ = [
        ("uSSIDLength", c_ulong),
        ("ucSSID", ctypes.c_ubyte * 32),
    ]

    @property
    def ssid(self):
        return bytes(self.ucSSID[: self.uSSIDLength]).decode("utf-8", errors="replace")


class WLAN_CONNECTION_ATTRIBUTES(Structure):
    _fields_ = [
        ("isState", c_ulong),
        ("wlanConnectionMode", c_ulong),
        ("strProfileName", c_wchar * WLAN_MAX_NAME_LENGTH),
        ("wlanAssociationAttributes_dot11Ssid", DOT11_SSID),
        ("wlanAssociationAttributes_dot11BssType", c_ulong),
        ("wlanAssociationAttributes_dot11Bssid", ctypes.c_ubyte * 6),
        ("wlanAssociationAttributes_dot11PhyType", c_ulong),
        ("wlanAssociationAttributes_uDot11PhyIndex", c_ulong),
        ("wlanAssociationAttributes_wlanSignalQuality", c_ulong),
        ("wlanAssociationAttributes_ulRxRate", c_ulong),
        ("wlanAssociationAttributes_ulTxRate", c_ulong),
        ("wlanSecurityAttributes_bSecurityEnabled", BOOL),
        ("wlanSecurityAttributes_bOneXEnabled", BOOL),
        ("wlanSecurityAttributes_dot11AuthAlgorithm", c_ulong),
        ("wlanSecurityAttributes_dot11CipherAlgorithm", c_ulong),
    ]


class WLAN_CONNECTION_PARAMETERS(Structure):
    _fields_ = [
        ("wlanConnectionMode", c_ulong),
        ("strProfile", c_wchar_p),
        ("pDot11Ssid", POINTER(DOT11_SSID)),
        ("pDesiredBssidList", c_void_p),
        ("dot11BssType", c_ulong),
        ("dwFlags", DWORD),
    ]


# wlan_intf_opcode
WLAN_INTF_OPCODE_CURRENT_CONNECTION = 7

# WLAN_CONNECTION_MODE
wlan_connection_mode_profile = 0
wlan_connection_mode_temporary_profile = 1

# dot11_bss_type
dot11_BSS_type_infrastructure = 1

wlanapi.WlanOpenHandle.argtypes = [DWORD, c_void_p, POINTER(DWORD), POINTER(HANDLE)]
wlanapi.WlanOpenHandle.restype = DWORD

wlanapi.WlanCloseHandle.argtypes = [HANDLE, c_void_p]
wlanapi.WlanCloseHandle.restype = DWORD

wlanapi.WlanEnumInterfaces.argtypes = [
    HANDLE,
    c_void_p,
    POINTER(POINTER(WLAN_INTERFACE_INFO_LIST)),
]
wlanapi.WlanEnumInterfaces.restype = DWORD

wlanapi.WlanQueryInterface.argtypes = [
    HANDLE,
    POINTER(GUID),
    c_ulong,
    c_void_p,
    POINTER(DWORD),
    POINTER(c_void_p),
    POINTER(c_ulong),
]
wlanapi.WlanQueryInterface.restype = DWORD

wlanapi.WlanGetProfile.argtypes = [
    HANDLE,
    POINTER(GUID),
    c_wchar_p,
    c_void_p,
    POINTER(c_wchar_p),
    POINTER(DWORD),
    POINTER(DWORD),
]
wlanapi.WlanGetProfile.restype = DWORD

wlanapi.WlanSetProfile.argtypes = [
    HANDLE,
    POINTER(GUID),
    DWORD,
    c_wchar_p,
    c_wchar_p,
    BOOL,
    c_void_p,
    POINTER(DWORD),
]
wlanapi.WlanSetProfile.restype = DWORD

wlanapi.WlanDeleteProfile.argtypes = [HANDLE, POINTER(GUID), c_wchar_p, c_void_p]
wlanapi.WlanDeleteProfile.restype = DWORD

wlanapi.WlanConnect.argtypes = [
    HANDLE,
    POINTER(GUID),
    POINTER(WLAN_CONNECTION_PARAMETERS),
    c_void_p,
]
wlanapi.WlanConnect.restype = DWORD

wlanapi.WlanDisconnect.argtypes = [HANDLE, POINTER(GUID), c_void_p]
wlanapi.WlanDisconnect.restype = DWORD

wlanapi.WlanRegisterNotification.argtypes = [
    HANDLE,
    DWORD,
    BOOL,
    c_void_p,
    c_void_p,
    c_void_p,
    POINTER(DWORD),
]
wlanapi.WlanRegisterNotification.restype = DWORD

wlanapi.WlanFreeMemory.argtypes = [c_void_p]
wlanapi.WlanFreeMemory.restype = None


class WlanApiError(OSError):
    """A wlanapi.dll call returned a non-success Win32 error code."""

    def __init__(self, function_name, error_code):
        self.function_name = function_name
        self.error_code = error_code
        super().__init__(
            f"{function_name} failed with Win32 error {error_code}: "
            f"{ctypes.FormatError(error_code)}"
        )


def _check(function_name, error_code):
    if error_code != ERROR_SUCCESS:
        raise WlanApiError(function_name, error_code)


class WlanHandle:
    """Context manager around WlanOpenHandle/WlanCloseHandle."""

    def __init__(self):
        self._handle = None

    def __enter__(self):
        negotiated_version = DWORD()
        handle = HANDLE()
        _check(
            "WlanOpenHandle",
            wlanapi.WlanOpenHandle(2, None, byref(negotiated_version), byref(handle)),
        )
        self._handle = handle
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._handle is not None:
            wlanapi.WlanCloseHandle(self._handle, None)
            self._handle = None

    @property
    def handle(self):
        return self._handle


def enum_interfaces(wlan_handle):
    """Return a list of {'guid': GUID, 'description': str, 'state': int} dicts."""
    interface_list_ptr = POINTER(WLAN_INTERFACE_INFO_LIST)()
    _check(
        "WlanEnumInterfaces",
        wlanapi.WlanEnumInterfaces(wlan_handle.handle, None, byref(interface_list_ptr)),
    )
    try:
        interface_list = interface_list_ptr.contents
        array_offset = WLAN_INTERFACE_INFO_LIST.InterfaceInfo.offset
        array_address = ctypes.addressof(interface_list) + array_offset
        info_array = ctypes.cast(
            array_address,
            POINTER(WLAN_INTERFACE_INFO * interface_list.dwNumberOfItems),
        ).contents

        return [
            {
                "guid": GUID.from_buffer_copy(info.InterfaceGuid),
                "description": info.strInterfaceDescription,
                "state": info.isState,
            }
            for info in info_array
        ]
    finally:
        wlanapi.WlanFreeMemory(interface_list_ptr)


def query_current_connection(wlan_handle, interface_guid):
    """Return a WLAN_CONNECTION_ATTRIBUTES for the given interface, or None if not connected."""
    data_size = DWORD()
    data_ptr = c_void_p()
    opcode_value_type = c_ulong()

    error_code = wlanapi.WlanQueryInterface(
        wlan_handle.handle,
        byref(interface_guid),
        WLAN_INTF_OPCODE_CURRENT_CONNECTION,
        None,
        byref(data_size),
        byref(data_ptr),
        byref(opcode_value_type),
    )
    if error_code != ERROR_SUCCESS:
        return None

    try:
        live_attributes = ctypes.cast(data_ptr, POINTER(WLAN_CONNECTION_ATTRIBUTES)).contents
        return WLAN_CONNECTION_ATTRIBUTES.from_buffer_copy(live_attributes)
    finally:
        wlanapi.WlanFreeMemory(data_ptr)


def get_profile_xml(wlan_handle, interface_guid, profile_name):
    """Return the XML profile string for `profile_name` on `interface_guid`."""
    xml_ptr = c_wchar_p()
    _check(
        "WlanGetProfile",
        wlanapi.WlanGetProfile(
            wlan_handle.handle,
            byref(interface_guid),
            profile_name,
            None,
            byref(xml_ptr),
            None,
            None,
        ),
    )
    try:
        return ctypes.wstring_at(xml_ptr)
    finally:
        wlanapi.WlanFreeMemory(xml_ptr)


def set_profile(wlan_handle, interface_guid, profile_xml, all_user=True):
    """Add or update a profile from its XML representation."""
    flags = 0 if all_user else 1  # WLAN_PROFILE_USER (per-user, not all-user)
    reason_code = DWORD()
    _check(
        "WlanSetProfile",
        wlanapi.WlanSetProfile(
            wlan_handle.handle,
            byref(interface_guid),
            flags,
            profile_xml,
            None,
            True,
            None,
            byref(reason_code),
        ),
    )


def delete_profile(wlan_handle, interface_guid, profile_name):
    _check(
        "WlanDeleteProfile",
        wlanapi.WlanDeleteProfile(wlan_handle.handle, byref(interface_guid), profile_name, None),
    )


def connect(wlan_handle, interface_guid, profile_name):
    """Connect to an existing profile by name (infrastructure mode)."""
    params = WLAN_CONNECTION_PARAMETERS()
    params.wlanConnectionMode = wlan_connection_mode_profile
    params.strProfile = profile_name
    params.pDot11Ssid = None
    params.pDesiredBssidList = None
    params.dot11BssType = dot11_BSS_type_infrastructure
    params.dwFlags = 0

    _check(
        "WlanConnect",
        wlanapi.WlanConnect(wlan_handle.handle, byref(interface_guid), byref(params), None),
    )


def disconnect(wlan_handle, interface_guid):
    _check(
        "WlanDisconnect",
        wlanapi.WlanDisconnect(wlan_handle.handle, byref(interface_guid), None),
    )


def register_notification(wlan_handle, callback, context=None):
    """Register for WLAN notifications. `callback` must match WLAN_NOTIFICATION_CALLBACK."""
    prev_mask = DWORD()
    _check(
        "WlanRegisterNotification",
        wlanapi.WlanRegisterNotification(
            wlan_handle.handle,
            0x0000FFFF,  # WLAN_NOTIFICATION_SOURCE_ALL
            False,
            callback,
            context,
            None,
            byref(prev_mask),
        ),
    )


def list_interfaces():
    """Return [{'description': str, 'guid': str, 'ssid': str | None}, ...]."""
    results = []
    with WlanHandle() as wlan_handle:
        for interface in enum_interfaces(wlan_handle):
            guid = interface["guid"]
            ssid = None
            attributes = query_current_connection(wlan_handle, guid)
            if attributes is not None:
                ssid = attributes.wlanAssociationAttributes_dot11Ssid.ssid

            results.append(
                {
                    "description": interface["description"],
                    "guid": str(guid),
                    "ssid": ssid,
                }
            )
    return results


def current_connection(interface_guid):
    """Return the current SSID for `interface_guid`, or None if not connected."""
    with WlanHandle() as wlan_handle:
        attributes = query_current_connection(wlan_handle, interface_guid)
        if attributes is None:
            return None
        return attributes.wlanAssociationAttributes_dot11Ssid.ssid


if __name__ == "__main__":
    for iface in list_interfaces():
        print(iface)
