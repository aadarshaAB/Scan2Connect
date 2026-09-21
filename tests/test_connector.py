from unittest.mock import MagicMock, patch

from scan2connect.qr.parser import WifiCredentials
from scan2connect.wifi.connector import CONNECT_TIMEOUT_SECONDS, WifiConnector
from scan2connect.wifi.wlanapi import (
    WLAN_INTERFACE_STATE_AUTHENTICATING,
    WLAN_INTERFACE_STATE_DISCONNECTED,
    WlanApiError,
)


class _FakeWlanHandle:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _run_connector(credentials, interface_guid=None, connector_setup=None, **wlanapi_overrides):
    """Run WifiConnector.run() synchronously against a mocked wlanapi module."""
    connector = WifiConnector(credentials, interface_guid)
    if connector_setup is not None:
        connector_setup(connector)

    status_updates = []
    results = []
    connector.status_updated.connect(status_updates.append)
    connector.connection_completed.connect(lambda ok, msg: results.append((ok, msg)))

    # current_connection is called once up-front (already-connected check) and then
    # once per poll iteration. Default: not connected yet, connects on the first poll.
    current_connection_mock = MagicMock(side_effect=[None, credentials.ssid])

    defaults = {
        "WlanHandle": MagicMock(return_value=_FakeWlanHandle()),
        "enum_interfaces": MagicMock(return_value=[{"guid": "fake-guid", "description": "Fake"}]),
        "set_profile": MagicMock(),
        "connect": MagicMock(),
        "current_connection": current_connection_mock,
        "interface_state": MagicMock(return_value=WLAN_INTERFACE_STATE_DISCONNECTED),
        "disconnect": MagicMock(),
        "delete_profile": MagicMock(),
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

        assert results == [(False, "No WiFi adapter found or WiFi is off")]


class TestExplicitAdapter:
    def test_explicit_guid_skips_enumeration(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        enum_interfaces_mock = MagicMock()
        connect_mock = MagicMock()
        _run_connector(
            creds,
            interface_guid="chosen-guid",
            enum_interfaces=enum_interfaces_mock,
            connect=connect_mock,
        )

        enum_interfaces_mock.assert_not_called()
        assert connect_mock.call_args.args[1] == "chosen-guid"


class TestTimeout:
    def test_never_connects_reports_timeout(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        connect_mock = MagicMock()
        status_updates, results = _run_connector(
            creds,
            current_connection=MagicMock(return_value=None),
            connect=connect_mock,
        )

        assert results == [(False, "Connection Timeout")]
        assert connect_mock.call_count == 3  # bounded retry: 3 attempts total

    def test_timeout_cleans_up_profile(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        delete_profile_mock = MagicMock()
        _run_connector(
            creds,
            current_connection=MagicMock(return_value=None),
            delete_profile=delete_profile_mock,
        )

        assert delete_profile_mock.called

    def test_retries_then_succeeds(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        # First attempt (15 polls) never connects; second attempt connects on first poll.
        current_connection_mock = MagicMock(
            side_effect=[None] + [None] * CONNECT_TIMEOUT_SECONDS + [creds.ssid]
        )
        status_updates, results = _run_connector(
            creds, current_connection=current_connection_mock
        )

        assert results == [(True, "Connected to MyNetwork")]
        assert any("Retrying connection" in s for s in status_updates)


class TestAlreadyConnected:
    def test_already_connected_to_target_ssid_skips_connect(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        connect_mock = MagicMock()
        set_profile_mock = MagicMock()
        status_updates, results = _run_connector(
            creds,
            current_connection=MagicMock(return_value="MyNetwork"),
            connect=connect_mock,
            set_profile=set_profile_mock,
        )

        assert results == [(True, "Already connected to MyNetwork")]
        connect_mock.assert_not_called()
        set_profile_mock.assert_not_called()


class TestWrongPassword:
    def test_authenticating_then_disconnected_reports_wrong_password(self):
        creds = WifiCredentials(ssid="MyNetwork", password="badpw", security="WPA2")
        state_mock = MagicMock(
            side_effect=[
                WLAN_INTERFACE_STATE_AUTHENTICATING,
                WLAN_INTERFACE_STATE_DISCONNECTED,
            ]
        )
        status_updates, results = _run_connector(
            creds,
            current_connection=MagicMock(return_value=None),
            interface_state=state_mock,
        )

        assert results == [(False, "Wrong password")]

    def test_wrong_password_cleans_up_profile(self):
        creds = WifiCredentials(ssid="MyNetwork", password="badpw", security="WPA2")
        state_mock = MagicMock(
            side_effect=[
                WLAN_INTERFACE_STATE_AUTHENTICATING,
                WLAN_INTERFACE_STATE_DISCONNECTED,
            ]
        )
        delete_profile_mock = MagicMock()
        disconnect_mock = MagicMock()
        _run_connector(
            creds,
            current_connection=MagicMock(return_value=None),
            interface_state=state_mock,
            delete_profile=delete_profile_mock,
            disconnect=disconnect_mock,
        )

        assert delete_profile_mock.called
        assert disconnect_mock.called

    def test_wrong_password_does_not_retry(self):
        creds = WifiCredentials(ssid="MyNetwork", password="badpw", security="WPA2")
        state_mock = MagicMock(
            side_effect=[
                WLAN_INTERFACE_STATE_AUTHENTICATING,
                WLAN_INTERFACE_STATE_DISCONNECTED,
            ]
        )
        connect_mock = MagicMock()
        _run_connector(
            creds,
            current_connection=MagicMock(return_value=None),
            interface_state=state_mock,
            connect=connect_mock,
        )

        assert connect_mock.call_count == 1


class TestCancel:
    def test_cancel_before_start_reports_cancelled(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        connect_mock = MagicMock()
        status_updates, results = _run_connector(
            creds,
            current_connection=MagicMock(return_value=None),
            connect=connect_mock,
            connector_setup=lambda c: c.cancel(),
        )

        assert results == [(False, "Cancelled")]
        connect_mock.assert_not_called()

    def test_cancel_during_poll_reports_cancelled(self):
        creds = WifiCredentials(ssid="MyNetwork", password="pw", security="WPA2")
        connector = WifiConnector(creds)

        status_updates = []
        results = []
        connector.status_updated.connect(status_updates.append)
        connector.connection_completed.connect(lambda ok, msg: results.append((ok, msg)))

        poll_count = {"n": 0}

        def current_connection_mock(_guid):
            poll_count["n"] += 1
            if poll_count["n"] == 2:
                connector.cancel()
            return None

        with patch.multiple(
            "scan2connect.wifi.connector.wlanapi",
            WlanHandle=MagicMock(return_value=_FakeWlanHandle()),
            enum_interfaces=MagicMock(return_value=[{"guid": "fake-guid", "description": "Fake"}]),
            set_profile=MagicMock(),
            connect=MagicMock(),
            current_connection=current_connection_mock,
            interface_state=MagicMock(return_value=WLAN_INTERFACE_STATE_DISCONNECTED),
            disconnect=MagicMock(),
            delete_profile=MagicMock(),
        ), patch("scan2connect.wifi.connector.time.sleep"):
            connector.run()

        assert results == [(False, "Cancelled")]


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
