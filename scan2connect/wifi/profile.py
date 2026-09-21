"""Build WLAN_profile XML documents for WlanSetProfile.

Schema: http://www.microsoft.com/networking/WLAN/profile/v1

Verified against Windows's own schema validator (`netsh wlan add profile`)
for WPA2PSK/AES, WPA3SAE/AES, open/none, WEP and hidden (nonBroadcast)
variants: WPA3SAE is accepted directly under the v1 namespace, with no
extra v3 namespace or transitionMode element required.
"""

from xml.sax.saxutils import escape

from scan2connect.qr.parser import WifiCredentials

_SECURITY_BY_TYPE = {
    "NOPASS": ("open", "none"),
    "WEP": ("open", "WEP"),
    "WPA": ("WPAPSK", "TKIP"),
    "WPA2": ("WPA2PSK", "AES"),
    "WPA2PSK": ("WPA2PSK", "AES"),
    "WPA3": ("WPA3SAE", "AES"),
    "SAE": ("WPA3SAE", "AES"),
}


def build_profile_xml(creds: WifiCredentials) -> str:
    """Build a WLAN_profile XML document for `creds`, ready for WlanSetProfile."""
    authentication, encryption = _SECURITY_BY_TYPE.get(creds.security.upper(), ("WPA2PSK", "AES"))

    ssid_escaped = escape(creds.ssid)
    ssid_hex = creds.ssid.encode("utf-8").hex().upper()
    non_broadcast = "true" if creds.hidden else "false"

    security_xml = _build_security_xml(encryption, authentication, creds.password)

    return (
        '<?xml version="1.0"?>\n'
        '<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">\n'
        f"    <name>{ssid_escaped}</name>\n"
        "    <SSIDConfig>\n"
        "        <SSID>\n"
        f"            <hex>{ssid_hex}</hex>\n"
        f"            <name>{ssid_escaped}</name>\n"
        "        </SSID>\n"
        f"        <nonBroadcast>{non_broadcast}</nonBroadcast>\n"
        "    </SSIDConfig>\n"
        "    <connectionType>ESS</connectionType>\n"
        "    <connectionMode>auto</connectionMode>\n"
        "    <MSM>\n"
        "        <security>\n"
        f"{security_xml}"
        "        </security>\n"
        "    </MSM>\n"
        "</WLANProfile>\n"
    )


def _build_security_xml(encryption: str, authentication: str, password) -> str:
    lines = [
        "            <authEncryption>\n",
        f"                <authentication>{authentication}</authentication>\n",
        f"                <encryption>{encryption}</encryption>\n",
        "                <useOneX>false</useOneX>\n",
        "            </authEncryption>\n",
    ]

    if encryption != "none" and password:
        key_type = "networkKey" if encryption == "WEP" else "passPhrase"
        password_escaped = escape(password)
        lines.extend(
            [
                "            <sharedKey>\n",
                f"                <keyType>{key_type}</keyType>\n",
                "                <protected>false</protected>\n",
                f"                <keyMaterial>{password_escaped}</keyMaterial>\n",
                "            </sharedKey>\n",
            ]
        )

    return "".join(lines)
