from scan2connect.qr.parser import WifiCredentials, parse_wifi_qr


class TestBasicParsing:
    """Test basic WIFI: payload parsing."""

    def test_wpa2_with_password(self):
        payload = "WIFI:T:WPA2;S:MyNetwork;P:mypassword;;"
        result = parse_wifi_qr(payload)
        assert result == WifiCredentials(
            ssid="MyNetwork",
            password="mypassword",
            security="WPA2",
            hidden=False
        )

    def test_wpa3_with_password(self):
        payload = "WIFI:T:WPA3;S:SecureNet;P:strong123;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "SecureNet"
        assert result.password == "strong123"
        assert result.security == "WPA3"

    def test_open_network(self):
        payload = "WIFI:T:nopass;S:PublicWiFi;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "PublicWiFi"
        assert result.password is None
        assert result.security == "NOPASS"

    def test_hidden_network(self):
        payload = "WIFI:S:HiddenSSID;P:secret;H:true;;"
        result = parse_wifi_qr(payload)
        assert result.hidden is True
        assert result.ssid == "HiddenSSID"

    def test_default_security_wpa2(self):
        payload = "WIFI:S:Network;P:pass;;"
        result = parse_wifi_qr(payload)
        assert result.security == "WPA2"

    def test_field_order_flexibility(self):
        """Test that fields can appear in any order."""
        payload1 = "WIFI:S:Net;P:pass;T:WPA3;H:false;;"
        payload2 = "WIFI:P:pass;H:false;S:Net;T:WPA3;;"
        assert parse_wifi_qr(payload1) == parse_wifi_qr(payload2)


class TestEscapes:
    """Test escape sequence handling."""

    def test_escaped_semicolon_in_ssid(self):
        payload = r"WIFI:S:Network\;5G;P:pass;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "Network;5G"

    def test_escaped_semicolon_in_password(self):
        payload = r"WIFI:S:Net;P:pass\;word;;"
        result = parse_wifi_qr(payload)
        assert result.password == "pass;word"

    def test_escaped_colon_in_password(self):
        payload = r"WIFI:S:Net;P:my\:password;;"
        result = parse_wifi_qr(payload)
        assert result.password == "my:password"

    def test_escaped_comma_in_password(self):
        payload = r"WIFI:S:Net;P:pass\,word;;"
        result = parse_wifi_qr(payload)
        assert result.password == "pass,word"

    def test_escaped_backslash_in_password(self):
        payload = r"WIFI:S:Net;P:pass\\word;;"
        result = parse_wifi_qr(payload)
        assert result.password == "pass\\word"

    def test_multiple_escapes(self):
        payload = r"WIFI:S:Net\;work;P:pass\:word\;123;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "Net;work"
        assert result.password == "pass:word;123"


class TestQuotedValues:
    """Test quoted field values."""

    def test_quoted_ssid(self):
        payload = 'WIFI:S:"My Network";P:pass;'
        result = parse_wifi_qr(payload)
        assert result.ssid == "My Network"

    def test_quoted_password(self):
        payload = 'WIFI:S:Net;P:"My Pass";'
        result = parse_wifi_qr(payload)
        assert result.password == "My Pass"


class TestRealWorldExamples:
    """Test real-world QR codes from various sources."""

    def test_android_share_sheet_wpa2(self):
        """Typical Android WiFi QR share sheet output."""
        payload = "WIFI:T:WPA2;S:AndroidNet;P:androidpass123;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "AndroidNet"
        assert result.password == "androidpass123"
        assert result.security == "WPA2"

    def test_ios_style(self):
        """iOS-style QR generation."""
        payload = "WIFI:T:WPA2;S:iPhoneWiFi;P:iospass;H:false;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "iPhoneWiFi"
        assert result.password == "iospass"

    def test_router_label_qr(self):
        """Typical router bottom-label QR (often no password)."""
        payload = "WIFI:T:WPA2;S:ASUS-Router;P:admin123;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "ASUS-Router"

    def test_hidden_guest_network(self):
        """Hidden guest network with special characters."""
        payload = r"WIFI:T:WPA2;S:Guest\;Network;P:guest\:123;H:true;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "Guest;Network"
        assert result.password == "guest:123"
        assert result.hidden is True

    def test_wpa3_sae(self):
        """WPA3 with SAE (Simultaneous Authentication of Equals)."""
        payload = "WIFI:T:SAE;S:WPA3Network;P:modern123;;"
        result = parse_wifi_qr(payload)
        assert result.security == "SAE"

    def test_wep_legacy(self):
        """WEP (legacy, insecure) for old devices."""
        payload = "WIFI:T:WEP;S:LegacyWiFi;P:wepkey;;"
        result = parse_wifi_qr(payload)
        assert result.security == "WEP"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_ssid(self):
        """SSID is mandatory."""
        payload = "WIFI:P:password;;"
        result = parse_wifi_qr(payload)
        assert result is None

    def test_empty_ssid(self):
        """Empty SSID is invalid."""
        payload = "WIFI:S:;P:password;;"
        result = parse_wifi_qr(payload)
        assert result is None

    def test_no_prefix(self):
        """Must start with WIFI:."""
        payload = "T:WPA2;S:Net;P:pass;;"
        result = parse_wifi_qr(payload)
        assert result is None

    def test_empty_string(self):
        result = parse_wifi_qr("")
        assert result is None

    def test_none_input(self):
        result = parse_wifi_qr(None)
        assert result is None

    def test_trailing_semicolon_single(self):
        """Single trailing semicolon should be stripped."""
        payload = "WIFI:S:Net;P:pass;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "Net"

    def test_trailing_semicolon_double(self):
        """Double trailing semicolon should be stripped."""
        payload = "WIFI:S:Net;P:pass;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "Net"

    def test_missing_password_allowed(self):
        """Open networks don't need a password."""
        payload = "WIFI:T:nopass;S:OpenNet;;"
        result = parse_wifi_qr(payload)
        assert result.password is None

    def test_empty_password_not_allowed(self):
        """Empty password (P:;) is treated as None."""
        payload = "WIFI:S:Net;P:;T:WPA2;;"
        result = parse_wifi_qr(payload)
        assert result.password is None or result.password == ""

    def test_whitespace_handling(self):
        """Whitespace around unquoted values is preserved; quoted values stripped."""
        payload = 'WIFI:S:"Network";P:"password";'
        result = parse_wifi_qr(payload)
        assert result.ssid == "Network"
        assert result.password == "password"

    def test_case_insensitive_security(self):
        """Security type should be normalized to uppercase."""
        payload = "WIFI:T:wpa2;S:Net;P:pass;;"
        result = parse_wifi_qr(payload)
        assert result.security == "WPA2"

    def test_case_insensitive_hidden(self):
        """Hidden flag should be case-insensitive."""
        payload1 = "WIFI:S:Net;H:true;P:pass;;"
        payload2 = "WIFI:S:Net;H:True;P:pass;;"
        payload3 = "WIFI:S:Net;H:TRUE;P:pass;;"
        assert parse_wifi_qr(payload1).hidden is True
        assert parse_wifi_qr(payload2).hidden is True
        assert parse_wifi_qr(payload3).hidden is True

    def test_malformed_field_skipped(self):
        """Fields without : should be skipped gracefully."""
        payload = "WIFI:S:Net;MALFORMED;P:pass;;"
        result = parse_wifi_qr(payload)
        assert result.ssid == "Net"
        assert result.password == "pass"


class TestDataclass:
    """Test WifiCredentials dataclass."""

    def test_dataclass_creation(self):
        creds = WifiCredentials(
            ssid="TestNet",
            password="testpass",
            security="WPA3",
            hidden=True
        )
        assert creds.ssid == "TestNet"
        assert creds.password == "testpass"
        assert creds.security == "WPA3"
        assert creds.hidden is True

    def test_dataclass_defaults(self):
        creds = WifiCredentials(ssid="Net")
        assert creds.password is None
        assert creds.security == "WPA2"
        assert creds.hidden is False

    def test_dataclass_equality(self):
        creds1 = WifiCredentials("Net", "pass", "WPA2", False)
        creds2 = WifiCredentials("Net", "pass", "WPA2", False)
        assert creds1 == creds2
