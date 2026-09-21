import xml.etree.ElementTree as ET

from scan2connect.qr.parser import WifiCredentials
from scan2connect.wifi.profile import build_profile_xml

NS = {
    "v1": "http://www.microsoft.com/networking/WLAN/profile/v1",
    "v3": "http://www.microsoft.com/networking/WLAN/profile/v3",
}


def _parse(xml_str):
    return ET.fromstring(xml_str)


class TestWpa2Psk:
    def test_structure(self):
        creds = WifiCredentials(ssid="MyNetwork", password="mypassword", security="WPA2")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)

        assert root.find("v1:name", NS).text == "MyNetwork"
        assert root.find("v1:SSIDConfig/v1:SSID/v1:name", NS).text == "MyNetwork"
        assert (
            root.find("v1:SSIDConfig/v1:SSID/v1:hex", NS).text
            == b"MyNetwork".hex().upper()
        )
        assert root.find("v1:SSIDConfig/v1:nonBroadcast", NS).text == "false"
        assert root.find("v1:connectionType", NS).text == "ESS"

        auth_encryption = root.find("v1:MSM/v1:security/v1:authEncryption", NS)
        assert auth_encryption.find("v1:authentication", NS).text == "WPA2PSK"
        assert auth_encryption.find("v1:encryption", NS).text == "AES"
        assert auth_encryption.find("v1:useOneX", NS).text == "false"

        shared_key = root.find("v1:MSM/v1:security/v1:sharedKey", NS)
        assert shared_key.find("v1:keyType", NS).text == "passPhrase"
        assert shared_key.find("v1:protected", NS).text == "false"
        assert shared_key.find("v1:keyMaterial", NS).text == "mypassword"

    def test_golden(self):
        creds = WifiCredentials(ssid="MyNetwork", password="mypassword", security="WPA2")
        xml_str = build_profile_xml(creds)

        assert xml_str == (
            '<?xml version="1.0"?>\n'
            '<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">\n'
            "    <name>MyNetwork</name>\n"
            "    <SSIDConfig>\n"
            "        <SSID>\n"
            "            <hex>4D794E6574776F726B</hex>\n"
            "            <name>MyNetwork</name>\n"
            "        </SSID>\n"
            "        <nonBroadcast>false</nonBroadcast>\n"
            "    </SSIDConfig>\n"
            "    <connectionType>ESS</connectionType>\n"
            "    <connectionMode>auto</connectionMode>\n"
            "    <MSM>\n"
            "        <security>\n"
            "            <authEncryption>\n"
            "                <authentication>WPA2PSK</authentication>\n"
            "                <encryption>AES</encryption>\n"
            "                <useOneX>false</useOneX>\n"
            "            </authEncryption>\n"
            "            <sharedKey>\n"
            "                <keyType>passPhrase</keyType>\n"
            "                <protected>false</protected>\n"
            "                <keyMaterial>mypassword</keyMaterial>\n"
            "            </sharedKey>\n"
            "        </security>\n"
            "    </MSM>\n"
            "</WLANProfile>\n"
        )


class TestWpa3Sae:
    def test_structure(self):
        creds = WifiCredentials(ssid="SecureNet", password="strong123", security="WPA3")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)

        assert root.tag == "{http://www.microsoft.com/networking/WLAN/profile/v1}WLANProfile"

        auth_encryption = root.find("v1:MSM/v1:security/v1:authEncryption", NS)
        assert auth_encryption is not None
        assert auth_encryption.find("v1:authentication", NS).text == "WPA3SAE"
        assert auth_encryption.find("v1:encryption", NS).text == "AES"

        shared_key = root.find("v1:MSM/v1:security/v1:sharedKey", NS)
        assert shared_key.find("v1:keyType", NS).text == "passPhrase"
        assert shared_key.find("v1:keyMaterial", NS).text == "strong123"

    def test_sae_alias(self):
        creds = WifiCredentials(ssid="SecureNet", password="strong123", security="SAE")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)
        assert root.find("v1:MSM/v1:security/v1:authEncryption/v1:authentication", NS).text == (
            "WPA3SAE"
        )


class TestOpenNetwork:
    def test_structure(self):
        creds = WifiCredentials(ssid="PublicWiFi", password=None, security="NOPASS")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)

        auth_encryption = root.find("v1:MSM/v1:security/v1:authEncryption", NS)
        assert auth_encryption.find("v1:authentication", NS).text == "open"
        assert auth_encryption.find("v1:encryption", NS).text == "none"

        assert root.find("v1:MSM/v1:security/v1:sharedKey", NS) is None

    def test_golden(self):
        creds = WifiCredentials(ssid="PublicWiFi", password=None, security="NOPASS")
        xml_str = build_profile_xml(creds)

        assert xml_str == (
            '<?xml version="1.0"?>\n'
            '<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">\n'
            "    <name>PublicWiFi</name>\n"
            "    <SSIDConfig>\n"
            "        <SSID>\n"
            "            <hex>5075626C696357694669</hex>\n"
            "            <name>PublicWiFi</name>\n"
            "        </SSID>\n"
            "        <nonBroadcast>false</nonBroadcast>\n"
            "    </SSIDConfig>\n"
            "    <connectionType>ESS</connectionType>\n"
            "    <connectionMode>auto</connectionMode>\n"
            "    <MSM>\n"
            "        <security>\n"
            "            <authEncryption>\n"
            "                <authentication>open</authentication>\n"
            "                <encryption>none</encryption>\n"
            "                <useOneX>false</useOneX>\n"
            "            </authEncryption>\n"
            "        </security>\n"
            "    </MSM>\n"
            "</WLANProfile>\n"
        )


class TestWep:
    def test_structure(self):
        creds = WifiCredentials(ssid="OldRouter", password="12345", security="WEP")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)

        auth_encryption = root.find("v1:MSM/v1:security/v1:authEncryption", NS)
        assert auth_encryption.find("v1:authentication", NS).text == "open"
        assert auth_encryption.find("v1:encryption", NS).text == "WEP"

        shared_key = root.find("v1:MSM/v1:security/v1:sharedKey", NS)
        assert shared_key.find("v1:keyType", NS).text == "networkKey"
        assert shared_key.find("v1:keyMaterial", NS).text == "12345"


class TestHidden:
    def test_non_broadcast_true(self):
        creds = WifiCredentials(
            ssid="HiddenNet", password="secret", security="WPA2", hidden=True
        )
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)
        assert root.find("v1:SSIDConfig/v1:nonBroadcast", NS).text == "true"

    def test_non_broadcast_false_by_default(self):
        creds = WifiCredentials(ssid="VisibleNet", password="secret", security="WPA2")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)
        assert root.find("v1:SSIDConfig/v1:nonBroadcast", NS).text == "false"


class TestEscaping:
    def test_ssid_and_password_with_special_chars(self):
        creds = WifiCredentials(
            ssid='Net & <Co>"s"', password="p&ss<word>", security="WPA2"
        )
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)

        assert root.find("v1:name", NS).text == 'Net & <Co>"s"'
        assert (
            root.find("v1:MSM/v1:security/v1:sharedKey/v1:keyMaterial", NS).text
            == "p&ss<word>"
        )

    def test_ssid_hex_matches_utf8_bytes(self):
        creds = WifiCredentials(ssid="Café WiFi", password="pw", security="WPA2")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)

        expected_hex = "Café WiFi".encode().hex().upper()
        assert root.find("v1:SSIDConfig/v1:SSID/v1:hex", NS).text == expected_hex


class TestUnknownSecurityFallsBackToWpa2:
    def test_unrecognized_security_token(self):
        creds = WifiCredentials(ssid="Weird", password="pw", security="BOGUS")
        xml_str = build_profile_xml(creds)
        root = _parse(xml_str)
        assert (
            root.find("v1:MSM/v1:security/v1:authEncryption/v1:authentication", NS).text
            == "WPA2PSK"
        )
