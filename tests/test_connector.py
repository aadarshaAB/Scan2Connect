from unittest.mock import MagicMock, patch

from scan2connect.qr.parser import WifiCredentials
from scan2connect.wifi.connector import WifiConnector
from scan2connect.wifi.wlanapi import WlanApiError


class _FakeWlanHandle:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _run_connector(credentials, **wlanapi_overrides):
    """Run WifiConnector.run() synchronously against a mocked wlanapi module."""
    connector = WifiConnector(credentials)

    status_updates = []
    results = []
    connector.status_updated.connect(status_updates.append)
    connector.connection_completed.connect(lambda ok, msg: results.append((ok, msg)))

    defaults = {
        "WlanHandle": MagicMock(return_value=_FakeWlanHandle()),
        "enum_interfaces": MagicMock(return_value=[{"guid": "fake-guid", "description": "Fake"}]),
        "set_profile": MagicMock(),
        "connect": MagicMock(),
        "current_connection": MagicMock(return_value=credentials.ssid),
    }
    defaults.update(wlanapi_overrides)

    with patch.multiple("scan2connect.wifi.connector.wlanapi", **defaults), patch(
        "scan2connect.wifi.connector.time.sleep"
    ):
        connector.run()

    return status_updates, results


class TestSuccessfulConnection:
    def test_wpa2_connects(self):
        creds = WifiCredentials(ssid="MyNetwork", password="mypassword", security="WPA2")
        status_updates, results = _run_connector(creds)

        assert results == [(True, "Connected to MyNetwork")]
        assert any("Connecting to MyNetwork" in s for s in status_updates)

    def test_wpa3_connects(self):
        creds = WifiCredentials(ssid="SecureNet", password="strong123", security="WPA3")
        status_updates, results = _run_connector(creds)

        assert results == [(True, "Connected to SecureNet")]

    def test_builds_and_sets_profile_before_connecting(self):
        creds = WifiCredentials(ssid="MyNetwork", password="mypassword", security="WPA2")
        set_profile_mock = MagicMock()
        connect_mock = MagicMock()
        _run_connector(creds, set_profile=set_profile_mock, connect=connect_mock)

        assert set_profile_mock.called
        assert connect_mock.called
        set_profile_call_order = set_profile_mock.call_args
        assert set_profile_call_order.kwargs.get("all_user") is False or (
            len(set_profile_call_order.args) >= 4 and set_profile_call_order.args[3] is False
        )


class TestNoAdapter:
    def test_no_interfaces_fails_fast(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        status_updates, results = _run_connector(creds, enum_interfaces=MagicMock(return_value=[]))

        assert results == [(False, "No WiFi adapter found")]


class TestTimeout:
    def test_never_connects_reports_timeout(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        status_updates, results = _run_connector(
            creds, current_connection=MagicMock(return_value=None)
        )

        assert results == [(False, "Connection Timeout")]


class TestWlanApiFailure:
    def test_set_profile_error_reported(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        error = WlanApiError("WlanSetProfile", 5)
        status_updates, results = _run_connector(creds, set_profile=MagicMock(side_effect=error))

        assert len(results) == 1
        ok, message = results[0]
        assert ok is False
        assert "WlanSetProfile" in message

    def test_connect_error_reported(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        error = WlanApiError("WlanConnect", 5)
        status_updates, results = _run_connector(creds, connect=MagicMock(side_effect=error))

        assert len(results) == 1
        assert results[0][0] is False
